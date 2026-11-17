"""Direct exact-model evaluation of a fixed rating on the fresh certification weeks (needs results_exact/cert_w*.npz).
usage: python cert_direct.py C eps [C eps ...]   -> counts weeks with P95 > 2 %"""
import sys, json
sys.path.insert(0, "/home/claude/code")
import numpy as np
from exact_sizing import p95_exact
from scipy import stats
args = [float(a) for a in sys.argv[1:]]
des = list(zip(args[0::2], args[1::2]))
N = int(__import__("os").environ.get("NCERT", 90))
res = {}
for (C, e) in des:
    p = []
    for k in range(N):
        d = np.load("/home/claude/code/results_exact/cert_w%03d.npz" % k)
        p.append(p95_exact(d["P"].astype(float), d["Q"].astype(float), C, e))
    p = np.array(p); nv = int((p > 2.0 + 1e-9).sum())
    res["%.4f_%.2f" % (C, e)] = dict(C=C, eps=e, nviol=nv, emp=nv / N, cp_up95=float(stats.beta.ppf(.95, nv + 1, N - nv)),
                                      p95_mean=float(p.mean()), p95_max=float(p.max()), p95=p.tolist())
    print(C, e, nv, nv / N, res["%.4f_%.2f" % (C, e)]["cp_up95"], p.mean(), p.max(), flush=True)
json.dump(res, open("/home/claude/subtasks/3/cert_direct.json", "w"), indent=1)
