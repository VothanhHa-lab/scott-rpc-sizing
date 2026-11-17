"""Check of approximation (8) with the exact phasor network model."""
import json, sys, time
import numpy as np
from rpc_sizing import rpc
from rpc_sizing.network import solve

SSC = 750.0
from analyse import load, methods
_m = methods(load('base'), 750)
DES = {"p95": (_m['p95']['C'], 2.0), "prop": (_m['proposed']['C'], _m['proposed']['eps'])}


def exact_vuf(P, Q, C, eps):
    S = P + 1j * Q
    if C > 0:
        sx, _ = rpc.compensate(P, Q, C, eps, SSC)
        mag = np.abs(S)
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
    else:
        sxv = np.zeros_like(S)
    v, _ = solve(S - sxv, sxv, SSC)
    return v


def cmin_exact(P, Q, eps, lo, hi, tol=0.05):
    f = lambda C: rpc.p95(rpc.vuf10(exact_vuf(P, Q, C, eps))) - 2.0
    it = 0
    while f(hi) > 0:
        lo, hi = hi, hi * 1.2
        it += 1
        if it > 6:
            return float('nan')
    if f(lo) <= 0:
        return lo
    while hi - lo > tol:
        m = 0.5 * (lo + hi)
        if f(m) <= 0: hi = m
        else: lo = m
    return hi


if __name__ == "__main__":
    weeks = range(int(sys.argv[1]), int(sys.argv[2]))
    out = []
    for k in weeks:
        t = time.time()
        d = np.load(f"results/base_w{k:03d}.npz")
        P, Q = d["P"].astype(float), d["Q"].astype(float)
        r = {"k": k}
        for name, (C, e) in [("none", (0.0, 2.0))] + list(DES.items()):
            va = rpc.compensate(P, Q, C, e, SSC)[1] if C > 0 else np.hypot(P, Q) / SSC * 100
            ve = exact_vuf(P, Q, C, e)
            r[name] = dict(p95_apx=rpc.p95(rpc.vuf10(va)), p95_ex=rpc.p95(rpc.vuf10(ve)),
                           max_apx=float(rpc.vuf10(va).max()), max_ex=float(rpc.vuf10(ve).max()),
                           relerr_inst=float(np.median((ve[va > 0.5] - va[va > 0.5]) / va[va > 0.5])))
        if k < 10:
            ca2 = rpc.c_min(P, Q, 2.0, SSC); ca1 = rpc.c_min(P, Q, DES["prop"][1], SSC)
            r["cmin"] = dict(apx2=ca2, ex19=cmin_exact(P, Q, 1.9, ca2 * 0.95, ca2 * 1.2),
                             apx1=ca1, ex1=cmin_exact(P, Q, DES["prop"][1], ca1 * 0.95, ca1 * 1.2))
        out.append(r)
        print(k, round(time.time() - t), json.dumps(r)[:300], flush=True)
    json.dump(out, open(f"results/netval_{weeks.start}_{weeks.stop}.json", "w"))
