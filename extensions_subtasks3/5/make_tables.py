"""Generate the LaTeX tables from decomposition.json (all numbers come from that file)."""
import json
D = json.load(open("/home/claude/subtasks3/5/decomposition.json"))
R = D["tEx_rows"]
f1 = lambda x: f"{x:.1f}"
f2 = lambda x: f"{x:.2f}"
def sg(x, n=1):
    if abs(x) < 0.05 and n == 1:
        n = 2
    return (f"{x:+.{n}f}").replace("-", "$-$").replace("+", "$+$")


def exrow(label, model, r, Japprox):
    cl = r["Jcap"] + r["Jloss"]
    return (f"{label} & {model} & {f2(r['C'])} & {r['eps']:.1f} & {Japprox} & {f1(r['J'])} & {f1(r['Jcap'])} & {f1(r['Jloss'])} & "
            f"{f1(cl)} & {f1(r['Jviol'])} & {f1(r['Eviol'])} & {r['p95']:.2f} ({r['p95max']:.2f}) & {100*r['comply']:.0f}\\\\")


pa, pc, pco, qa, qe = R["pct_approx"], R["pct_corr"], R["pct_corr_Copt"], R["prop_approx"], R["prop_exact"]
Jap_conv = D["tA_prop_vs_p95"]["J_base"]; Jap_prop = D["tA_prop_vs_p95"]["J_prop"]
rows = [
    exrow("Percentile (12)", "approx.\\ (8)", pa, f1(Jap_conv)),
    exrow("Percentile, corrected", "exact", pc, "--"),
    exrow("Percentile, corrected, $C$ optimised", "exact", pco, "--"),
    exrow("Proposed", "approx.\\ (8)", qa, f1(Jap_prop)),
    exrow("Proposed", "exact", qe, "--"),
]
tex = r"""\begin{table}[htbp]
\caption{\label{tEx}Designs obtained with approximation (8) and with the exact network model in the loop ($S_\mathrm{sc}=750$~MVA, 60 base weeks, $\varepsilon_\mathrm{lim}=2\%$). $J$ (8) is the objective computed with (8) as in Table~\ref{tA}; the remaining columns are evaluated with the exact model (means over the weeks; $J_\mathrm{cap}$, $J_\mathrm{loss}$, $J_\mathrm{viol}$ are the three terms of (16), in kUSD/yr; $J_\mathrm{cap}+J_\mathrm{loss}$ is the capital and loss part; $E_\mathrm{viol}$ in \%$\cdot$h/yr). `Percentile, corrected, $C$ optimised' keeps $\varepsilon_u=1.9\%$ and takes the rating with the lowest $J$ among the grid values $\hat C\cdot\{1,1.1,1.2,1.35,1.5,1.75,2,2.5\}$ ($\hat C=11.83$~MVA). Compliance is the share of weeks with $P_{95}[\mathrm{VUF}_\mathrm{10\,min}]\le2\%$.}
\centering
\begin{adjustbox}{max width=\linewidth}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}llrrrrrrrrrrr}
\hline
Sizing & Model in & $C$ & $\varepsilon_u$ & $J$ (8) & $J$ exact & $J_\mathrm{cap}$ & $J_\mathrm{loss}$ & $J_\mathrm{cap}$ & $J_\mathrm{viol}$ & $E_\mathrm{viol}$ & Exact $P_{95}$ (\%) & Compliance\\
 & the loop & (MVA) & (\%) & (kUSD/yr) & (kUSD/yr) & & & $+J_\mathrm{loss}$ & & & mean (max) & (\%)\\
\hline
""" + "\n".join(rows) + r"""
\hline
\end{tabular}
\end{adjustbox}
\end{table}
"""
open("/home/claude/subtasks3/5/table_tEx.tex", "w").write(tex)

# ---- decomposition table
def drow(label, key):
    d = D[key]
    return (f"\\quad {label} & {f1(d['J_base'])} & {f1(d['J_prop'])} & {sg(d['dJ'])} ({sg(d['dJ_pct'])}) & {sg(d['dcap'])} & {sg(d['dloss'])} & {sg(d['dpen'])} & "
            f"{sg(d['dcaploss'])} ({sg(d['dcaploss_pct'])}) & {sg(d['dEviol_pct'],0) if abs(d['dEviol_pct'])>=10 else sg(d['dEviol_pct'])}\\\\")

blocks = [
    ("High-speed line, approximation (8), 60 weeks", [("vs percentile sizing (12)", "tA_prop_vs_p95"), ("vs percentile, $C$ optimised", "tA_prop_vs_p95_Copt")]),
    ("High-speed line, exact model in the loop, 60 weeks", [("vs corrected percentile sizing", "tEx_prop_vs_corrected"), ("vs corrected, $C$ optimised", "tEx_prop_vs_corrected_Copt")]),
    ("Suburban line, approximation (8), 40 weeks", [("750~MVA, vs percentile sizing (12)", "tSub_750_prop_vs_p95"), ("750~MVA, vs percentile, $C$ optimised", "tSub_750_prop_vs_p95_Copt"), ("1000~MVA, vs percentile sizing (12)", "tSub_1000_prop_vs_p95")]),
]
body = []
for title, items in blocks:
    body.append(f"\\multicolumn{{9}}{{@{{}}l}}{{\\emph{{{title}}}}}\\\\")
    for lab, key in items:
        body.append(drow(lab, key))
    body.append("\\hline" if title != blocks[-1][0] else "")
tex2 = r"""\begin{table}[htbp]
\caption{\label{tDec}Decomposition of the difference of the annual objective $\bar J=J_\mathrm{cap}+J_\mathrm{loss}+J_\mathrm{viol}$ between the proposed design and the baseline (proposed minus baseline, kUSD/yr; $\Delta J$ and $\Delta(J_\mathrm{cap}+J_\mathrm{loss})$ also in \% of the baseline value). $\Delta E_\mathrm{viol}$: change of the mean exceedance in \%. The difference of the exceedance term $\Delta J_\mathrm{viol}=w_3\,\Delta E_\mathrm{viol}$ is the part of the saving that depends on the assumed penalty $w_3$.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}lrrrrrrrr}
\hline
Comparison & $J$ baseline & $J$ proposed & $\Delta J$ (\%) & $\Delta J_\mathrm{cap}$ & $\Delta J_\mathrm{loss}$ & $\Delta J_\mathrm{viol}$ & $\Delta(J_\mathrm{cap}+J_\mathrm{loss})$ (\%) & $\Delta E_\mathrm{viol}$ (\%)\\
\hline
""" + "\n".join(b for b in body if b != "") + r"""
\hline
\end{tabular}
\end{adjustbox}
\end{table}
"""
open("/home/claude/subtasks3/5/table_tDec.tex", "w").write(tex2)

# ---- tCI additional rows
hs, sb = D["tA_prop_vs_p95"], D["tSub_750_prop_vs_p95"]
bh, bs = D["tCI_bootstrap_of_split"]["high_speed_750"], D["tCI_bootstrap_of_split"]["suburban_750"]
def ci(v, n=1): return "[" + ", ".join(f"{x:.{n}f}".replace("-", "$-$") for x in v) + "]"
def chg(x): return (f"{x:+.1f}").replace("-", "$-$").replace("+", "$+$")
rows_h = [
    f"Change of capital + loss part (\\%) & {chg(hs['dcaploss_pct'])} & -- & --\\\\",
    f"Change of exceedance $E_\\mathrm{{viol}}$ (\\%) & {chg(hs['dEviol_pct'])} & -- & {ci(bh['dEviol_pct'])}$^\\dagger$\\\\",
]
rows_s = [
    f"Change of capital + loss part (\\%) & {chg(sb['dcaploss_pct'])} & -- & --\\\\",
    f"Change of exceedance $E_\\mathrm{{viol}}$ (\\%) & {chg(sb['dEviol_pct'])} & -- & {ci(bs['dEviol_pct'])}$^\\dagger$\\\\",
]
open("/home/claude/subtasks3/5/tCI_rows.tex", "w").write(
    "% insert after 'Cost reduction (\\%) & 14.9 ...' (high speed) and after 'Cost reduction (\\%) & 15.2 ...' (suburban)\n"
    "% high-speed\n" + "\n".join(rows_h) + "\n% suburban\n" + "\n".join(rows_s) + "\n")
print(tex); print(tex2); print(open("/home/claude/subtasks3/5/tCI_rows.tex").read())
