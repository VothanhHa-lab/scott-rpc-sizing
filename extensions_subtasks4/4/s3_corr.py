"""(b) Correlated delays: independent-delay baseline vs delay episodes on the SAME seeds.
usage: python s3_corr.py CASE [NW]   -> corr_{case}.json"""
import sys, json, time
import numpy as np
from dz import *
case = sys.argv[1]; NW = int(sys.argv[2]) if len(sys.argv) > 2 else 40
t0 = time.time()
log = lambda s: print(f"[{case} {time.time()-t0:.0f}s] {s}", flush=True)
W = {"b": [], "c": []}
for k in range(NW):
    d = np.load(f"data/{case}_w{k:03d}.npz")
    for sc in W:
        W[sc].append((d[f"{sc}_P"].astype(float), d[f"{sc}_Q"].astype(float)))
out = {}
for sc, nm in (("b", "independent"), ("c", "correlated")):
    log(f"design {nm}")
    r = design(W[sc], Ssc=750.0, log=log)
    out[nm] = r
    json.dump({k: v for k, v in out.items()}, open(f"corr_{case}.json", "w"))
# transfer: baseline design applied to correlated weeks
pb = out["independent"]["proposed"]; pc = out["correlated"]["proposed"]
out["transfer"] = dict(
    base_design_on_corr=evaluate_design(W["c"], pb["C"], pb["eps"]),
    corr_design_on_base=evaluate_design(W["b"], pc["C"], pc["eps"]))
# percentile design (eps=2, C=Chat) on the two sets for the table
for nm in ("independent", "correlated"):
    pr = out[nm]["percentile"]
out["Ssc"] = 750.0
json.dump(out, open(f"corr_{case}.json", "w"))
log("done")
