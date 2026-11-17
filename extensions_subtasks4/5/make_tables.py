"""Write LaTeX tables (literal numbers) and a text digest from the result JSON files of sub-task 4.5.
 table_mono.tex        monotonicity of P95[VUF10](C), exact model, 5 weeks per line (+ extended range if available)
 table_designs.tex     designs (i)-(iii), both lines, v7 model (capacity limit with approximate U) and consistent model (exact U)
 table_fresh_v7.tex    fresh weeks, set A (hs seed SEED0+950000, sub SEED0+960000): v7-model designs, evaluated in both models
 table_fresh_cons.tex  fresh weeks, set B (hs SEED0+970000, sub SEED0+980000): consistent-model designs, evaluated in both models
 digest.txt            all numbers used in NOTES.md
"""
import json, os
import numpy as np
from common5 import HERE

L = {"hs": "High-speed", "sub": "Suburban"}
NM = {"design_i": "(i) corrected percentile", "design_ii": "(ii) corrected percentile, $C$ optimised",
      "design_iii": "(iii) proposed $(C,\\varepsilon_u)$"}
dig = []


def P(*a):
    dig.append(" ".join(str(x) for x in a))


def jl(p):
    return json.load(open(p)) if os.path.exists(p) else None


# ------------------------------------------------------------------ monotonicity
s1 = jl(f"{HERE}/summary_t1.json")
if s1:
    rows = []
    for line in ("hs", "sub"):
        for eps in (0.0, 1.0, 1.9):
            a = s1[f"{line}_none_{eps}"]; b = s1[f"{line}_bg1_{eps}"]
            rows.append(f"{L[line]} & {eps:.1f} & {a['n_monotone']}/{a['n']} & {a['max_rise_pp']:.1e} & {a['n_upclosed']}/{a['n']} & "
                        f"{b['n_monotone']}/{b['n']} & {b['max_rise_pp']:.1e} & {b['n_feasible']}/{b['n']} \\\\")
    tex = ("\\begin{tabular}{llcccccc}\n\\hline\nLine & $\\varepsilon_u$ (\\%) & \\multicolumn{3}{c}{No background} & "
           "\\multicolumn{3}{c}{Background 1\\,\\%, worst phase} \\\\\n & & monotone & max rise (pp) & feasible set up-closed & monotone & max rise (pp) & "
           "feasible on grid \\\\\n\\hline\n" + "\n".join(rows) + "\n\\hline\n\\end{tabular}\n")
    open(f"{HERE}/table_mono.tex", "w").write(tex)


s1b = jl(f"{HERE}/summary_t1b.json")
if s1b:
    rows = []
    for line in ("hs", "sub"):
        for eps in (0.0, 1.0):
            b = s1b[f"{line}_bg1_{eps}"]
            rows.append(f"{L[line]} & {eps:.1f} & {b['n_monotone']}/{b['n']} & {b['max_rise_pp']:.1e} & {b['n_feasible']}/{b['n']} & {b['n_upclosed']}/{b['n']} \\\\")
    open(f"{HERE}/table_mono_ext.tex", "w").write("\\begin{tabular}{llcccc}\n\\hline\nLine & $\\varepsilon_u$ (\\%) & monotone & max rise (pp) & feasible & feasible set up-closed \\\\\n\\hline\n"
        + "\n".join(rows) + "\n\\hline\n\\end{tabular}\n")

# ------------------------------------------------------------------ designs
rows = []
for line in ("hs", "sub"):
    d7 = jl(f"{HERE}/designs_{line}.json"); dc = jl(f"{HERE}/designs_cons_{line}.json")
    for nm in ("design_i", "design_ii", "design_iii"):
        a = d7[nm]
        r = f"{L[line]} & {NM[nm]} & {a['eps']:.2f} & {a['C']:.2f} & {a['J']:.1f} & {a['Jcap']:.1f} / {a['Jloss']:.1f} / {a['Jviol']:.1f} & {a['n_comply']}/{a['n_weeks']}"
        P("DESIGN v7", line, nm, f"eps={a['eps']:.2f} C={a['C']:.3f} J={a['J']:.2f} cap={a['Jcap']:.1f} loss={a['Jloss']:.1f} viol={a['Jviol']:.1f} comply={a['n_comply']}/{a['n_weeks']} Eviol={a['E_viol_h_yr']:.1f} share={a['share_above_pct']:.2f} p95mean={a['p95_mean']:.3f}")
        if dc:
            b = dc[nm]
            r += f" & {b['eps']:.2f} & {b['C']:.2f} & {b['J']:.1f} & {b['Jcap']:.1f} / {b['Jloss']:.1f} / {b['Jviol']:.1f} & {b['n_comply']}/{b['n_weeks']}"
            P("DESIGN cons", line, nm, f"eps={b['eps']:.2f} C={b['C']:.3f} J={b['J']:.2f} cap={b['Jcap']:.1f} loss={b['Jloss']:.1f} viol={b['Jviol']:.1f} comply={b['n_comply']}/{b['n_weeks']} Eviol={b['E_viol_h_yr']:.1f} share={b['share_above_pct']:.2f} p95mean={b['p95_mean']:.3f}")
        rows.append(r + " \\\\")
    rows.append("\\hline")
    for tag, d in (("v7", d7), ("cons", dc)):
        if d:
            Ji, Jii, Jiii = d["design_i"]["J"], d["design_ii"]["J"], d["design_iii"]["J"]
            P("REL", line, tag, f"J(iii)/J(i)-1 = {100*(Jiii/Ji-1):.1f} %  J(iii)/J(ii)-1 = {100*(Jiii/Jii-1):.1f} %  J(ii)/J(i)-1 = {100*(Jii/Ji-1):.1f} %  "
              f"capex+loss: (i) {d['design_i']['Jcap']+d['design_i']['Jloss']:.1f} (ii) {d['design_ii']['Jcap']+d['design_ii']['Jloss']:.1f} (iii) {d['design_iii']['Jcap']+d['design_iii']['Jloss']:.1f}"
              f"  per eps: {[(p['eps'], round(p['C'], 2), round(p['J'], 1)) for p in d['per_eps']]}")
hdr = ("\\begin{tabular}{llcccccccccccc}\n\\hline\n & & \\multicolumn{5}{c}{Model v7 (approximate $U$ in the cap)} & & "
       "\\multicolumn{6}{c}{Consistent model (exact $U$ in the cap)} \\\\\n Line & Design & $\\varepsilon_u$ & $C$ & $J$ & capital / losses / exceedance & compliant & "
       "$\\varepsilon_u$ & $C$ & $J$ & capital / losses / exceedance & compliant \\\\\n\\hline\n")
open(f"{HERE}/table_designs.tex", "w").write(hdr.replace("{llcccccccccccc}", "{llcccccccccccc}") + "\n".join(rows) + "\n\\end{tabular}\n")


# ------------------------------------------------------------------ fresh
def fresh_table(fname, setname, fam, prim_files, cross_files, title):
    rows = []
    for line in ("hs", "sub"):
        pr = jl(prim_files[line]); cr = jl(cross_files[line])
        if not pr:
            continue
        for nm in ("design_i", "design_ii", "design_iii"):
            a = pr[nm]
            P("FRESH", setname, fam, line, nm, f"eps={a['eps']} C={a['C']:.3f} viol={a['n_viol']}/{a['n_weeks']} CP95={100*a['cp95_upper']:.1f}% J={a['J']:.1f} ({a['Jcap']:.1f}/{a['Jloss']:.1f}/{a['Jviol']:.1f}) p95mean={a['p95_mean']:.3f} p95max={a['p95_max']:.3f} share={a['share_above_pct']:.2f} Eviol={a['E_viol_h_yr']:.1f}")
            r = (f"{L[line]} & {NM[nm]} & {a['eps']:.2f} & {a['C']:.2f} & {a['n_viol']}/{a['n_weeks']} & {100*a['rate']:.1f} & {100*a['cp95_upper']:.1f} & "
                 f"{a['J']:.1f} & {a['Jcap']:.1f} / {a['Jloss']:.1f} / {a['Jviol']:.1f}")
            if cr:
                b = cr[nm]
                r += f" & {b['n_viol']}/{b['n_weeks']} & {100*b['cp95_upper']:.1f} & {b['J']:.1f}"
                P("FRESH-cross", setname, fam, line, nm, f"viol={b['n_viol']}/{b['n_weeks']} CP95={100*b['cp95_upper']:.1f}% J={b['J']:.1f} ({b['Jcap']:.1f}/{b['Jloss']:.1f}/{b['Jviol']:.1f})")
            rows.append(r + " \\\\")
        for k in pr:
            if k.startswith("paired"):
                P("PAIRED", setname, fam, line, k, pr[k])
        rows.append("\\hline")
    return rows


tab = {}
for setname, fam, own, other, fname in (("A", "v7", "v7", "cons", "table_fresh_v7.tex"), ("B", "cons", "cons", "v7", "table_fresh_cons.tex")):
    pf = {l: f"{HERE}/summary_t3_{l}.json" if (setname == "A") else f"{HERE}/summary_t3b_{l}_B_cons_cons.json" for l in ("hs", "sub")}
    cf = {l: f"{HERE}/summary_t3b_{l}_{setname}_{fam}_{other}.json" for l in ("hs", "sub")}
    rows = fresh_table(fname, setname, fam, pf, cf, "")
    mod1 = "v7" if own == "v7" else "consistent"; mod2 = "consistent" if own == "v7" else "v7"
    tex = ("\\begin{tabular}{llcccccccccc}\n\\hline\n & & & & \\multicolumn{6}{c}{Evaluated with the " + mod1 + " model} & \\multicolumn{3}{c}{" + mod2 +
           " model} \\\\\n Line & Design & $\\varepsilon_u$ & $C$ & violating weeks & rate (\\%) & CP95 upper (\\%) & $J$ & capital / losses / exceedance & violating & CP95 (\\%) & $J$ \\\\\n\\hline\n"
           + "\n".join(rows) + "\n\\end{tabular}\n")
    open(f"{HERE}/{fname}", "w").write(tex)
open(f"{HERE}/digest.txt", "w").write("\n".join(dig) + "\n")
print("\n".join(dig))
