"""Task 3 (exact model): refine C around the exact-model optimum (eps = 1 %, C* = 11.27 MVA) with a few additional
exact evaluations on the 60 base weeks; also evaluates the two approximation-(8) designs of Table tEx under the exact
model to count compliant weeks.  Light: 12 candidates x 60 weeks."""
import json, time
import numpy as np
from common import *
import exact_sizing as ex

t0 = time.time()
A2 = json.load(open(f"{CODE}/results_exact/stepA2.json"))
new = [(1.0, c) for c in (10.5, 10.75, 11.0, 11.5, 11.75, 12.0)] + [(0.75, 11.0), (0.75, 11.5), (1.25, 11.0), (1.25, 11.5)] \
      + [(2.0, 11.87), (1.0, 10.4387)]                       # last two: approximation-(8) designs of Table tEx
ev = [[None] * 60 for _ in new]
for k in range(60):
    P, Q = load_week("base", k)
    for j, (e, C) in enumerate(new):
        ev[j][k] = ex.evaluate_exact(P, Q, C, e)
    if k % 10 == 0:
        print("week", k, round(time.time() - t0), "s", flush=True)
out = dict(new=[], stored=[])
def summ(e, C, w):
    J, cap, loss, viol = ex.J_of(w)
    p = np.array([x["p95"] for x in w])
    return dict(eps=e, C=C, J=J, Jcap=cap, Jloss=loss, Jviol=viol, n_comply=int((p <= LIM + 1e-9).sum()), p95_mean=float(p.mean()), p95_max=float(p.max()))
for j, (e, C) in enumerate(new):
    out["new"].append(summ(e, C, ev[j]))
for i, (e, C) in enumerate(A2["cands"]):
    if e in (0.75, 1.0, 1.25, 1.9):
        out["stored"].append(summ(e, C, [w[i] for w in A2["evals"]]))
json.dump(out, open("exact_refine.json", "w"), indent=1)
allc = [x for x in out["new"][:10] + out["stored"] if x["n_comply"] >= 57]
b = min(allc, key=lambda x: x["J"])
print("best exact candidate (stored + refined, eps in {0.75,1,1.25,1.9}):", {k: round(v, 3) for k, v in b.items()})
for x in sorted(out["new"] + [s for s in out["stored"] if s["eps"] == 1.0], key=lambda x: (x["eps"], x["C"])):
    print(f"eps={x['eps']:.2f} C={x['C']:.3f} J={x['J']:.1f} comply={x['n_comply']}/60 P95mean={x['p95_mean']:.2f}")
print("done", round(time.time() - t0), "s")
