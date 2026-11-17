"""What if the RPC alpha-leg current limit used the exact busbar voltage? sizing law rpc.compensate limits
|s_x| <= 0.96*C*min(U_approx,1) with an approximate U; the exact model gives |s_x|/U_alpha up to 1.029 C.
Here |s_x| is additionally clipped to C*U_alpha(exact) (1 pu rated current) and the exact model is re-solved
(2 passes); the change in the weekly P95 of the 10-min VUF is reported."""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/code"); sys.path.insert(0, "/home/claude/subtasks4/2")
from rpc_sizing import rpc
import compute_legs as cl
C = cl.C
res = []
for k in range(60):
    z = np.load(f"{cl.OUT}/legs_w{k:03d}.npz")
    P = z["P_L"].astype(float); Q = z["Q_L"].astype(float)
    S = P + 1j * Q; mag = np.abs(S); nz = mag > 0
    sx = z["sx_abs"].astype(float)
    Ua = z["U_alpha"].astype(float)
    for _ in range(2):
        sx = np.minimum(sx, C * np.where(Ua > 0, Ua, 1.0))
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
        ua, ub, Ia, Ib, vuf, r = cl.solve_full((S - sxv)[nz], sxv[nz])
        Ua = np.zeros(len(S)); Ua[nz] = np.abs(ua)
    v = np.zeros(len(S)); v[nz] = vuf
    p95_new = rpc.p95(rpc.vuf10(v))
    v0 = z["vuf"].astype(float)
    p95_old = rpc.p95(rpc.vuf10(v0))
    res.append(dict(week=k, p95_old=p95_old, p95_new=p95_new, n_gt1_after=int(((sx / np.maximum(Ua, 1e-9)) / C > 1.0 + 1e-6)[nz].sum()),
                    max_after=float(((sx / np.maximum(Ua, 1e-9)) / C)[nz].max()),
                    sx_reduction_MWh=float((z["sx_abs"].astype(float) - sx).sum() / 3600)))
    if k % 10 == 0: print(k, flush=True)
d = np.array([r["p95_new"] - r["p95_old"] for r in res])
out = dict(weeks=res, max_dP95=float(d.max()), min_dP95=float(d.min()), p95_new_max=max(r["p95_new"] for r in res),
           p95_old_max=max(r["p95_old"] for r in res), weeks_viol_new=int(sum(r["p95_new"] > 2.0 + 1e-9 for r in res)))
json.dump(out, open("/home/claude/subtasks4/2/results/exact_limit_check.json", "w"))
print({k: v for k, v in out.items() if k != "weeks"})
