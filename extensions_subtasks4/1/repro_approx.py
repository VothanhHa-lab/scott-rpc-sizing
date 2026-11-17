"""Independent re-derivation of the approximate-model (8) design (Ssc=750) from the stored weeks:
weekly C_min(eps) (bisection), Chat(eps)=X_(ceil .95N), 72-candidate line search, J of every candidate.
Compares with the stored base.json / suburban.json evaluations. Usage: repro_approx.py base|sub"""
import sys, time, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *
import analyse  # /home/claude/code (cwd-independent: sys.path set in common)

name = sys.argv[1]
case = {"base": "base", "sub": "suburban"}[name]
stored = json.load(open(CODE + ("/results/base.json" if name == "base" else "/results_sub/suburban.json")))
N = NW[name]
eps_grid = stored["eps_grid"]; cf = stored["c_fact"]
t0 = time.time()
cm = np.zeros((N, len(eps_grid)))
W = [load_week(name, k) for k in range(N)]
for k, (P, Q) in enumerate(W):
    for i, e in enumerate(eps_grid):
        cm[k, i] = rpc.c_min(P, Q, e, SSC)
print("cmin done", round(time.time() - t0), flush=True)
cm_st = np.array([w["cmin"][str(int(SSC))] for w in stored["weeks"]])
cdes = np.array([q95(cm[:, i]) for i in range(len(eps_grid))])
d = stored["design"][str(int(SSC))]
peaks = np.array([max(0.0, float(np.hypot(P, Q).max()) - LIM / 100 * SSC) / 2 for P, Q in W])
fulls = np.array([float(np.hypot(P, Q).max()) / 2 for P, Q in W])
c_peak, c_full = q95(peaks), q95(fulls)
cands = [(float(e), float(cdes[i] * f)) for i, e in enumerate(eps_grid) for f in cf] + [(LIM, c_peak), (0.0, c_full)]
ev = [[rpc.evaluate(P, Q, C, e, SSC) for (e, C) in cands] for (P, Q) in W]   # [week][cand]
cs = [analyse.cost_terms(ev, i) for i in range(len(cands))]
J = np.array([c[0] for c in cs])
comply = np.array([np.mean([w[i]["p95"] <= LIM + 1e-9 for w in ev]) for i in range(len(cands))])
nf = len(cf)
i_prop = int(np.argmin(J[: len(eps_grid) * nf]))
i_p95 = eps_grid.index(LIM) * nf
# stored comparison
ev_st = d["evals"]
maxdiff = {f: max(abs(ev[k][i][f] - ev_st[k][i][f]) for k in range(N) for i in range(len(cands)))
           for f in ["C", "p95", "vmax10", "share_above", "E_viol", "E_loss", "E_transfer", "sx_max"]}
out = dict(set=name, N=N, eps_grid=eps_grid, cdes=cdes.tolist(), cdes_stored=d["c_design"],
           cmin_maxabsdiff_vs_stored=float(np.max(np.abs(cm - cm_st))),
           c_peak=c_peak, c_full=c_full, c_peak_stored=d["c_peak"], c_full_stored=d["c_full"],
           cands=cands, J=J.tolist(), comply=comply.tolist(),
           i_prop=i_prop, prop=dict(C=cands[i_prop][1], eps=cands[i_prop][0], J=float(J[i_prop]),
                                    Jcap=cs[i_prop][1], Jloss=cs[i_prop][2], Jviol=cs[i_prop][3], comply=float(comply[i_prop])),
           p95=dict(C=cands[i_p95][1], eps=LIM, J=float(J[i_p95]), Jcap=cs[i_p95][1], Jloss=cs[i_p95][2], Jviol=cs[i_p95][3],
                    comply=float(comply[i_p95])),
           eval_maxabsdiff_vs_stored=maxdiff,
           weeks_nan_cmin=int(np.isnan(cm).sum()))
# percentile with optimised C (stored 72-grid, eps = 2 %) and round-3 absolute grid result
cand_p95opt = min(range(i_p95, i_p95 + nf), key=lambda i: J[i])
out["p95_Copt_72grid"] = dict(C=cands[cand_p95opt][1], J=float(J[cand_p95opt]))
json.dump(out, open(f"{OUT}/data/repro_approx_{name}.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ["cmin_maxabsdiff_vs_stored", "i_prop", "prop", "p95", "p95_Copt_72grid", "eval_maxabsdiff_vs_stored", "c_peak", "c_full"]}, indent=1))
print("time", round(time.time() - t0))
