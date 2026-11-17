"""Monotonicity of P95(C) in the CONSISTENT model (bisection for Chat' relies on it): same 5 weeks per line as t1_monotone.py,
eps in {1.0, 1.9}, 25 points C = 0 .. 1.2*Chat'(1.9) (hs) resp. 1.2*Chat(eps) of the v7 model."""
import sys
from common_cons import *
out = {}
for line in ("hs", "sub"):
    r1 = json.load(open(f"{HERE}/results_t1_{line}.json"))
    weeks = r1["weeks"]
    stepA = json.load(open(f"{HERE}/stepA_{line}.json"))
    for eps in (1.0, 1.9):
        chat = stepA["chat"][EPS.index(eps)]
        Cg = np.linspace(0, 1.2 * chat, 25)
        for k in weeks:
            P, Q = load_week(line, k)
            p = np.array([p95_model(P, Q, float(C), eps, "cons") for C in Cg])
            df = np.diff(p)
            out[f"{line}_{eps}_{k}"] = dict(p95=p.tolist(), max_rise=float(df.max()), n_up=int((df > 1e-9).sum()), C=Cg.tolist())
            print(line, eps, k, "max rise %.2e" % df.max(), flush=True)
json.dump(out, open(f"{HERE}/results_t1c_cons.json", "w"))
print("total non-monotone:", sum(v["n_up"] > 0 for v in out.values()), "of", len(out))
