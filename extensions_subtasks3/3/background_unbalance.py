"""Design of the RPC rating with a pre-existing PCC negative-sequence voltage.

Approximation (8) in complex form (see scott_phase_check.py):
   u2_sub(t) = exp(j theta_s) * conj(S_alpha - S_beta) / S_sc,
   S_alpha - S_beta = S_L - 2 s_x   (s_x along S_L, real scaling, expression (11)/(15)).
Background phasor u2_bg = b * exp(j psi), constant within a week.
Per 10-min window (rms aggregation of the 1-s values, as in section 4):
   VUF10^2 = mean_t |u2_bg + u2_sub(t)|^2 = b^2 + mean|u2_sub|^2 + 2 b Re(e^{-j psi} mean u2_sub)
so only per-window moments (m2, Re/Im of the mean phasor) are needed for any psi.
Scenarios (b in {0.5, 1.0} %):
  none   : no background (reproduces the design rule of section 4.3)
  alg    : in phase at every instant, VUF = b + |u2_sub| (algebraic sum, upper bound)
  worst  : psi fixed per week, worst of 8 angles (psi = theta_s + k*45 deg) per week
  rand   : psi uniform; 8 equally weighted angles per week (quadrature, no sampling noise)
  iec    : IEC TR 61000-3-13 summation law, VUF10 = (b^a + vuf10_sub^a)^(1/a), a = 1.4
Design rule (same as sections 4.2-4.3): for each eps_u the weekly minimum rating C_min^(k)
(bisection, tol 0.01 MVA) such that P95[VUF10] <= 2 %; C_hat = 95 % quantile (inverted_cdf)
over the (week, phase) realisations; line search C = C_hat*{1,1.1,1.2,1.35,1.5,1.75,2,2.5}
minimising the mean annual cost J = w1 C + w2 E_loss + w3 E_viol (same cost model).
"""
import sys, json, time, os
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing.params import GRID, RPC

OUT = "/home/claude/subtasks3/3"
RES = "/home/claude/code/results/base_w%03d.npz"
SSC = 750.0
LIM = GRID["vuf_lim"]
THETA_S = np.arctan(10.0)               # source X/R = 10 (network.py)
ALPHA = 1.4
EPS = [0.0, 0.5, 1.0, 1.5, 2.0]         # 2.0 = conventional percentile sizing (12)
EPS_SEARCH = [0.0, 0.5, 1.0, 1.5]       # coarse grid of the design rule (task)
FACT = [1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0, 2.5]
BG = [0.5, 1.0]
NPSI = 8
PSI = THETA_S + 2 * np.pi * np.arange(NPSI) / NPSI    # psi = 0 <=> in phase with unity-pf motoring contribution
WIN = rpc.WIN
NW = 60
W = RPC["weeks_per_year"]


def load(k):
    d = np.load(RES % k)
    return d["P"].astype(float), d["Q"].astype(float)


class Week:
    def __init__(self, P, Q):
        self.P, self.Q = P, Q
        S = np.hypot(P, Q)
        self.S = S
        ph = THETA_S - np.arctan2(Q, P)          # arg of conj(S_L)*exp(j theta_s)
        self.wr, self.wi = np.cos(ph), np.sin(ph)
        self.peak = S.max()

    def moments(self, C, eps):
        """Per-window moments of the substation contribution at rating C."""
        sx, mag = rpc.compensate(self.P, self.Q, C, eps, SSC)
        n = len(mag) // WIN
        m = mag[: n * WIN].reshape(n, WIN)
        mr = (mag * self.wr)[: n * WIN].reshape(n, WIN)
        mi = (mag * self.wi)[: n * WIN].reshape(n, WIN)
        return dict(sx=sx, m1=m.mean(1), m2=(m ** 2).mean(1), ur=mr.mean(1), ui=mi.mean(1))


def v10(mo, kind, b, k_psi=None):
    """10-min VUF (%) per window for a scenario."""
    if kind == "none":
        return np.sqrt(mo["m2"])
    if kind == "alg":
        return np.sqrt(b * b + 2 * b * mo["m1"] + mo["m2"])
    if kind == "iec":
        return (b ** ALPHA + np.sqrt(mo["m2"]) ** ALPHA) ** (1 / ALPHA)
    if kind == "phase":
        psi = PSI[k_psi]
        return np.sqrt(np.maximum(b * b + mo["m2"] + 2 * b * (np.cos(psi) * mo["ur"] + np.sin(psi) * mo["ui"]), 0))
    raise ValueError(kind)


def cmin(wk, eps, kind, b, k_psi=None, tol=0.01):
    f = lambda C: rpc.p95(v10(wk.moments(C, eps), kind, b, k_psi)) - LIM
    if f(0.0) <= 0:
        return 0.0
    hi = wk.peak / 2.0 * 1.1 + 0.1
    if f(hi) > 0:
        return np.inf
    lo = 0.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0: hi = mid
        else: lo = mid
    return hi


def scen_list():
    L = [("none", 0.0)]
    for b in BG:
        L += [("alg", b), ("iec", b), ("phase", b)]      # phase -> worst & rand share the bisections
    return L


def pass1():
    t0 = time.time()
    out = {}
    for k in range(NW):
        wk = Week(*load(k))
        for eps in EPS:
            out[(k, eps, "none", 0.0)] = cmin(wk, eps, "none", 0.0)
            for b in BG:
                out[(k, eps, "alg", b)] = cmin(wk, eps, "alg", b)
                out[(k, eps, "iec", b)] = cmin(wk, eps, "iec", b)
                for j in range(NPSI):
                    out[(k, eps, "phase", b, j)] = cmin(wk, eps, "phase", b, j)
        print(f"pass1 week {k+1}/{NW}  {time.time()-t0:.0f}s", flush=True)
    return out


def quant95(x):
    x = np.asarray(x, float)
    x = np.where(np.isnan(x), np.inf, x)
    return float(np.quantile(x, 0.95, method="inverted_cdf"))


def design(c1):
    """C_hat for every (scenario, eps)."""
    D = {}
    for eps in EPS:
        D[("none", 0.0, eps)] = quant95([c1[(k, eps, "none", 0.0)] for k in range(NW)])
        for b in BG:
            D[("alg", b, eps)] = quant95([c1[(k, eps, "alg", b)] for k in range(NW)])
            D[("iec", b, eps)] = quant95([c1[(k, eps, "iec", b)] for k in range(NW)])
            D[("rand", b, eps)] = quant95([c1[(k, eps, "phase", b, j)] for k in range(NW) for j in range(NPSI)])
            D[("worst", b, eps)] = quant95([max(c1[(k, eps, "phase", b, j)] for j in range(NPSI)) for k in range(NW)])
    return D


def eval_week(wk, C, eps, name, b):
    """Return list of per-realisation dicts (p95, E_viol, comply...) for a scenario at rating C."""
    mo = wk.moments(C, eps)
    sx = mo["sx"]
    if name in ("none", "alg", "iec"):
        vs = [v10(mo, name, b)]
    else:
        vs = [v10(mo, "phase", b, j) for j in range(NPSI)]
    res = []
    for v in vs:
        ex = np.maximum(0.0, v - LIM)
        res.append(dict(p95=rpc.p95(v), E_viol=float(ex.sum() / 6.0), share=float(np.mean(v > LIM + 1e-9)),
                        vmax10=float(v.max())))
    return dict(E_loss=rpc.losses_MWh(sx, C), E_tr=float(sx.sum() / 3600.0), real=res)


def J_of(C, E_loss, E_viol):
    cap = RPC["cost_kUSD_per_MVA"] * 2.0 * C * RPC["crf"]
    return cap + RPC["energy_price_USD_MWh"] * E_loss * W / 1000.0 + RPC["viol_price_kUSD_per_pct_h"] * E_viol * W, cap


def pass2(D):
    names = [("none", 0.0)] + [(n, b) for b in BG for n in ("alg", "rand", "worst", "iec")]
    cands = {}
    for (name, b) in names:
        for eps in EPS:
            ch = D[(name, b, eps)]
            if np.isfinite(ch):
                for f in FACT:
                    cands[(name, b, eps, f)] = ch * f
    acc = {key: [] for key in cands}
    t0 = time.time()
    for k in range(NW):
        wk = Week(*load(k))
        cache = {}
        for (name, b, eps, f), C in cands.items():
            kk = (round(C, 9), eps, "phase" if name in ("rand", "worst") else name, b)
            if kk not in cache:
                cache[kk] = eval_week(wk, C, eps, "rand" if name in ("rand", "worst") else name, b)
            acc[(name, b, eps, f)].append(cache[kk])
        print(f"pass2 week {k+1}/{NW}  {time.time()-t0:.0f}s", flush=True)
    return cands, acc


def summarise(cands, acc, D, c1):
    S = {}
    for key, C in cands.items():
        name, b, eps, f = key
        ev = acc[key]
        Ev, Pp, Cm, Sh = [], [], [], []
        for w in ev:
            r = w["real"]
            if name == "worst":      # worst fixed phase of the week (by P95; E_viol of that phase)
                i = int(np.argmax([x["p95"] for x in r])); r = [r[i]]
                i2 = int(np.argmax([x["E_viol"] for x in w["real"]]))
                Ev.append(w["real"][i2]["E_viol"])
            else:
                Ev.append(np.mean([x["E_viol"] for x in r]))
            Pp.append(np.mean([x["p95"] for x in r]))
            Cm.append(np.mean([x["p95"] <= LIM + 1e-6 for x in r]))
            Sh.append(np.mean([x["share"] for x in r]))
        Eloss = np.mean([w["E_loss"] for w in ev])
        Etr = np.mean([w["E_tr"] for w in ev])
        Ev = float(np.mean(Ev))
        J, cap = J_of(C, Eloss, Ev)
        S[key] = dict(C=float(C), J=float(J), Jcap=float(cap),
                      Jloss=float(RPC["energy_price_USD_MWh"] * Eloss * W / 1000),
                      Jviol=float(RPC["viol_price_kUSD_per_pct_h"] * Ev * W),
                      E_viol_h_yr=float(Ev * W), E_loss_MWh_yr=float(Eloss * W), E_tr_GWh_yr=float(Etr * W / 1000),
                      p95_mean=float(np.mean(Pp)), comply=float(np.mean(Cm)), share_above=float(np.mean(Sh)))
    return S


def main():
    c1 = pass1()
    D = design(c1)
    cands, acc = pass2(D)
    S = summarise(cands, acc, D, c1)
    names = [("none", 0.0)] + [(n, b) for b in BG for n in ("alg", "rand", "worst", "iec")]
    result = dict(meta=dict(Ssc=SSC, lim=LIM, theta_s_deg=float(np.degrees(THETA_S)), alpha=ALPHA, eps=EPS,
                            eps_search=EPS_SEARCH, factors=FACT, bg=BG, n_weeks=NW, n_psi=NPSI,
                            psi_deg_relative=[float(np.degrees(p - THETA_S)) for p in PSI],
                            weekly_dir=RES), scen={})
    for (name, b) in names:
        key = f"{name}_{b}"
        r = dict(Chat={str(e): D[(name, b, e)] for e in EPS})
        # proposed design: min J over eps in EPS_SEARCH and factors
        best = None
        for e in EPS_SEARCH:
            for f in FACT:
                kk = (name, b, e, f)
                if kk in S and (best is None or S[kk]["J"] < S[best]["J"]):
                    best = kk
        r["proposed"] = dict(eps_u=best[2], factor=best[3], **S[best]) if best else None
        # conventional percentile design (eps_u = 2 %, C = C_hat) and its feasibility
        kk = (name, b, 2.0, 1.0)
        r["conventional"] = dict(S[kk]) if kk in S else None
        r["J_per_eps_at_Chat_mult"] = {str(e): {str(f): S[(name, b, e, f)]["J"] for f in FACT if (name, b, e, f) in S}
                                       for e in EPS}
        r["best_J_per_eps"] = {str(e): (lambda L: dict(factor=min(L)[1], J=min(L)[0], C=S[(name, b, e, min(L)[1])]["C"]))(
            [(S[(name, b, e, f)]["J"], f) for f in FACT]) if (name, b, e, 1.0) in S else None for e in EPS}
        result["scen"][key] = r
    # weekly cmin arrays for reference (no bg and per scenario at eps = 1)
    result["weekly_cmin_eps1"] = {
        "none": [c1[(k, 1.0, "none", 0.0)] for k in range(NW)],
        **{f"alg_{b}": [c1[(k, 1.0, "alg", b)] for k in range(NW)] for b in BG},
        **{f"iec_{b}": [c1[(k, 1.0, "iec", b)] for k in range(NW)] for b in BG}}
    json.dump(result, open(f"{OUT}/results_background.json", "w"), indent=1,
              default=lambda o: None if (isinstance(o, float) and not np.isfinite(o)) else float(o))
    print("done")


if __name__ == "__main__":
    main()
