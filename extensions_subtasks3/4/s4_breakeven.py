"""Why C* = 0 at Ssc = 1500 MVA: smallest exceedance penalty w3 for which C > 0 is optimal.
Uses the evaluations of arrays_<case>_1500.npz (C and eps grid of s2_reselect.py)."""
import json, numpy as np
from common import *
out = {}
for case, N in [("base", 60), ("suburban", 40)]:
    d = np.load(f"arrays_{case}_1500.npz")
    A = {f: d[f] for f in FIELDS}; c = d["cands"]; C = c[:, 1]
    rows = []
    for w3 in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0]:
        J = J_arrays(C, A, dict(viol=w3))[0]
        ok = n_comply(A) >= order_k(N)
        i = np.where(ok)[0][np.argmin(J[ok])]
        j0 = J[(C == 0)].min()
        rows.append(dict(w3=w3, C=float(C[i]), eps=float(c[i, 0]), J=float(J[i]), J_C0=float(j0)))
    # finest w3 for the switch
    lo, hi = 2.0, 15.0
    def Cstar(w3):
        J = J_arrays(C, A, dict(viol=w3))[0]; ok = n_comply(A) >= order_k(N)
        return C[np.where(ok)[0][np.argmin(J[ok])]]
    if Cstar(hi) > 0:
        while hi - lo > 0.01:
            m = 0.5 * (lo + hi)
            if Cstar(m) > 0: hi = m
            else: lo = m
        sw = hi
    else:
        sw = None
    # initial slope dJ/dC at C -> 0+ for eps = 1 and eps = 0 (first candidate C>0)
    sl = {}
    for e in (0.0, 1.0, 2.0):
        m = (np.abs(c[:, 0] - e) < 1e-9)
        Js, cap, loss, viol = J_arrays(C, A)
        pos = np.where(m & (C > 0))[0]; i1 = pos[np.argmin(C[pos])]; i0 = np.where(m & (C == 0))[0][0]
        sl[str(e)] = dict(C1=float(C[i1]), dcap_dC=float((cap[i1] - cap[i0]) / C[i1]), dloss_dC=float((loss[i1] - loss[i0]) / C[i1]),
                          dviol_dC=float((viol[i1] - viol[i0]) / C[i1]), dJ_dC=float((Js[i1] - Js[i0]) / C[i1]))
    out[case] = dict(by_w3=rows, w3_switch=sw, slopes=sl)
    print(case, "w3 at which C*>0 becomes optimal:", sw)
    for e, v in sl.items(): print("  eps", e, {k: round(x, 1) for k, x in v.items()})
json.dump(out, open("breakeven_1500.json", "w"), indent=1)
