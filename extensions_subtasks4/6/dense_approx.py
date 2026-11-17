"""Dense candidate grid with the APPROXIMATE model (law (15) + relation (8)) on the stored weeks: base (60 high-speed weeks) or sub (40 suburban weeks).
Same formulas as rpc.evaluate.  Writes results/dense_<case>.json (records: eps, C, n, comply, Ev (%.h/week), El (MWh/week), F)."""
import sys, os, json, time
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/claude/code")
import numpy as np
from rpc_sizing import rpc

case = sys.argv[1]
if case == "base":
    store = "/home/claude/code/results/base_w%03d.npz"; nw = 60
    EPS = [0.5, 0.75, 1.0, 1.25, 2.0]; CS = [round(8.0 + 0.5 * i, 2) for i in range(16)]
else:
    store = "/home/claude/code/results_sub/suburban_w%03d.npz"; nw = 40
    EPS = [0.5, 0.75, 1.0, 1.5, 2.0]; CS = [round(4.5 + 0.25 * i, 2) for i in range(23)]
cands = [(e, c) for e in EPS for c in CS]
acc = {k: dict(p95=[], Ev=[], El=[], F=[]) for k in cands}
t0 = time.time()
for k in range(nw):
    d = np.load(store % k); P = d["P"].astype(float); Q = d["Q"].astype(float)
    for (e, C) in cands:
        sx, v = rpc.compensate(P, Q, C, e, 750.0)
        v10 = rpc.vuf10(v)
        a = acc[(e, C)]
        a["p95"].append(rpc.p95(v10)); a["Ev"].append(float(np.maximum(0.0, v10 - 2.0).sum() / 6.0))
        a["El"].append(rpc.losses_MWh(sx, C)); a["F"].append(float(np.sum(sx ** 2) / C / 3600.0))
    if k % 5 == 0:
        print(case, "week", k, round(time.time() - t0), "s", flush=True)
recs = [dict(eps=e, C=C, n=nw, comply=float(np.mean(np.array(a["p95"]) <= 2.0 + 1e-9)), Ev=float(np.mean(a["Ev"])), El=float(np.mean(a["El"])),
             F=float(np.mean(a["F"])), p95_mean=float(np.mean(a["p95"]))) for (e, C), a in acc.items()]
json.dump(dict(case=case, records=recs), open(f"/home/claude/subtasks4/6/results/dense_{case}.json", "w"))
print("done", round(time.time() - t0))
