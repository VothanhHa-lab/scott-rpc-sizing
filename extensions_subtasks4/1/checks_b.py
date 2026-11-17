"""Monotonicity of the weekly P95 in C (approx. model), 20 base weeks, eps in {0, 1.0, 1.9, 2.0}; and agreement
of the bisection result c_min with the smallest grid value that meets the criterion.
Also: aggregation (mean of weekly maxima vs maximum over weeks) of the 'maximum 10-min VUF' column of Table 6."""
import sys, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

out = {}
from rpc_sizing.network import solve
step = 0.1
Cgrid = np.round(np.arange(0.0, 20.0 + 1e-9, step), 3)
res = {}
for e in (0.0, 1.0, 1.9, 2.0):
    nonmono_weeks, maxrise, cmin_gap = 0, 0.0, []
    for k in range(0, 60, 3):                       # 20 weeks
        P, Q = load_week("base", k)
        p95s = np.array([rpc.p95(rpc.vuf10(rpc.compensate(P, Q, C, e, SSC)[1])) for C in Cgrid])
        rise = np.max(np.diff(p95s))                 # largest increase of P95 when C grows by `step`
        if rise > 1e-9:
            nonmono_weeks += 1
        maxrise = max(maxrise, float(rise))
        ok = np.where(p95s <= LIM)[0]
        c_scan = float(Cgrid[ok[0]]) if len(ok) else float("nan")
        c_bis = rpc.c_min(P, Q, e, SSC)
        cmin_gap.append(dict(k=k, c_scan_first_feasible=c_scan, c_min_bisection=c_bis,
                             bis_minus_scan=c_bis - c_scan,
                             feasible_set_is_upper_interval=bool(len(ok) == 0 or np.all(p95s[ok[0]:] <= LIM))))
    res[str(e)] = dict(weeks_with_P95_increasing_in_C=nonmono_weeks, max_increase_of_P95_per_step=maxrise,
                       all_feasible_sets_upper_intervals=bool(all(g["feasible_set_is_upper_interval"] for g in cmin_gap)),
                       max_abs_bis_minus_scan=float(np.nanmax([abs(g["bis_minus_scan"]) for g in cmin_gap])),
                       min_bis_minus_scan=float(np.nanmin([g["bis_minus_scan"] for g in cmin_gap])))
    print(e, res[str(e)], flush=True)
out["monotonicity_C_grid_0.1"] = res

# ---- convergence of the fixed-point solver as used in exact_sizing (n_iter=10, tol=1e-6) ----
conv = []
for k in (0, 17, 43):
    P, Q = load_week("base", k)
    for (C, e) in ((11.2706, 1.0), (0.0, 0.0)):
        S = P + 1j * Q
        mag = np.abs(S)
        if C > 0:
            sx, _ = rpc.compensate(P, Q, C, e, SSC)
            sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
        else:
            sxv = np.zeros_like(S)
        m = mag > 0
        v10_, _ = solve(S[m] - sxv[m], sxv[m], SSC, n_iter=10, tol=1e-6)
        v40_, _ = solve(S[m] - sxv[m], sxv[m], SSC, n_iter=60, tol=1e-13)
        full10 = np.zeros(len(S)); full40 = np.zeros(len(S)); full10[m] = v10_; full40[m] = v40_
        conv.append(dict(k=k, C=C, eps=e, max_abs_vuf_diff_pct=float(np.max(np.abs(full10 - full40))),
                         P95_10it=rpc.p95(rpc.vuf10(full10)), P95_60it=rpc.p95(rpc.vuf10(full40))))
        print(conv[-1], flush=True)
out["exact_solver_convergence"] = conv
json.dump(out, open(f"{OUT}/data/checks_b.json", "w"), indent=1)
