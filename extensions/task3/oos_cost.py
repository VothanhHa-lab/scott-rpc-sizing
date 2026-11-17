"""Out-of-sample exact-model cost of the exact-model designs on the 90 fresh weeks."""
import sys, json
sys.path.insert(0, "/home/claude/code")
import os; os.chdir("/home/claude/code")
import numpy as np
from exact_sizing import evaluate_exact, J_of, LIM
D = {"prop": (11.270562480978487, 1.0), "conv": (11.825103356680708, 1.9),
     "approx_prop": (10.438726371017976, 1.0), "approx_conv": (11.867963134155023, 2.0)}
res = {}
for name, (C, e) in D.items():
    evs = []
    for k in range(90):
        d = np.load("results_exact/cert_w%03d.npz" % k)
        evs.append(evaluate_exact(d["P"].astype(float), d["Q"].astype(float), C, e))
    J, cap, loss, viol = J_of(evs)
    res[name] = dict(C=C, eps=e, J=J, Jcap=cap, Jloss=loss, Jviol=viol, p95=float(np.mean([x["p95"] for x in evs])),
                     nfail=int(sum(x["p95"] > LIM + 1e-9 for x in evs)), share=100 * float(np.mean([x["share"] for x in evs])))
    print(name, res[name], flush=True)
json.dump(res, open("/home/claude/subtasks/3/oos_cost.json", "w"), indent=1, default=float)
