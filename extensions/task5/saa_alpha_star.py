"""Calibrate alpha* = largest alpha for which SAA-A (eps_u=2) meets the grid-code
criterion (P95 of 10-min VUF <= 2 % in >= 95 % of weeks); bisection in alpha."""
import sys, json
sys.path.insert(0, "/home/claude/subtasks/5")
from saa_baseline import *

case = sys.argv[1]
n = 60 if case == "base" else 40
ks, weeks = load_weeks(case, n, 1)
pool = Pool(weeks)
lo, hi = 0.005, 0.05      # lo meets criterion, hi does not (checked below)
def ev(a):
    C = pool.c_alpha(a, LIM)
    r = evaluate_design(weeks, C, LIM); r["alpha"] = a; return r
rlo, rhi = ev(lo), ev(hi)
if rhi["comply"] >= 0.95:
    out = dict(case=case, note="alpha=5% already meets", best=rhi)
else:
    assert rlo["comply"] >= 0.95
    for _ in range(9):
        mid = (lo * hi) ** 0.5
        r = ev(mid)
        print(f"alpha={mid:.5f} C={r['C']:.3f} comply={r['comply']:.3f} J={r['J']:.1f}", flush=True)
        if r["comply"] >= 0.95:
            lo, rlo = mid, r
        else:
            hi = mid
    out = dict(case=case, best=rlo)
json.dump(out, open(f"/home/claude/subtasks/5/results_alphastar_{case}.json", "w"), indent=1)
print({k: round(v, 3) for k, v in out["best"].items()})
