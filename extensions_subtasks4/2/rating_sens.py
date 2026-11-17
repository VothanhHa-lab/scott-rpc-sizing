"""Sensitivity of the exact-model VUF (and of the design check) to the Scott leg rating that sets
the leakage impedance (uk = 10.5 % on its own rating, X/R = 30): GRID['trafo_leg_MVA'] is patched in
memory only. RPC fixed at C = 11.27 MVA, eps_u = 1.0 %, Ssc = 750 MVA, 60 high-speed weeks.
The RPC law (compensate) uses the same patched impedance for its busbar-voltage current limit."""
import sys, json, time
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing.params import GRID
import rpc_sizing.network as net
C, EPS, SSC = 11.27, 1.0, 750.0
RATINGS = [20.0, 25.0, 31.5, 40.0, 50.0, 63.0]
out = {}
t0 = time.time()
for Sr in RATINGS:
    GRID["trafo_leg_MVA"] = Sr
    p95, vmax, vmean, bad = [], [], [], 0
    for k in range(60):
        d = np.load("/home/claude/code/results/base_w%03d.npz" % k)
        P = d["P"].astype(float); Q = d["Q"].astype(float)
        S = P + 1j * Q; mag = np.abs(S)
        sx, _ = rpc.compensate(P, Q, C, EPS, SSC)
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
        nz = mag > 0
        v = np.zeros(len(S))
        v[nz], _ = net.solve((S - sxv)[nz], sxv[nz], SSC, n_iter=12, tol=1e-7)
        v10 = rpc.vuf10(v)
        p95.append(rpc.p95(v10)); vmax.append(float(v10.max()))
    p95 = np.array(p95)
    out[str(Sr)] = dict(p95=p95.tolist(), vmax10=vmax, p95_mean=float(p95.mean()), p95_max=float(p95.max()),
                        weeks_viol=int((p95 > 2.0 + 1e-9).sum()), vmax_max=float(max(vmax)))
    print(Sr, out[str(Sr)]["p95_mean"], out[str(Sr)]["p95_max"], out[str(Sr)]["weeks_viol"], f"{time.time()-t0:.0f}s", flush=True)
    json.dump(out, open("/home/claude/subtasks4/2/results/rating_sens.json", "w"))
