"""Exact-model evaluation (60 base weeks) of the designs obtained with approximation (8)."""
import sys, json
sys.path.insert(0, "/home/claude/code")
import os; os.chdir("/home/claude/code")
import numpy as np
from exact_sizing import evaluate_exact, load_week, J_of, LIM
D = {"approx_proposed": (10.438726371017976, 1.0), "approx_conv": (11.867963134155023, 2.0)}
res = {}
for name, (C, e) in D.items():
    evs = [evaluate_exact(*load_week("base", k, "results/base_w%03d.npz"), C, e) for k in range(60)]
    J, cap, loss, viol = J_of(evs)
    res[name] = dict(C=C, eps=e, J=J, Jcap=cap, Jloss=loss, Jviol=viol,
                     p95=float(np.mean([x["p95"] for x in evs])), p95max=float(np.max([x["p95"] for x in evs])),
                     comply=float(np.mean([x["p95"] <= LIM + 1e-9 for x in evs])),
                     share=100 * float(np.mean([x["share"] for x in evs])),
                     Eviol=float(np.mean([x["E_viol"] for x in evs]) * 52.14),
                     Eloss=float(np.mean([x["E_loss"] for x in evs]) * 52.14),
                     Etr=float(np.mean([x["E_tr"] for x in evs]) * 52.14 / 1000), nfail=int(sum(x["p95"] > LIM + 1e-9 for x in evs)))
    print(name, res[name], flush=True)
json.dump(res, open("/home/claude/subtasks/3/approx_designs_exact.json", "w"), indent=1)
