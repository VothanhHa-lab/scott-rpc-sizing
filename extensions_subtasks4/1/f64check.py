"""Trace the 1e-6 MVA differences: stored weekly cmin (pass1) was computed on the freshly generated float64 week,
whereas stored evaluations (pass2) and this reproduction use the float32 npz store."""
import sys, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *
from rpc_sizing.experiment import week_case, seed_of
st = json.load(open(CODE + "/results/base.json"))
rows = []
for k in (0, 1, 2, 17, 43):
    P64, Q64 = week_case("base", k, seed_of("base"))
    P32, Q32 = load_week("base", k)
    stc = st["weeks"][k]["cmin"]["750"]
    r = dict(k=k)
    for i in (0, 4, 8):
        e = st["eps_grid"][i]
        c64 = rpc.c_min(P64, Q64, e, SSC); c32 = rpc.c_min(P32, Q32, e, SSC)
        r[f"eps{e}"] = dict(stored=stc[i], f64_regen=c64, f32_store=c32, d64=c64 - stc[i], d32=c32 - stc[i])
    r["peakS_stored"] = st["weeks"][k]["peakS"]; r["peakS_f64"] = float(np.hypot(P64, Q64).max()); r["peakS_f32"] = float(np.hypot(P32, Q32).max())
    rows.append(r); print(r, flush=True)
json.dump(rows, open(OUT + "/data/f64check.json", "w"), indent=1)
