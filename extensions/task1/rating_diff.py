"""Paired bootstrap of the rating reduction of the proposed design vs percentile sizing."""
import sys, json, os
sys.path.insert(0, "/home/claude/code"); os.chdir("/home/claude/code")
import numpy as np
from analyse import load, methods, weekly_cmin
B, SEED = 10000, 20261112
def q(xb, r): return np.sort(xb, axis=1)[:, r - 1]
out = {}
for name, s, N, fac in [("base", load("base"), 60, 1.35), ("suburban", load("suburban", "results_sub"), 40, 1.35)]:
    m = methods(s, 750); e = m["proposed"]["eps"]
    x2, xs = weekly_cmin(s, 750, 2.0), weekly_cmin(s, 750, e)
    rng = np.random.default_rng(SEED); idx = rng.integers(0, N, (B, N)); r = int(np.ceil(0.95 * N))
    red = 100 * (1 - fac * q(xs[idx], r) / q(x2[idx], r))
    out[name] = dict(est=100 * (1 - m["proposed"]["C"] / m["p95"]["C"]), ci=[float(v) for v in np.percentile(red, [2.5, 97.5])],
                     share_pos=float(np.mean(red > 0)))
    print(name, out[name])
json.dump(out, open("/home/claude/subtasks/1/rating_diff.json", "w"), indent=1)
