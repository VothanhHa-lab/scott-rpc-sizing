"""Print a compact text summary of every result file (used to write NOTES.md by hand with literal numbers)."""
import json, os
import numpy as np
from common5 import HERE

for line in ("hs", "sub"):
    f = f"{HERE}/stepA_{line}.json"
    if os.path.exists(f):
        d = json.load(open(f))
        print(line, "Chat(eps):", {e: round(c, 3) for e, c in zip(d["eps"], d["chat"])}, "order stat", d["order_stat"])
    f = f"{HERE}/designs_{line}.json"
    if os.path.exists(f):
        d = json.load(open(f))
        for nm in ("design_i", "design_ii", "design_iii", "design_ii_factor_grid_only", "design_iii_factor_grid_only"):
            s = d[nm]
            print(f"  {line} {nm:28s} eps={s['eps']:.2f} C={s['C']:.3f} J={s['J']:.2f} cap={s['Jcap']:.1f} loss={s['Jloss']:.1f} "
                  f"viol={s['Jviol']:.1f} comply={s['n_comply']}/{s['n_weeks']} p95mean={s['p95_mean']:.3f} "
                  f"Eviol={s['E_viol_h_yr']:.1f} share={s['share_above_pct']:.2f}")
        print("  per eps:", [(p['eps'], round(p['C'], 2), round(p['J'], 1)) for p in d["per_eps"]])
    f = f"{HERE}/summary_t3_{line}.json"
    if os.path.exists(f):
        d = json.load(open(f))
        for nm in ("design_i", "design_ii", "design_iii"):
            s = d[nm]
            print(f"  FRESH {line} {nm}: eps={s['eps']} C={s['C']:.3f} viol={s['n_viol']}/{s['n_weeks']} CP95={s['cp95_upper']:.4f} "
                  f"J={s['J']:.1f} ({s['Jcap']:.1f}/{s['Jloss']:.1f}/{s['Jviol']:.1f}) p95mean={s['p95_mean']:.3f} p95max={s['p95_max']:.3f}")
        for k in d:
            if k.startswith("paired"):
                print("  ", line, k, d[k])
f = f"{HERE}/summary_t1.json"
if os.path.exists(f):
    for k, v in json.load(open(f)).items():
        print("T1", k, v)
