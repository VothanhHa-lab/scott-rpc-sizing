"""Task 3: sensitivity of (C*, eps*, J*) to the grid of the line search, approximate model, base case,
Ssc = 750 MVA, all 60 weeks.
 grid A (manuscript): eps step 0.25, C = Chat*{1,1.1,1.2,1.35,1.5,1.75,2,2.5}   (stored evaluations)
 grid B (fine)      : eps step 0.125 (17 values), C = Chat(eps)*{1, 1.2, 1.225, ..., 1.5}
 grid C (absolute)  : eps in {0.75, 1, 1.25}, C = 9.0, 9.1, ..., 12.0 MVA (step 0.1), subject to >= 57 compliant weeks
"""
import json, time
import numpy as np
from common import *

SSC = 750
s = load_summary("base"); N = 60
t0 = time.time()
EPSB = [round(0.125 * i, 3) for i in range(17)]
FACB = [1.0] + [round(1.2 + 0.025 * i, 3) for i in range(13)]
EA = [0.75, 1.0, 1.25]
CA = [round(9.0 + 0.1 * i, 2) for i in range(31)]
# ---- Chat(eps) on the fine eps grid (weekly bisection c_min, tol 0.01 as in the manuscript) ----
stored = {e: np.array([w["cmin"]["750"][i] for w in s["weeks"]]) for i, e in enumerate(s["eps_grid"])}
cmin = {e: stored[e] for e in EPSB if e in stored}
need = [e for e in EPSB if e not in stored]
tmp = {e: np.zeros(N) for e in need}
for k in range(N):
    P, Q = load_week("base", k)
    for e in need:
        tmp[e][k] = rpc.c_min(P, Q, e, SSC)
for e in need:
    cmin[e] = tmp[e]
print("c_min on fine eps grid done", round(time.time() - t0), "s", flush=True)
Chat = {e: design_quantile(cmin[e]) for e in EPSB}
for e in s["eps_grid"]:
    assert abs(Chat[e] - s["design"]["750"]["c_design"][s["eps_grid"].index(e)]) < 1e-9
cands = [(e, f * Chat[e], f"B{f}") for e in EPSB for f in FACB] + [(e, c, "C") for e in EA for c in CA]
res = {f: np.zeros((len(cands), N)) for f in FIELDS}
for k in range(N):
    P, Q = load_week("base", k)
    for j, (e, C, _) in enumerate(cands):
        ev = rpc.evaluate(P, Q, C, e, SSC)
        for f, a in zip(FIELDS, [ev["p95"], ev["E_viol"], ev["E_loss"], ev["E_transfer"], ev["vmax10"], ev["share_above"]]):
            res[f][j, k] = a
    if k % 10 == 0:
        print("week", k, round(time.time() - t0), "s", flush=True)
np.savez_compressed("arrays_gridsens.npz", cands=np.array([(c[0], c[1]) for c in cands]), **res)

C = np.array([c[1] for c in cands]); E = np.array([c[0] for c in cands]); tag = [c[2] for c in cands]
J, cap, loss, viol = J_arrays(C, res); nc = n_comply(res)
ok = nc >= order_k(N)
def best(mask):
    idx = np.where(mask & ok)[0]; i = idx[np.argmin(J[idx])]
    return dict(eps=float(E[i]), C=float(C[i]), J=float(J[i]), n_comply=int(nc[i]), tag=tag[i])
isB = np.array([t.startswith("B") for t in tag]); isC = np.array([t == "C" for t in tag])
# grid A re-derived from stored evaluations
ocands, OA = old_arrays(s, SSC); ia, _ = select(ocands, OA, N)
JA = J_arrays([c[1] for c in ocands], OA)[0]
out = dict(
    gridA=dict(eps=ocands[ia][0], C=ocands[ia][1], J=float(JA[ia])),
    gridB=best(isB),
    gridB_restricted_to_old_eps=best(isB & np.isin(E, s["eps_grid"])),
    gridC_eps_1=best(isC & (np.abs(E - 1.0) < 1e-9)),
    gridC=best(isC),
    Chat_fine={str(e): Chat[e] for e in EPSB},
)
# surface J(eps, factor) on grid B
out["J_surface_B"] = {str(e): {str(f): float(J[next(j for j, (ee, cc, t) in enumerate(cands) if ee == e and t == f"B{f}")]) for f in FACB} for e in EPSB}
out["comply_B"] = {str(e): {str(f): int(nc[next(j for j, (ee, cc, t) in enumerate(cands) if ee == e and t == f"B{f}")]) for f in FACB} for e in EPSB}
# best C for each eps on grid B, near-optimal set
Jstar = out["gridB"]["J"]
perE = []
for e in EPSB:
    m = isB & (np.abs(E - e) < 1e-9); r = best(m); perE.append(r)
out["per_eps_B"] = perE
out["near_opt_1pct"] = [dict(eps=float(E[j]), C=float(C[j]), J=float(J[j])) for j in np.where(isB & ok & (J <= 1.01 * Jstar))[0]]
out["near_opt_0.5pct"] = [dict(eps=float(E[j]), C=float(C[j]), J=float(J[j])) for j in np.where(isB & ok & (J <= 1.005 * Jstar))[0]]
# profile at eps = 1 (absolute C grid, step 0.1)
for e in EA:
    out[f"profile_eps_{e}"] = [dict(C=float(C[j]), J=float(J[j]), Jcap=float(cap[j]), Jloss=float(loss[j]), Jviol=float(viol[j]), n_comply=int(nc[j]))
                               for j in np.where(isC & (np.abs(E - e) < 1e-9))[0]]
json.dump(out, open("gridsens_base.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ["gridA", "gridB", "gridB_restricted_to_old_eps", "gridC_eps_1", "gridC"]}, indent=1))
print("near-optimal (within 1 %) pairs on grid B:", len(out["near_opt_1pct"]), "eps range",
      min(x["eps"] for x in out["near_opt_1pct"]), max(x["eps"] for x in out["near_opt_1pct"]),
      "C range", round(min(x["C"] for x in out["near_opt_1pct"]), 2), round(max(x["C"] for x in out["near_opt_1pct"]), 2))
print("done", round(time.time() - t0), "s")
