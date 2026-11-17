"""Updated rows of Tables tA, t7 and tSub from the corrected line search (reads reselect_*.json)."""
import json, glob
import numpy as np
from common import *
from analyse import methods, weekly_cmin, ci95

NUM = json.load(open(f"{CODE}/results/numbers.json"))
def rj(case, key):
    d = {}
    for f in glob.glob(f"reselect_{case}_*.json"):
        d.update(json.load(open(f)))
    return d
RB, RS = rj("base", ""), rj("suburban", "")
sb = load_summary("base"); ss = load_summary("suburban")
out = {}

# ---------------- Table t7 ----------------
t7_old, t7_new, rows = [], [], []
for S in [500, 750, 1000, 1500, 2000]:
    m = methods(sb, S); x = weekly_cmin(sb, S, 2.0); a, b = ci95(x) if x.std() > 0 else (0.0, 0.0)
    unc = np.mean([w["p95_unc"][str(S)] for w in sb["weeks"]])
    r = RB[str(S)]; n = r["new"]
    def row(C, eps, J):
        if m["p95"]["C"] > 0:
            return (f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & {x[0]:.2f} & ${a:.2f}\\pm{b:.2f}$ & {m['p95']['C']:.2f} & {C:.2f} & {eps:.2f} & {m['p95']['J']:.0f} / {J:.0f}\\\\")
        epstxt = "--" if C == 0 else f"{eps:.2f}"
        return f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & 0 & 0 & 0 & {C:.0f} & {epstxt} & {m['p95']['J']:.0f} / {J:.0f}\\\\" if C == 0 else \
               f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & 0 & 0 & 0 & {C:.2f} & {epstxt} & {m['p95']['J']:.0f} / {J:.0f}\\\\"
    o = r["old"]
    t7_old.append(row(m["proposed"]["C"], m["proposed"]["eps"], m["proposed"]["J"]))
    t7_new.append(row(n["C"], n["eps"], n["J"]))
    rows.append(dict(Ssc=S, old=dict(C=o["C"], eps=o["eps"], J=o["J"]), new=dict(C=n["C"], eps=n["eps"], J=n["J"], n_comply=n["n_comply"]),
                     J_p95=m["p95"]["J"], C_p95=m["p95"]["C"], dJ_pct=100 * (o["J"] - n["J"]) / o["J"],
                     cost_red_old=100 * (1 - o["J"] / m["p95"]["J"]) if m["p95"]["J"] > 0 else None,
                     cost_red_new=100 * (1 - n["J"] / m["p95"]["J"]) if m["p95"]["J"] > 0 else None))
assert "\n".join(t7_old) == NUM["TABLE_7"], "old Table 7 not reproduced"
out["t7"] = dict(rows=rows, tex_old=t7_old, tex_new=t7_new)

# ---------------- Table tSub ----------------
ts_old, ts_new, rowsS = [], [], []
for S in [750, 1000, 1500]:
    m = methods(ss, S); unc = np.mean([w["p95_unc"][str(S)] for w in ss["weeks"]]); r = RS[str(S)]; o, n = r["old"], r["new"]
    def row(C, eps, Ev, J):
        return (f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & {m['p95']['C']:.2f} & {C:.2f} & {eps:.2f} & "
                f"{m['p95']['Eviol']:.1f} / {Ev:.1f} & {m['p95']['J']:.0f} / {J:.0f} & {100*(1-J/m['p95']['J']):.0f}\\\\")
    ts_old.append(row(m["proposed"]["C"], m["proposed"]["eps"], m["proposed"]["Eviol"], m["proposed"]["J"]))
    ts_new.append(row(n["C"], n["eps"], n["Eviol"], n["J"]))
    rowsS.append(dict(Ssc=S, old=dict(C=o["C"], eps=o["eps"], J=o["J"]), new=dict(C=n["C"], eps=n["eps"], J=n["J"], n_comply=n["n_comply"], Eviol=n["Eviol"]), J_p95=m["p95"]["J"]))
assert "\n".join(ts_old) == NUM["TABLE_SUB"], "old Table tSub not reproduced"
out["tSub"] = dict(rows=rowsS, tex_old=ts_old, tex_new=ts_new)

# ---------------- Table tA (Ssc = 750): proposed and percentile-C-optimised columns ----------------
M = methods(sb, 750); r = RB["750"]
def colA(m):   # new column values as in collect_numbers.py
    return [f"{m['C']:.1f}", f"{m['eps']:.1f}", f"{m['p95_mean']:.2f}", f"{100*m['n_comply']/m['N']:.0f}", f"{m['vmax']:.2f}",
            f"{100*m['share']:.1f}", f"{m['Eviol']:.1f}", f"{m['Etr']/1000:.1f}", f"{m['Eloss']:.0f}",
            f"{m['Jcap']:.0f}/{m['Jloss']:.0f}/{m['Jviol']:.0f}", f"{m['J']:.0f}"]
for nm, key in [("proposed", "new"), ("p95_Copt", "p95copt_new")]:
    x = r[key]; x = dict(x, Jcap=x["Jcap"], Jloss=x["Jloss"], Jviol=x["Jviol"])
    out.setdefault("tA_columns_new", {})[nm] = colA(x)
out["tA_row_labels"] = ["C", "eps", "P95", "comply %", "vmax", "share %", "Eviol", "Etr", "Eloss", "J terms", "J"]
out["tA_columns_old"] = {nm: [f"{M[nm]['C']:.1f}", f"{M[nm]['eps']:.1f}", f"{M[nm]['p95_mean']:.2f}", f"{100*M[nm]['comply']:.0f}", f"{M[nm]['vmax']:.2f}",
                              f"{100*M[nm]['share']:.1f}", f"{M[nm]['Eviol']:.1f}", f"{M[nm]['Etr']/1000:.1f}", f"{M[nm]['Eloss']:.0f}",
                              f"{M[nm]['Jcap']:.0f}/{M[nm]['Jloss']:.0f}/{M[nm]['Jviol']:.0f}", f"{M[nm]['J']:.0f}"] for nm in ["proposed", "p95_Copt"]}
json.dump(out, open("tables_updated.json", "w"), indent=1)

print("=== Table t7: old vs new (rows that changed are marked *) ===")
for a, b in zip(t7_old, t7_new):
    print(("  " if a == b else "* "), "OLD", a); 
    if a != b: print("   ", "NEW", b)
print("=== Table tSub ===")
for a, b in zip(ts_old, ts_new):
    print(("  " if a == b else "* "), "OLD", a)
    if a != b: print("   ", "NEW", b)
print("=== tA proposed / p95_Copt: old vs new ===")
for nm in ["proposed", "p95_Copt"]:
    print(nm); print("  old", out["tA_columns_old"][nm]); print("  new", out["tA_columns_new"][nm])
