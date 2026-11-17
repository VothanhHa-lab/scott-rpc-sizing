"""Sensitivity: capacity limit with the exact busbar voltage instead of the approximate U used inside rpc.compensate.
sx = min(req, KAPPA*C*min(|u_alpha|,|u_beta|,1)), |u| from the exact phasor model with the transfer applied (3 fixed-point passes).
20 base weeks (every 3rd), designs of Table 12: proposed exact (11.27, 1.0), corrected percentile (11.83, 1.9)."""
import sys, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *
from rpc_sizing.rpc import KAPPA

def exact_limited(P, Q, C, eps, n_pass=3):
    S = P + 1j * Q; mag = np.abs(S)
    req = np.maximum(0.0, mag - eps / 100 * SSC) / 2
    sx, _ = rpc.compensate(P, Q, C, eps, SSC)            # start: code's own limit
    m = mag > 0
    for _ in range(n_pass):
        sxv = np.where(m, sx * S / np.maximum(mag, 1e-9), 0)
        v = np.zeros(len(S)); ua = np.ones(len(S)); ub = np.ones(len(S))
        v[m], (ua_m, ub_m) = solve(S[m] - sxv[m], sxv[m], SSC, n_iter=10, tol=1e-6)
        ua[m], ub[m] = np.abs(ua_m), np.abs(ub_m)
        sx = np.minimum(req, KAPPA * C * np.minimum(np.minimum(ua, ub), 1.0))
    sxv = np.where(m, sx * S / np.maximum(mag, 1e-9), 0)
    v = np.zeros(len(S))
    v[m], _ = solve(S[m] - sxv[m], sxv[m], SSC, n_iter=10, tol=1e-6)
    return v, np.abs(sxv)

res = {}
for tag, C, eps in (("proposed_exact", 11.2706, 1.0), ("corrected_percentile", 11.8251, 1.9)):
    base, lim = [], []
    for k in range(0, 60, 3):
        P, Q = load_week("base", k)
        b = eval_week(P, Q, C, eps, "exact")
        v, sx = exact_limited(P, Q, C, eps)
        l = week_metrics(v, sx, C)
        base.append(b); lim.append(l)
    f = lambda rows, key: float(np.mean([r[key] for r in rows]))
    res[tag] = dict(C=C, eps=eps, n_weeks=len(base),
                    P95_mean_code=f(base, "P95"), P95_mean_exactU=f(lim, "P95"),
                    P95_max_code=max(r["P95"] for r in base), P95_max_exactU=max(r["P95"] for r in lim),
                    comply_code=int(sum(r["P95"] <= LIM + 1e-9 for r in base)), comply_exactU=int(sum(r["P95"] <= LIM + 1e-9 for r in lim)),
                    Eviol_code=f(base, "E_viol"), Eviol_exactU=f(lim, "E_viol"),
                    Eloss_code=f(base, "E_loss"), Eloss_exactU=f(lim, "E_loss"),
                    J_code=f(base, "J"), J_exactU=f(lim, "J"), Jviol_code=f(base, "J_viol"), Jviol_exactU=f(lim, "J_viol"))
    print(tag, res[tag], flush=True)
json.dump(res, open(OUT + "/data/checks_d.json", "w"), indent=1)
