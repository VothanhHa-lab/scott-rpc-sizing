"""Task 1: corrected line search = union of Chat*{factors} (stored) and an absolute grid of ratings.

usage: python s2_reselect.py CASE SSC[,SSC...] [lowprune]
 - absolute grid: step 0.25 MVA up to 5 MVA, step 0.5 MVA above, up to
   Cmax = min(peak-sizing rating, J_old_best / w1)  (J >= w1*C, so a larger C cannot beat the old optimum)
 - lowprune (used for the 40-week sensitivity cases): absolute candidates below 0.95*Chat(eps) are skipped,
   because fewer than ceil(0.95 N) weeks can comply there (verified without pruning for base/suburban).
 - selection: minimum mean annual cost J subject to  n_comply >= ceil(0.95 N)  (57/60, 38/40).
"""
import sys, json, time
import numpy as np
from common import *

case = sys.argv[1]; Sscs = [int(x) for x in sys.argv[2].split(",")]
lowprune = len(sys.argv) > 3 and sys.argv[3] == "lowprune"
s = load_summary(case)
N = s["n_weeks"]
eg = s["eps_grid"]
plan = {}
for Ssc in Sscs:
    d = s["design"][str(Ssc)]
    ocands, OA = old_arrays(s, Ssc)
    Jold = J_arrays([c[1] for c in ocands], OA)[0]
    iold, _ = select(ocands, OA, N)              # old procedure (all old candidates comply by construction)
    Cmax = min(d["c_peak"], Jold[iold] / W1)
    grid = [round(0.25 * i, 2) for i in range(0, 21)]
    c = 5.0
    while c < Cmax + 0.5:
        c += 0.5; grid.append(round(c, 2))
    grid = [g for g in grid if g <= Cmax + 0.5]
    new = []
    for i, e in enumerate(eg):
        chat = d["c_design"][i]
        for g in grid:
            if lowprune and g < 0.95 * chat and g > 0:
                continue
            if any(abs(oc[0] - e) < 1e-9 and abs(oc[1] - g) < 1e-9 for oc in ocands):
                continue
            new.append((float(e), float(g)))
    plan[Ssc] = dict(ocands=ocands, OA=OA, iold=iold, Cmax=Cmax, new=new)
    print(case, Ssc, "old best", ocands[iold], round(Jold[iold], 2), "Cmax", round(Cmax, 2), "new cands", len(new), flush=True)

# evaluate new candidates, streaming over the weeks
res = {S: {f: np.zeros((len(p["new"]), N)) for f in FIELDS} for S, p in plan.items()}
t0 = time.time()
for k in range(N):
    P, Q = load_week(case, k)
    for S, p in plan.items():
        for j, (e, C) in enumerate(p["new"]):
            ev = rpc.evaluate(P, Q, C, e, S)
            for f, a in zip(FIELDS, [ev["p95"], ev["E_viol"], ev["E_loss"], ev["E_transfer"], ev["vmax10"], ev["share_above"]]):
                res[S][f][j, k] = a
    if k % 10 == 0:
        print("week", k, round(time.time() - t0), "s", flush=True)

out = {}
for S, p in plan.items():
    cands = p["ocands"] + p["new"]
    A = {f: np.vstack([p["OA"][f], res[S][f]]) for f in FIELDS}
    np.savez_compressed(f"arrays_{case}_{S}.npz", cands=np.array(cands), **A)
    C = np.array([c[1] for c in cands]); E = np.array([c[0] for c in cands])
    J, cap, loss, viol = J_arrays(C, A)
    nc = n_comply(A)
    inew, _ = select(cands, A, N)
    iold = p["iold"]
    # eps = 2 (percentile threshold) with C optimised
    mask2 = np.abs(E - 2.0) < 1e-9
    i2, _ = select(cands, A, N, mask=mask2)
    i2old, _ = select(cands[:72], {f: A[f][:72] for f in FIELDS}, N, mask=mask2[:72])
    # infeasible candidates below Chat: check monotonicity claim (any feasible candidate with C < Chat(eps)?)
    d = s["design"][str(S)]
    below = [(float(E[i]), float(C[i])) for i in range(len(C))
             if C[i] < d["c_design"][eg.index(E[i])] - 1e-9 and nc[i] >= order_k(N)]
    # best C for each eps (for Fig 9a): old vs new
    per_eps = []
    for ie, e in enumerate(eg):
        m = (np.abs(E - e) < 1e-9)
        io, _ = select(cands[:72], {f: A[f][:72] for f in FIELDS}, N, mask=m[:72])
        inn, _ = select(cands, A, N, mask=m)
        per_eps.append(dict(eps=e, Chat=d["c_design"][ie], C_old=float(C[io]), J_old=float(J[io]), C_new=float(C[inn]), J_new=float(J[inn])))
    def rec(i):
        return dict(C=float(C[i]), eps=float(E[i]), J=float(J[i]), Jcap=float(cap[i]), Jloss=float(loss[i]), Jviol=float(viol[i]),
                    n_comply=int(nc[i]), N=N, need=order_k(N), p95_mean=float(A["p95"][i].mean()),
                    Eviol=float(A["E_viol"][i].mean() * WY), Eloss=float(A["E_loss"][i].mean() * WY),
                    Etr=float(A["E_transfer"][i].mean() * WY), vmax=float(A["vmax10"][i].mean()), share=float(A["share_above"][i].mean()))
    out[S] = dict(old=rec(iold), new=rec(inew), p95copt_old=rec(i2old), p95copt_new=rec(i2),
                  Cmax=p["Cmax"], n_new_cands=len(p["new"]), feasible_below_Chat=below, per_eps=per_eps,
                  # J(C) profile at the new optimum threshold
                  profile=[dict(C=float(C[i]), J=float(J[i]), n_comply=int(nc[i])) for i in np.where(np.abs(E - E[inew]) < 1e-9)[0]])
    o, n = out[S]["old"], out[S]["new"]
    print(f"Ssc={S}: OLD C*={o['C']:.2f} eps*={o['eps']:.2f} J={o['J']:.1f} | NEW C*={n['C']:.2f} eps*={n['eps']:.2f} J={n['J']:.1f} comply {n['n_comply']}/{N}"
          f" | p95_Copt old {out[S]['p95copt_old']['C']:.2f}/{out[S]['p95copt_old']['J']:.1f} new {out[S]['p95copt_new']['C']:.2f}/{out[S]['p95copt_new']['J']:.1f}"
          f" | feasible below Chat: {len(below)}", flush=True)
json.dump(out, open(f"reselect_{case}_{'_'.join(map(str, Sscs))}.json", "w"), indent=1)
print("done", round(time.time() - t0), "s")
