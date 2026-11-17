"""Table t13 (cost-weight sensitivity, Ssc = 750, 60 weeks) re-selected on the union grid."""
import json, numpy as np
from common import *
from analyse import methods
d = np.load("arrays_base_750.npz"); A = {f: d[f] for f in FIELDS}; c = d["cands"]; C = c[:, 1]; E = c[:, 0]; N = 60
sb = load_summary("base")
lab = [("Base", {}), ("No exceedance penalty ($w_3=0$)", dict(viol=0)), ("Penalty 0.5~kUSD/(\\%$\\cdot$h)", dict(viol=0.5)),
       ("Penalty 5~kUSD/(\\%$\\cdot$h)", dict(viol=5)), ("Energy price 40~USD/MWh", dict(price=40)),
       ("Energy price 160~USD/MWh", dict(price=160)), ("Converter cost 75~kUSD/MVA", dict(cost=75)),
       ("Converter cost 225~kUSD/MVA", dict(cost=225))]
rows, tex_new, tex_old = [], [], []
Cmax_eval = C.max()
for l, w in lab:
    J = J_arrays(C, A, w)[0]; ok = n_comply(A) >= order_k(N)
    jo = J[:72]; io = np.argmin(jo)                                # old procedure (old candidates only)
    idx = np.where(ok)[0]; i = idx[np.argmin(J[idx])]
    m = methods(sb, 750, w); jp = m["p95"]["J"]
    # is the optimum interior with respect to the evaluated absolute grid?  (largest abs-grid C at that eps)
    mE = np.abs(E - E[i]) < 1e-9
    rows.append(dict(label=l, old=dict(C=float(C[io]), eps=float(E[io]), J=float(jo[io])), new=dict(C=float(C[i]), eps=float(E[i]), J=float(J[i]), n_comply=int(n_comply(A)[i])),
                     J_p95=jp, max_abs_C_at_eps=float(C[mE].max())))
    f = lambda C_, e_, J_: f"{l} & {C_:.2f} & {e_:.2f} & {J_:.0f} & {jp:.0f} & {100*(1-J_/jp):.0f}\\\\"
    tex_old.append(f(C[io], E[io], jo[io])); tex_new.append(f(C[i], E[i], J[i]))
import json as _j
NUM = _j.load(open(f"{CODE}/results/numbers.json"))
assert "\n".join(tex_old) == NUM["TABLE_13"], "old t13 not reproduced"
json.dump(dict(rows=rows, tex_old=tex_old, tex_new=tex_new), open("t13_updated.json", "w"), indent=1)
for a, b in zip(tex_old, tex_new):
    print(("  " if a == b else "* ") + "OLD", a)
    if a != b: print("   NEW", b)
print("largest evaluated C at any eps:", Cmax_eval)
