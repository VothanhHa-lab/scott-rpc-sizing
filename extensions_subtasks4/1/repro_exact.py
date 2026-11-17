"""Exact-model reproduction: (a) weekly exact C_min at eps=1.0 and 1.9 on all 60 stored base weeks vs stepA.json;
(b) certification: weekly exact C_min on a subsample of cert weeks (regenerated in float64 as stepB did) vs stepB.json;
(c) Table 13 order statistics / confidences from stepB.json; (d) direct violation counts on all 90 cert weeks.
Usage: repro_exact.py a|b|c"""
import sys, json, time
sys.path.insert(0, "/home/claude/subtasks4/1")
sys.path.insert(0, "/home/claude/code")
from common import *
from scipy import stats
from exact_sizing import cmin_exact
from rpc_sizing.experiment import week_case

part = sys.argv[1]
SA = json.load(open(CODE + "/results_exact/stepA.json"))
SB = json.load(open(CODE + "/results_exact/stepB.json"))
EPS = SA["eps"]
if part == "a":
    cm_st = np.array(SA["cmin"])
    res = {1.0: [], 1.9: []}
    t0 = time.time()
    for k in range(60):
        P, Q = load_week("base", k)
        for e in (1.0, 1.9):
            res[e].append(cmin_exact(P, Q, e))
        if k % 10 == 9:
            print("week", k, round(time.time() - t0), flush=True)
    out = {}
    for e in res:
        j = EPS.index(e)
        d = np.array(res[e]) - cm_st[:, j]
        out[str(e)] = dict(recomputed=res[e], stored=cm_st[:, j].tolist(), maxabsdiff=float(np.abs(d).max()),
                           chat_recomputed=q95(res[e]), chat_stored=q95(cm_st[:, j]), n_exact_equal=int(np.sum(d == 0)))
    json.dump(out, open(f"{OUT}/data/repro_exact_a.json", "w"), indent=1)
    print({e: {k: v for k, v in o.items() if k not in ("recomputed", "stored")} for e, o in out.items()})
elif part == "b":
    cb = np.array(SB["cmin"])
    ks = [0, 7, 13, 29, 41, 52, 66, 74, 81, 89]
    rows = []
    for k in ks:
        P, Q = week_case("base", k, SEED0 + 900000)
        r = dict(k=k)
        for j, e in enumerate(SB["eps"]):
            c = cmin_exact(P, Q, e)
            r[str(e)] = dict(recomputed=c, stored=float(cb[k, j]), diff=c - float(cb[k, j]))
        rows.append(r); print(r, flush=True)
    json.dump(rows, open(f"{OUT}/data/repro_exact_b.json", "w"), indent=1)
elif part == "c":
    cb = np.array(SB["cmin"]); N = cb.shape[0]
    out = {}
    for j, e in enumerate(SB["eps"]):
        x = np.sort(cb[:, j])[::-1]
        out[str(e)] = [dict(k=k, C=float(x[k]), conf_rho5=float(1 - stats.binom.cdf(k, N, 0.05)),
                            conf_rho10=float(1 - stats.binom.cdf(k, N, 0.10))) for k in range(5)]
    json.dump(out, open(f"{OUT}/data/repro_exact_c.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
