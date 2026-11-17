"""Task 2: quantile definition and number of compliant weeks of every reported design.
Uses only stored evaluations (results*/..json, results_exact/stepA*.json)."""
import json, glob, numpy as np
from common import *
from analyse import methods, weekly_cmin   # noqa  (code base, read-only)

out = dict(rule="C_hat = X_(ceil(0.95 N)) of the weekly minimum ratings (numpy quantile, method='inverted_cdf')")
# (a) numpy really returns X_(ceil(0.95 N))
chk = {}
rng = np.random.default_rng(1)
for N in (40, 60, 90, 120):
    x = rng.random(N)
    chk[N] = dict(k=order_k(N), numpy_equals=bool(np.quantile(x, .95, method="inverted_cdf") == np.sort(x)[order_k(N) - 1]),
                  max_exceeding_weeks=N - order_k(N), min_compliant=order_k(N))
out["numpy_check"] = chk
# P95 of the 1008 10-min values of a week
n10 = 604800 // 600
out["p95_10min"] = dict(n=n10, k=order_k(n10), max_values_above=n10 - order_k(n10), share_above_max=(n10 - order_k(n10)) / n10)

rows = []
def add(table, label, case, Ssc, name, m, s):
    N = s["n_weeks"]; i = m["idx"]
    ev = [wk[i] for wk in s["design"][str(Ssc)]["evals"]]
    p95 = np.array([e["p95"] for e in ev])
    cmin = weekly_cmin(s, Ssc, m["eps"]) if m["eps"] in s["eps_grid"] else None
    r = dict(table=table, label=label, case=case, Ssc=Ssc, design=name, C=m["C"], eps=m["eps"], N=N,
             need=order_k(N), n_comply=int((p95 <= LIM + 1e-9).sum()), n_comply_tol1e6=int((p95 <= LIM + 1e-6).sum()),
             n_exceed=int((p95 > LIM + 1e-9).sum()), max_p95=float(p95.max()))
    if cmin is not None and m["C"] > 0:
        r["n_cmin_le_C"] = int((cmin <= m["C"] + 1e-9).sum())
    rows.append(r)

for case, d, Sscs, tab in [("base", "results", [500, 750, 1000, 1500, 2000], "tA/t7"),
                           ("suburban", "results_sub", [750, 1000, 1500], "tSub")]:
    s = load_summary(case)
    for S in Sscs:
        M = methods(s, S)
        for name in ["full", "peak", "p95", "p95_Copt", "proposed"]:
            add(tab, f"{case} Ssc={S}", case, S, name, M[name], s)
for f in sorted(glob.glob(f"{CODE}/results40/*.json")):
    case = f.split("/")[-1][:-5]; s = load_summary(case); M = methods(s, 750)
    for name in ["peak", "p95", "p95_Copt", "proposed"]:
        add("t8", f"{case} Ssc=750", case, 750, name, M[name], s)
sb = load_summary("base")
add("t8", "base Ssc=750", "base", 750, "proposed", methods(sb, 750)["proposed"], sb)

# exact model (tEx): stepA2
A2 = json.load(open(f"{CODE}/results_exact/stepA2.json")); cm = np.array(json.load(open(f"{CODE}/results_exact/stepA.json"))["cmin"])
ex = []
def exrow(label, eps, C):
    for i, (e, c) in enumerate(A2["cands"]):
        if abs(e - eps) < 1e-9 and abs(c - C) < 0.02:
            p = np.array([w[i]["p95"] for w in A2["evals"]]); EPSL = [0.0,.25,.5,.75,1.0,1.25,1.5,1.75,1.9]
            j = EPSL.index(eps)
            ex.append(dict(label=label, eps=e, C=c, N=60, need=57, n_comply=int((p <= LIM + 1e-9).sum()),
                           n_exact_cmin_le_C=int((cm[:, j] <= c + 1e-9).sum()), mean_p95=float(p.mean()), max_p95=float(p.max())))
            return
    raise KeyError(label)
exrow("corrected percentile (exact), eps=1.9", 1.9, 11.825103356680708)
exrow("proposed (exact), eps=1.0", 1.0, 11.270562480978487)
# approximate-model designs evaluated with the exact model: tEx rows 1 and 3
for label, eps, C in [("percentile (12) approx, eps=2.0 (exact eval)", 2.0, 11.87), ("proposed approx, eps=1.0 (exact eval)", 1.0, 10.44)]:
    # stepA2 candidates are Chat_exact*factor; approx designs were evaluated in an earlier run (fig F) -> not in stepA2
    pass
out["exact_rows"] = ex
out["rows"] = rows
json.dump(out, open("quantile_check.json", "w"), indent=1)

bad = [r for r in rows if r["design"] in ("p95", "proposed", "p95_Copt") and r["n_comply"] < r["need"]]
print("rows", len(rows), "designs (p95/proposed/p95_Copt) below the required count:", len(bad))
for r in bad: print("  ", r)
print("tA/t7 base:")
for r in rows:
    if r["case"] == "base" and r["design"] in ("p95", "proposed", "p95_Copt"):
        print(f"  Ssc={r['Ssc']:5d} {r['design']:9s} C={r['C']:6.2f} eps={r['eps']:.2f} comply={r['n_comply']}/{r['N']} (need {r['need']}) cmin<=C:{r.get('n_cmin_le_C')}")
print("tSub:")
for r in rows:
    if r["case"] == "suburban" and r["design"] in ("p95", "proposed", "p95_Copt"):
        print(f"  Ssc={r['Ssc']:5d} {r['design']:9s} C={r['C']:6.2f} eps={r['eps']:.2f} comply={r['n_comply']}/{r['N']} (need {r['need']}) cmin<=C:{r.get('n_cmin_le_C')}")
print("t8:")
for r in rows:
    if r["table"] == "t8" and r["design"] in ("p95", "proposed"):
        print(f"  {r['case']:14s} {r['design']:9s} C={r['C']:6.2f} eps={r['eps']:.2f} comply={r['n_comply']}/{r['N']} (need {r['need']}) cmin<=C:{r.get('n_cmin_le_C')}")
print("exact:", json.dumps(ex, indent=1))
