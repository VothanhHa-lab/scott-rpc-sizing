"""Reproduce agent 1's sensitivity (subtasks4/1/data/checks_d.json): 20 base weeks (every 3rd), consistent capacity limit."""
import sys
from common_cons import *
for C, eps in ((11.2706, 1.0), (11.8251, 1.9)):
    for model in ("v7", "cons"):
        ev = [evaluate_model(*load_week("hs", k), C, eps, model) for k in range(0, 60, 3)]
        J = J_of(ev)
        print(model, C, eps, "J=%.1f (viol %.1f)" % (J[0], J[3]), "comply", sum(e["p95"] <= LIM + 1e-9 for e in ev), "/", len(ev),
              "P95 mean %.3f" % np.mean([e["p95"] for e in ev]), flush=True)
