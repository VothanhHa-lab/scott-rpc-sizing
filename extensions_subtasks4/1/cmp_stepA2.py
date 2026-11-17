"""Per-week comparison of the directly re-evaluated exact-model designs (csv/) with the stored stepA2.json evaluations."""
import sys, json, csv
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

A2 = json.load(open(CODE + "/results_exact/stepA2.json"))
cands = A2["cands"]; ev = A2["evals"]
out = {}
for tag in ("hs_exact_proposed", "hs_exact_percentile_corrected", "hs_exact_percentile_corrected_Copt"):
    rows = list(csv.DictReader(open(f"{OUT}/csv/{tag}.csv")))
    C = float(rows[0]["C"]); e = float(rows[0]["eps_u"])
    i = [j for j, c in enumerate(cands) if abs(c[0] - e) < 1e-9 and abs(c[1] - C) < 1e-9]
    assert len(i) == 1, (tag, i)
    i = i[0]
    m = {}
    for csvk, stk in (("P95", "p95"), ("P99", "p99"), ("vmax10", "vmax"), ("E_viol", "E_viol"), ("E_loss", "E_loss"), ("E_transfer", "E_tr")):
        m[csvk] = max(abs(float(rows[k][csvk]) - ev[k][i][stk]) for k in range(60))
    m["share_gt2_pct"] = max(abs(float(rows[k]["share_gt2_pct"]) / 100 - ev[k][i]["share"]) for k in range(60))
    m["stepA2_index"] = i
    out[tag] = m
    print(tag, m)
json.dump(out, open(f"{OUT}/data/cmp_stepA2.json", "w"), indent=1)
