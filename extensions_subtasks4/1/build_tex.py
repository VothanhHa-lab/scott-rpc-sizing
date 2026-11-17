"""LaTeX reproduction tables (literal numbers from the recomputation) -> reproduction.tex"""
import sys, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

S = json.load(open(f"{OUT}/data/summary.json"))
D = json.load(open(f"{OUT}/data/report_diffs.json"))
cert = D["cert"]
RB = json.load(open(f"{OUT}/data/repro_approx_base.json"))
RS = json.load(open(f"{OUT}/data/repro_approx_sub.json"))
sp, sc = S["sub_approx_proposed"], S["sub_approx_percentile12"]
hp, hc = S["hs_approx_proposed"], S["hs_approx_percentile12"]
ep, ec = S["hs_exact_proposed"], S["hs_exact_percentile_corrected"]


def g(x, d):
    return f"{x:.{d}f}"


L = []
L.append("% Reproduction table of the v7 reference results (all numbers recomputed from the stored 1-s weeks; see reproduction.md)")
L.append("% Needs: booktabs not required (uses \\hline as in the manuscript)")
L.append("\\begin{table}[htbp]")
L.append("\\caption{\\label{tRepro}Reference designs reproduced from the code and seeds of Online Resource~1 ($S_\\mathrm{sc}=750$~MVA, $\\varepsilon_\\mathrm{lim}=2\\%$). "
         "$J$ is evaluated on the stored weeks (60 design weeks for the high-speed line, 40 for the suburban line); certification uses 90 further high-speed weeks}")
L.append("\\centering")
L.append("\\begin{adjustbox}{max width=\\linewidth}")
L.append("\\begin{tabular}{@{}llrrrrr}")
L.append("\\hline")
L.append("Case & Model in the loop & $C^*$ (MVA) & $\\varepsilon_u^*$ (\\%) & $J$ (kUSD/yr) & Compliant weeks & Violated fresh weeks\\\\")
L.append("\\hline")
L.append(f"High-speed, proposed & approx.\\ (8) & {g(hp['C'],2)} & {g(hp['eps_u'],1)} & {g(hp['J'],1)} & {hp['comply_weeks']}/60 & --\\\\")
L.append(f"High-speed, proposed & exact phasor & {g(ep['C'],2)} & {g(ep['eps_u'],1)} & {g(ep['J'],1)} & {ep['comply_weeks']}/60 & {cert['prop']['nv_direct']}/90\\\\")
L.append(f"High-speed, corrected percentile & exact phasor & {g(ec['C'],2)} & {g(ec['eps_u'],1)} & {g(ec['J'],1)} & {ec['comply_weeks']}/60 & {cert['corr']['nv_direct']}/90\\\\")
L.append(f"Suburban, proposed & approx.\\ (8) & {g(sp['C'],2)} & {g(sp['eps_u'],2)} & {g(sp['J'],1)} & {sp['comply_weeks']}/40 & --\\\\")
L.append(f"Suburban, percentile (12) & approx.\\ (8) & {g(sc['C'],2)} & {g(sc['eps_u'],1)} & {g(sc['J'],1)} & {sc['comply_weeks']}/40 & --\\\\")
L.append("\\hline")
L.append("\\end{tabular}")
L.append("\\end{adjustbox}")
L.append("\\end{table}")
# ---- second table: all exported designs ----
LAB = {"hs_approx_proposed": ("High-speed", "approx.\\ (8)", "Proposed"),
       "hs_approx_percentile12": ("High-speed", "approx.\\ (8)", "Percentile (12)"),
       "hs_approx_percentile_Copt": ("High-speed", "approx.\\ (8)", "Percentile, $C$ optimised"),
       "hs_approx_peak11": ("High-speed", "approx.\\ (8)", "Peak (11)"),
       "hs_approx_full": ("High-speed", "approx.\\ (8)", "Full compensation"),
       "hs_exact_proposed": ("High-speed", "exact", "Proposed"),
       "hs_exact_percentile_corrected": ("High-speed", "exact", "Percentile, corrected"),
       "hs_exact_percentile_corrected_Copt": ("High-speed", "exact", "Percentile, corrected, $C$ opt."),
       "hs_exact_of_approx_proposed": ("High-speed", "exact", "Proposed of (8), re-evaluated"),
       "hs_exact_of_approx_percentile12": ("High-speed", "exact", "Percentile (12), re-evaluated"),
       "sub_approx_proposed": ("Suburban", "approx.\\ (8)", "Proposed"),
       "sub_approx_percentile12": ("Suburban", "approx.\\ (8)", "Percentile (12)"),
       "sub_approx_percentile_Copt": ("Suburban", "approx.\\ (8)", "Percentile, $C$ optimised"),
       "cert_exact_proposed": ("Cert.\\ (90 new weeks)", "exact", "Proposed"),
       "cert_exact_percentile_corrected": ("Cert.\\ (90 new weeks)", "exact", "Percentile, corrected")}
L.append("")
L.append("% Per-design summary of the exported per-week CSVs (means over the weeks; VUF in %, E_viol in %.h/yr, E_loss in MWh/yr, J in kUSD/yr)")
L.append("\\begin{table}[htbp]")
L.append("\\caption{\\label{tReproAll}Reported designs evaluated on the same 1-s load of each stored week ($S_\\mathrm{sc}=750$~MVA). Means over the weeks; $\\hat V_{\\max}$ is the mean (maximum over the weeks) of the weekly maximum 10-min VUF}")
L.append("\\centering")
L.append("\\begin{adjustbox}{max width=\\linewidth}")
L.append("\\begin{tabular}{@{}lllrrrrrrrrrr}")
L.append("\\hline")
L.append("Weeks & Model & Design & $C$ & $\\varepsilon_u$ & Compl. & $P_{95}$ & $\\hat V_{\\max}$ & $E_\\mathrm{viol}$ & $E_\\mathrm{loss}$ & $J_\\mathrm{cap}/J_\\mathrm{loss}/J_\\mathrm{viol}$ & $J$\\\\")
L.append("\\hline")
for t, (a, b, c) in LAB.items():
    s_ = S[t]
    L.append(f"{a} & {b} & {c} & {g(s_['C'],2)} & {g(s_['eps_u'],2)} & {s_['comply_weeks']}/{s_['n_weeks']} & {g(s_['P95_mean'],2)} & {g(s_['vmax_mean'],2)} ({g(s_['vmax_max'],2)}) & {g(s_['Eviol_yr'],1)} & {g(s_['Eloss_yr'],0)} & {g(s_['Jcap'],0)}/{g(s_['Jloss'],0)}/{g(s_['Jviol'],0)} & {g(s_['J'],1)}\\\\")
L.append("\\hline")
L.append("\\end{tabular}")
L.append("\\end{adjustbox}")
L.append("\\end{table}")
open(f"{OUT}/reproduction.tex", "w").write("\n".join(L) + "\n")
print("\n".join(L))
