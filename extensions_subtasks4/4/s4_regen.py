"""(c1) Regeneration: v7 (return to the grid/other trains) vs no return to the 110 kV grid (clip), lumped substation.
usage: python s4_regen.py CASE [NW]  -> regen_{case}.json"""
import sys, json, time
import numpy as np
from dz import *
from cat import clip_variants
case = sys.argv[1]; NW = int(sys.argv[2]) if len(sys.argv) > 2 else 40
t0 = time.time()
log = lambda s: print(f"[{case} {time.time()-t0:.0f}s] {s}", flush=True)
V = {}; ACC = {}
tanphi = None
for k in range(NW):
    d = np.load(f"data/{case}_w{k:03d}.npz")
    P, Q = d["b_P"].astype(float), d["b_Q"].astype(float)
    tanphi = float(np.tan(np.arccos(0.998)))
    vv = clip_variants(P, Q, d["b_Sp"], d["b_Sn"], tanphi)
    for nm, (p_, q_, acc) in vv.items():
        V.setdefault(nm, []).append((p_, q_)); ACC.setdefault(nm, []).append(acc)
acc_sum = {nm: {k: float(np.mean([a[k] for a in ACC[nm]])) for k in ACC[nm][0]} for nm in ACC}
out = dict(accounting_MWh_per_week=acc_sum, designs={})
for nm in ("v7", "noreturn_onboard", "noreturn_wayside"):
    log(f"design {nm}")
    out["designs"][nm] = design(V[nm], Ssc=750.0, log=log)
    json.dump(out, open(f"regen_{case}.json", "w"))
# v7 design applied to the no-return weeks
pv = out["designs"]["v7"]["proposed"]
out["transfer"] = {nm: evaluate_design(V[nm], pv["C"], pv["eps"]) for nm in ("noreturn_onboard", "noreturn_wayside")}
json.dump(out, open(f"regen_{case}.json", "w"))
log("done")
