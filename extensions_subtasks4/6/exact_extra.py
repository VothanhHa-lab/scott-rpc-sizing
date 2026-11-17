"""Extra exact-model evaluations (60 base weeks, all weeks, no subsampling) of candidates (eps, C) around the equal-exceedance caps.
Writes results/exact_extra.json (records with means + per-week arrays).  nice, single process."""
import sys, os, json, time
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/claude/code")
os.chdir("/home/claude/code")
import numpy as np
import exact_sizing as ex
from rpc_sizing import rpc

CANDS = [(1.9, 12.5), (1.9, 12.75), (1.9, 13.5), (1.9, 13.9),
         (1.0, 10.6), (1.0, 11.15), (0.75, 10.45), (0.75, 11.1), (1.25, 10.9), (0.5, 10.35), (0.5, 11.0)]
OUT = "/home/claude/subtasks4/6/results/exact_extra.json"
done = {}
if os.path.exists(OUT):
    for r in json.load(open(OUT))["records"]:
        done[(r["eps"], r["C"])] = r
t0 = time.time()
recs = []
for (e, C) in CANDS:
    if (e, C) in done:
        recs.append(done[(e, C)]); continue
    p95, ev, el, F, share = [], [], [], [], []
    for k in range(60):
        d = np.load(f"/home/claude/code/results/base_w{k:03d}.npz"); P = d["P"].astype(float); Q = d["Q"].astype(float)
        r = ex.evaluate_exact(P, Q, C, e)
        sx, _ = rpc.compensate(P, Q, C, e, 750.0)
        p95.append(r["p95"]); ev.append(r["E_viol"]); el.append(r["E_loss"]); F.append(float(np.sum(sx ** 2) / C / 3600.0))
    rec = dict(eps=e, C=C, n=60, comply=float(np.mean(np.array(p95) <= 2.0 + 1e-9)), Ev=float(np.mean(ev)), El=float(np.mean(el)), F=float(np.mean(F)),
               p95_mean=float(np.mean(p95)), p95_max=float(np.max(p95)), week_p95=p95, week_Ev=ev, week_El=el, week_F=F)
    recs.append(rec)
    json.dump(dict(note="exact model, 60 base weeks, law (15) sx; per-week arrays", records=recs), open(OUT, "w"))
    print(e, C, "Ev/yr", round(rec["Ev"] * 52.14, 1), "comply", rec["comply"], round(time.time() - t0), "s", flush=True)
print("done", round(time.time() - t0))
