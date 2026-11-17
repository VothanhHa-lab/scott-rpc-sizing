"""Sizing with the exact phasor network model inside the loop (item 1) and
certification of the design with the scenario approach (item 5).

Step A (selection): on the 60 base weeks, the weekly minimum rating that
meets P95[VUF_10min] <= 2 % is found by bisection with the VUF computed by
the exact network model (rpc_sizing/network.py); the design rule and the
cost model are the same as in experiment.py.
Step B (certification): on N_c independent new weeks (other seeds), the
weekly minimum ratings for the selected threshold are computed, and the
design rating is the (k+1)-th largest value. For a scalar decision with a
monotone constraint, the probability V that a new week violates the
criterion satisfies P(V > eps) = BinomCDF(k; N_c, eps) (distribution-free).
"""
import json, os, sys, time
import numpy as np
from multiprocessing import Pool
from scipy import stats
from rpc_sizing import rpc
from rpc_sizing.network import solve
from rpc_sizing.experiment import week_case, seed_of
from rpc_sizing.params import SEED0, RPC

SSC = 750.0
EPS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 1.9]
C_FACT = [1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0, 2.5]
LIM = 2.0


def vuf_exact(P, Q, C, eps):
    S = P + 1j * Q
    mag = np.abs(S)
    if C > 0:
        sx, _ = rpc.compensate(P, Q, C, eps, SSC)
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
    else:
        sxv = np.zeros_like(S)
    v = np.zeros(len(S))
    m = mag > 0
    v[m], _ = solve(S[m] - sxv[m], sxv[m], SSC, n_iter=10, tol=1e-6)
    return v, sxv


def p95_exact(P, Q, C, eps):
    return rpc.p95(rpc.vuf10(vuf_exact(P, Q, C, eps)[0]))


def cmin_exact(P, Q, eps, tol=0.02):
    f = lambda C: p95_exact(P, Q, C, eps) - LIM
    if f(0.0) <= 0:
        return 0.0
    hi = float(np.hypot(P, Q).max()) / 2 * 1.1 + 0.1
    if f(hi) > 0:
        return float("nan")
    # start from the approximate solution to save evaluations
    c0 = rpc.c_min(P, Q, min(eps, LIM), SSC)
    lo, h = 0.0, hi
    for c in ((c0, c0 * 1.05, c0 * 1.1, c0 * 1.2) if np.isfinite(c0) else ()):
        if c > 0 and f(c) <= 0:
            h = c
            break
        lo = max(lo, c)
    hi = h
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return hi


def load_week(case, k, store):
    d = np.load(store % k)
    return d["P"].astype(float), d["Q"].astype(float)


def stepA_week(k):
    P, Q = load_week("base", k, "results/base_w%03d.npz")
    return [cmin_exact(P, Q, e) for e in EPS]


def evaluate_exact(P, Q, C, eps):
    v, sxv = vuf_exact(P, Q, C, eps)
    sx = np.abs(sxv)
    v10 = rpc.vuf10(v)
    return dict(C=C, eps=eps, p95=rpc.p95(v10), p99=float(np.quantile(v10, 0.99, method="inverted_cdf")),
                vmax=float(v10.max()), share=float(np.mean(v10 > LIM + 1e-9)),
                E_viol=float(np.maximum(0, v10 - LIM).sum() / 6), E_loss=rpc.losses_MWh(sx, C),
                E_tr=float(sx.sum() / 3600))


def stepA2_week(args):
    k, cands = args
    P, Q = load_week("base", k, "results/base_w%03d.npz")
    return [evaluate_exact(P, Q, C, e) for (e, C) in cands]


def stepB_week(args):
    k, eps_list = args
    P, Q = week_case("base", k, SEED0 + 900000)     # new, independent weeks
    np.savez_compressed("results_exact/cert_w%03d.npz" % k, P=P.astype(np.float32), Q=Q.astype(np.float32))
    return [cmin_exact(P, Q, e) for e in eps_list]


def J_of(evs):
    C = evs[0]["C"]; W = RPC["weeks_per_year"]
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    loss = RPC["energy_price_USD_MWh"] * np.mean([e["E_loss"] for e in evs]) * W / 1000
    viol = RPC["viol_price_kUSD_per_pct_h"] * np.mean([e["E_viol"] for e in evs]) * W
    return cap + loss + viol, cap, loss, viol


if __name__ == "__main__":
    t = time.time()
    out = {}
    os.makedirs("results_exact", exist_ok=True)
    # ---- Step A: weekly exact minimum ratings ----
    fA = "results_exact/stepA.json"
    if os.path.exists(fA):
        cm = np.array(json.load(open(fA))["cmin"])
    else:
        with Pool(2) as pool:
            cm = np.array(pool.map(stepA_week, range(60)))
        json.dump({"eps": EPS, "cmin": cm.tolist()}, open(fA, "w"))
    print("A done", round(time.time() - t), flush=True)
    cdes = [float(np.quantile(c[~np.isnan(c)], 0.95, method="inverted_cdf")) if np.all(~np.isnan(c)) else float("nan")
            for c in cm.T]
    cands = [(e, cdes[i] * f) for i, e in enumerate(EPS) if not np.isnan(cdes[i]) for f in C_FACT]
    fA2 = "results_exact/stepA2.json"
    if os.path.exists(fA2):
        ev = json.load(open(fA2))["evals"]
    else:
        with Pool(2) as pool:
            ev = pool.map(stepA2_week, [(k, cands) for k in range(60)])
        json.dump({"cands": cands, "evals": ev}, open(fA2, "w"))
    print("A2 done", round(time.time() - t), flush=True)
    Js = [J_of([w[i] for w in ev])[0] for i in range(len(cands))]
    ok = [np.mean([w[i]["p95"] <= LIM + 1e-9 for w in ev]) >= 0.95 for i in range(len(cands))]
    ibest = min((i for i in range(len(cands)) if ok[i]), key=lambda i: Js[i])
    nf = len(C_FACT)
    iconv = EPS.index(1.9) * nf                         # corrected percentile sizing
    eps_star = cands[ibest][0]
    print("selected", cands[ibest], Js[ibest], "conv(1.9)", cands[iconv], Js[iconv], flush=True)
    # ---- Step B: certification on new weeks ----
    NB = 90
    fB = "results_exact/stepB.json"
    if os.path.exists(fB):
        cb = np.array(json.load(open(fB))["cmin"])
    else:
        with Pool(2) as pool:
            cb = np.array(pool.map(stepB_week, [(k, [eps_star, 1.9]) for k in range(NB)]))
        json.dump({"eps": [eps_star, 1.9], "cmin": cb.tolist()}, open(fB, "w"))
    print("B done", round(time.time() - t), flush=True)
