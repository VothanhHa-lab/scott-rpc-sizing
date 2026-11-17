"""SAA-C: joint (eps_u, C) chance constraint on the pooled 10-min VUF values.

  min_{eps_u, C}  capital + losses   s.t.  (1/N10) sum_j 1{VUF_10min,j > 2 %} <= alpha10
(pooled over all stored weeks; alpha10 = 5 % is the pooled analogue of the grid-code
percentile criterion).  Evaluated with the same criteria/cost as Table A.
Run: nice -n 15 python3 saa10_baseline.py base|suburban
"""
import sys, json, time
import numpy as np
sys.path.insert(0, "/home/claude/subtasks/5")
sys.path.insert(0, "/home/claude/code")
from saa_baseline import load_weeks, evaluate_design, SSC, LIM, rpc

EPS = [0.0, 0.5, 1.0, 1.5, 2.0]
ALPHA10 = [0.05, 0.02, 0.01]


def pooled_v10(weeks, C, eps):
    return np.concatenate([rpc.vuf10(rpc.compensate(P, Q, C, eps, SSC)[1]) for P, Q in weeks])


def c_alpha10(weeks, alpha, eps, hi=16.0, tol=0.01):
    lo = 0.0
    f = lambda C: np.mean(pooled_v10(weeks, C, eps) > LIM + 1e-9) <= alpha
    if f(0.0):
        return 0.0
    while not f(hi):          # make sure the bracket is feasible at its upper end
        lo, hi = hi, hi * 1.5
        assert hi < 80.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid):
            hi = mid
        else:
            lo = mid
    return hi


def main():
    case = sys.argv[1]
    n = 60 if case == "base" else 40
    t0 = time.time()
    ks, weeks = load_weeks(case, n, 1)
    out = dict(case=case, weeks=ks)
    for a in ALPHA10:
        cand = []
        for e in EPS:
            C = c_alpha10(weeks, a, e)
            r = evaluate_design(weeks, C, e)
            r["alpha10"] = a
            cand.append(r)
            print(f"C alpha10={a:g} eps={e:g} C={C:.3f} comply={r['comply']:.2f} J_capl={r['J_caploss']:.0f} J={r['J']:.0f} t={time.time()-t0:.0f}", flush=True)
        out[f"{a:g}"] = dict(best=min(cand, key=lambda r: r["J_caploss"]), grid=cand)
        with open(f"/home/claude/subtasks/5/results10_{case}.json", "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
