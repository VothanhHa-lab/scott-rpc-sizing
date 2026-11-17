"""Assemble LaTeX tables/rows (tables_new.tex) from the JSON results of s1..s6 (and the t8 re-selections that finished)."""
import json, os, glob
import numpy as np
from common import *
from analyse import methods, weekly_cmin, ci95

NUM = json.load(open(f"{CODE}/results/numbers.json"))
T = json.load(open("tables_updated.json")); Q = json.load(open("quantile_check.json")); G = json.load(open("gridsens_base.json"))
L = []
def w(s=""): L.append(s)

# ------------------------------------------------------------------ compliance table (Online Resource 2)
w("%% ===== Table (Online Resource 2): compliant weeks of every reported design ====="); w("%% rows are generated from quantile_check.json (stored per-week P95 values)")
w("\\begin{table}[htbp]")
w("\\caption{\\label{tComply}Number of weeks with $P_{95}[\\mathrm{VUF}_\\mathrm{10\\,min}]\\le2\\%$ for the reported designs. Required: $\\lceil0.95N\\rceil$ of $N$ weeks (57 of 60, 38 of 40). Percentile: percentile sizing (12); Proposed: $(C^*,\\varepsilon_u^*)$ from the line search. Exact: VUF from the exact network model.}")
w("\\centering\\begin{adjustbox}{max width=\\linewidth}\\begin{tabular}{@{}llrrrrrrr}\\hline")
w("Case & $S_\\mathrm{sc}$ (MVA) & $N$ & Required & \\multicolumn{2}{c}{Percentile} & \\multicolumn{3}{c}{Proposed}\\\\")
w(" & & & & $C$ (MVA) & Weeks & $C^*$ (MVA) & $\\varepsilon_u^*$ (\\%) & Weeks\\\\\\hline")
rows = Q["rows"]
def pick(case, S, d): return next(r for r in rows if r["case"] == case and r["Ssc"] == S and r["design"] == d and r["table"] != "t8" or (case not in ("base", "suburban") and r["case"] == case and r["design"] == d))
for case, name, Ss in [("base", "High-speed (Tables~\\ref{tA}, \\ref{t7})", [500, 750, 1000, 1500, 2000]), ("suburban", "Suburban (Table~\\ref{tSub})", [750, 1000, 1500])]:
    for S in Ss:
        p = next(r for r in rows if r["case"] == case and r["Ssc"] == S and r["design"] == "p95" and r["table"] != "t8")
        RJ = {}
        for f in glob.glob(f"reselect_{case}_*.json"): RJ.update(json.load(open(f)))
        qn = RJ[str(S)]["new"]      # proposed design of the corrected line search
        q = dict(C=qn["C"], eps=qn["eps"], n_comply=qn["n_comply"])
        w(f"{name if S == Ss[0] else ''} & {S} & {p['N']} & {p['need']} & {p['C']:.2f} & {p['n_comply']} & {q['C']:.2f} & {q['eps']:.2f} & {q['n_comply']}\\\\")
w("\\hline\\multicolumn{9}{@{}l}{\\emph{Sensitivity cases of Table~\\ref{t8} (40 weeks, 750 MVA): percentile sizing complies in 38 (12 cases) or 39 (power $\\times1.25$) of 40 weeks; the proposed design in 40 of 40.}}\\\\")
exr = Q["exact_rows"]
w("\\multicolumn{9}{@{}l}{\\emph{Table~\\ref{tEx} (exact model, 60 weeks): percentile (12) with (8): 0; corrected percentile ($\\varepsilon_u=1.9\\%$, 11.83 MVA): " + f"{exr[0]['n_comply']}; proposed with (8) (10.44 MVA): 60; proposed, exact (11.27 MVA): {exr[1]['n_comply']}." + "}}\\\\")
w("\\hline\\end{tabular}\\end{adjustbox}\\end{table}"); w()

# ------------------------------------------------------------------ Table t7 / tSub / tA / t13
w("%% ===== Table t7 (replace the content of {{TABLE_7}}; only the 500 MVA row differs) =====")
w("%% OLD row: " + T["t7"]["tex_old"][0]); [w(x) for x in T["t7"]["tex_new"]]; w()
w("%% ===== Table tSub (replace the content of {{TABLE_SUB}}; only the 1000 MVA row differs) =====")
for a, b in zip(T["tSub"]["tex_old"], T["tSub"]["tex_new"]):
    if a != b: w("%% OLD row: " + a)
[w(x) for x in T["tSub"]["tex_new"]]; w()
w("%% ===== Table tA: column 'Percentile, C optimised' (4th column) changes; 'Proposed' (5th) is unchanged =====")
lab = ["Rating per leg $C$ (MVA)", "Threshold $\\varepsilon_u$ (\\%)", "P95 of 10-min VUF (\\%)", "Weeks meeting the P95 criterion (\\%)", "Maximum 10-min VUF (\\%)",
       "10-min values above 2\\% (\\%)", "Exceedance $E_\\mathrm{viol}$ (\\%$\\cdot$h/yr)", "Energy processed per leg (GWh/yr)", "Losses $E_\\mathrm{loss}$ (MWh/yr)",
       "$J$: capital / losses / exceedance (kUSD/yr)", "Expected annual cost $J$ (kUSD/yr)"]
tabA = NUM["TABLE_A"].split("\n"); newA = []
for i, line in enumerate(tabA):
    cells = line.rstrip("\\").split(" & ")
    old4 = T["tA_columns_old"]["p95_Copt"][i]
    assert cells[4].strip() == old4 or cells[4].strip() == "0" or i == 1, (i, cells[4], old4)
    cells[4] = T["tA_columns_new"]["p95_Copt"][i] if i != 1 else "2.0"
    newA.append(" & ".join(cells) + "\\\\")
[w(x) for x in newA]; w()
t13 = json.load(open("t13_updated.json"))
w("%% ===== Table t13 (cost weights), union grid: rows that change are marked in the comment =====")
for a, b in zip(t13["tex_old"], t13["tex_new"]):
    if a != b: w("%% OLD row: " + a)
    w(b)
w()

# ------------------------------------------------------------------ Table t8 (re-run cases)
LAB = {"base": "Base (60 weeks)", "freq_x0.5": "Train frequency $\\times0.5$", "freq_x1.5": "Train frequency $\\times1.5$",
       "power_x0.75": "Train power $\\times0.75$", "power_x1.25": "Train power $\\times1.25$",
       "no_regen": "No regenerative braking", "regen_4MW": "Regenerated power limited to 4~MW",
       "speed_250": "Line speed 250~km/h", "speed_350": "Line speed 350~km/h", "stop_0.5": "50\\% of trains stop",
       "poisson": "Poisson arrivals (independent trains)", "segments_prev": "Random power segments, Poisson arrivals",
       "diode": "Diode trains ($\\cos\\varphi=0.77$, no regeneration)", "grade_alt": "Other grade profile"}
t8old, t8new, t8rows, done = [], [], [], []
for c in LAB:
    ss = load_summary(c); m = methods(ss, 750); x = weekly_cmin(ss, 750, 2.0); a, b = ci95(x)
    mp_ = np.mean([wk["meanP"] for wk in ss["weeks"]]); pk, p95, pr = m["peak"]["C"], m["p95"]["C"], m["proposed"]["C"]
    def row(pr_, eps_, J_):
        return (f"{LAB[c]} & {mp_:.1f} & {pk:.1f} & ${a:.2f}\\pm{b:.2f}$ & {p95:.2f} & {pr_:.2f} & {eps_:.2f} & "
                f"{100*(1-p95/pk):.0f} / {100*(1-pr_/pk):.0f} & {100*(1-J_/m['p95']['J']):.0f}\\\\")
    t8old.append(row(pr, m["proposed"]["eps"], m["proposed"]["J"]))
    f = f"reselect_{c}_750.json" if c != "base" else "reselect_base_750_1000_500.json"
    if os.path.exists(f):
        n = json.load(open(f))["750"]["new"]; t8new.append(row(n["C"], n["eps"], n["J"])); done.append(c)
        t8rows.append(dict(case=c, old=dict(C=pr, eps=m["proposed"]["eps"], J=m["proposed"]["J"]), new=dict(C=n["C"], eps=n["eps"], J=n["J"], n_comply=n["n_comply"])))
    else:
        t8new.append(t8old[-1] + " % NOT RE-RUN")
assert "\n".join(t8old) == NUM["TABLE_8"], "old t8 not reproduced"
w("%% ===== Table t8 (re-selection finished for: " + ", ".join(done) + "); changed rows are preceded by their OLD row =====")
for a, b in zip(t8old, t8new):
    if a != b.split(" % NOT")[0]: w("%% OLD row: " + a)
    w(b)
w()
json.dump(dict(t8=t8rows), open("t8_updated.json", "w"), indent=1)

# ------------------------------------------------------------------ grid-sensitivity table (Online Resource 2)
S = G["J_surface_B"]; C_hat = G["Chat_fine"]
w("%% ===== Online Resource 2: sensitivity of the optimum to the search grid (base case, 750 MVA, approximation (8), 60 weeks) =====")
w("\\begin{table}[htbp]")
w("\\caption{\\label{tGrid}Expected annual cost $\\bar J$ (kUSD/yr) of the high-speed design ($S_\\mathrm{sc}=750$~MVA, 60 weeks, approximation (8)) on a refined search grid: $\\varepsilon_u$ in steps of 0.125\\% and $C=f\\,\\hat C(\\varepsilon_u)$ with $f$ in steps of 0.025. Bold: minimum of each row; all listed designs comply in 60 of 60 weeks.}")
w("\\centering\\begin{adjustbox}{max width=\\linewidth}\\begin{tabular}{@{}rrrrrrrrrr}\\hline")
w("$\\varepsilon_u$ (\\%) & $\\hat C$ (MVA) & $f=1.2$ & 1.25 & 1.3 & 1.35 & 1.4 & 1.45 & 1.5 & Best $C$ (MVA) \\\\\\hline")
for e in [0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25, 1.375, 1.5]:
    ks = ["1.2", "1.25", "1.3", "1.35", "1.4", "1.45", "1.5"]
    vals = [S[str(e)][k] for k in ks]; ib = int(np.argmin(vals))
    cells = [("\\textbf{%.1f}" % v) if i == ib else "%.1f" % v for i, v in enumerate(vals)]
    best = next(r for r in G["per_eps_B"] if abs(r["eps"] - e) < 1e-9)
    w(f"{e:g} & {C_hat[str(e)]:.2f} & " + " & ".join(cells) + f" & {best['C']:.2f}\\\\")
w("\\hline\\end{tabular}\\end{adjustbox}\\end{table}")
open("tables_new.tex", "w").write("\n".join(L) + "\n")
print("\n".join(L))
