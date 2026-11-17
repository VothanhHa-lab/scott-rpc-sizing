"""LaTeX tables from results/compare_*.json (literal numbers)."""
import sys, os, json
sys.dont_write_bytecode = True
RES = "/home/claude/subtasks4/6/results"; OUT = "/home/claude/subtasks4/6/deliver"
M = {m: json.load(open(f"{RES}/compare_{m}.json")) for m in ("exact", "approx", "sub") if os.path.exists(f"{RES}/compare_{m}.json")}
M0 = {m: json.load(open(f"{RES}/compare_{m}_gridonly.json")) for m in ("exact", "approx", "sub") if os.path.exists(f"{RES}/compare_{m}_gridonly.json")}


def f(x, d=1):
    return f"{x:.{d}f}".replace("-", "$-$") if isinstance(x, (int, float)) else str(x)


def sgn(x, d=1):
    s = f"{abs(x):.{d}f}"
    return ("$-$" if x < 0 else "$+$") + s


NAME = dict(pct_min="Percentile, corrected, minimum rating", pct_opt="Percentile, corrected, $C$ optimised", prop="Proposed")
NAME_A = dict(pct_min="Percentile (12), minimum rating", pct_opt="Percentile (12), $C$ optimised", prop="Proposed")


REFNAME = dict(pct12="Percentile (12), approx.\\ (8) design", prop8="Proposed, approx.\\ (8) design")


def design_rows(sc, names):
    rows = []
    for k in ("pct12", "pct_min", "pct_opt", "prop8", "prop"):
        if k in REFNAME:
            if k not in sc.get("ref_designs", {}):
                continue
            p = sc["ref_designs"][k]; names = dict(names); names[k] = REFNAME[k]
        else:
            p = sc["designs"][k]
        rows.append(f"{names[k]} & {p['C']:.2f} & {p['eps']:.2f} & {p['cap']:.1f} & {p['hw']:.1f} & {p['loss']+p['filt']:.1f} & {p['caploss']:.1f} & {p['viol']:.1f} & {p['J']:.1f} & {p['Eviol']:.1f}\\\\")
    return rows


def table_tEx(model="exact", main="TF"):
    m = M[model]
    names = NAME if model == "exact" else NAME_A
    lines = [r"\begin{table}[htbp]",
             r"\caption{\label{tExHW" + ("" if model == "exact" else model) + r"}Designs with the hardware items of Table~\ref{tHW} included in the annual objective (" +
             ("exact network model in the loop, $S_\\mathrm{sc}=750$~MVA, 60 base weeks" if model == "exact" else
              "approximation (8), $S_\\mathrm{sc}=750$~MVA, 60 base weeks" if model == "approx" else "approximation (8), suburban line, 40 weeks") +
             r"). $J_\mathrm{cap}$ is the converter-leg term of (16) ($30.6\,C$), $J_\mathrm{hw}$ the annualised added hardware (coupling transformers, 100~Hz filter), $J_\mathrm{loss}$ includes the filter loss; kUSD/yr; $E_\mathrm{viol}$ in \%$\cdot$h/yr. The ratings of the `$C$ optimised' and proposed rows are re-selected for each cost assumption. First block: cost model of (16) without hardware items, ratings on the candidate grid of Table~\ref{tEx} (as published); second block: finer candidate set (additional evaluations at the ratings in between).}",
             r"\centering", r"\begin{adjustbox}{max width=\linewidth}", r"\setlength{\tabcolsep}{4pt}",
             r"\begin{tabular}{@{}lrrrrrrrrr}", r"\hline",
             r"Sizing & $C$ (MVA) & $\varepsilon_u$ (\%) & $J_\mathrm{cap}$ & $J_\mathrm{hw}$ & $J_\mathrm{loss}$ & $J_\mathrm{cap}{+}J_\mathrm{hw}{+}J_\mathrm{loss}$ & $J_\mathrm{viol}$ & $J$ & $E_\mathrm{viol}$\\", r"\hline",
             r"\multicolumn{10}{@{}l}{\emph{Without hardware items (v7)}}\\"]
    lines += design_rows(M0.get(model, m)["scenarios"]["v7"], names)
    lines += [r"\hline", r"\multicolumn{10}{@{}l}{\emph{With coupling transformers and 100~Hz filter (central unit costs)}}\\"]
    lines += design_rows(m["scenarios"][main], names)
    sc = m["scenarios"][main]
    d1, d2 = sc["delta_vs_pct_min"], sc["delta_vs_pct_opt"]
    lines += [r"\hline",
              r"\multicolumn{10}{@{}l}{Proposed minus minimum-rating percentile: $\Delta J$ " + f"{sgn(d1['J'])} ({sgn(d1['dJ_pct'])}\\%), $\\Delta(J_\\mathrm{{cap}}{{+}}J_\\mathrm{{hw}}{{+}}J_\\mathrm{{loss}})$ {sgn(d1['caploss'])} ({sgn(d1['dcaploss_pct'])}\\%), $\\Delta E_\\mathrm{{viol}}$ {sgn(d1['dEviol_pct'],0)}\\%}}\\\\",
              r"\multicolumn{10}{@{}l}{Proposed minus percentile with $C$ optimised: $\Delta J$ " + f"{sgn(d2['J'])} ({sgn(d2['dJ_pct'])}\\%), $\\Delta(J_\\mathrm{{cap}}{{+}}J_\\mathrm{{hw}}{{+}}J_\\mathrm{{loss}})$ {sgn(d2['caploss'])} ({sgn(d2['dcaploss_pct'])}\\%), $\\Delta E_\\mathrm{{viol}}$ {sgn(d2['dEviol_pct'],0)}\\%}}\\\\",
              r"\hline", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]
    open(f"{OUT}/table_tExHW_{model}.tex", "w").write("\n".join(lines) + "\n")


ORDER = ["v7", "T", "TF", "TF_low", "TF_high", "F_only", "TD", "TD_low", "TD_high", "TFS"]
LAB = {"v7": "No hardware items (v7)", "T": "Coupling transformers", "TF": "Transformers + 100~Hz filter", "TF_low": "\\quad low unit costs",
       "TF_high": "\\quad high unit costs", "F_only": "Filter only (transformers in 150~kUSD/MVA)", "TD": "Transformers + $H_\\mathrm{dc}=26.2$~ms",
       "TD_low": "\\quad low unit costs", "TD_high": "\\quad high unit costs", "TFS": "Transformers + filter + Scott 40$\\to$50~MVA per leg (not required, see text)"}


def table_sens(model="exact"):
    m = M[model]
    lines = [r"\begin{table}[htbp]",
             r"\caption{\label{tHWsens" + model + r"}Effect of the hardware assumptions on the comparison (" + ("exact model" if model == "exact" else "approximation (8), high-speed line" if model == "approx" else "approximation (8), suburban line") +
             r", " + ("40" if model == "sub" else "60") + r" weeks, $w_3=2$~kUSD/(\%$\cdot$h)). $\Delta$ = proposed minus baseline in \%, baselines: percentile at its minimum rating (min) and with $C$ optimised (opt). $J$ and $J_\mathrm{cap}{+}J_\mathrm{hw}{+}J_\mathrm{loss}$ (`cap+hw+loss') in kUSD/yr.}",
             r"\centering", r"\begin{adjustbox}{max width=\linewidth}", r"\begin{tabular}{@{}lrrrrrrrrrrr}", r"\hline",
             r"Hardware assumption & $C^*$ & $\varepsilon_u^*$ & $J$ prop. & $J$ min & $J$ opt & $\Delta J$ min & $\Delta J$ opt & $\Delta$cap+hw+loss min & $\Delta$cap+hw+loss opt & $\Delta E_\mathrm{viol}$ min & $\Delta E_\mathrm{viol}$ opt\\", r"\hline"]
    for k in ORDER:
        if k not in m["scenarios"]:
            continue
        sc = m["scenarios"][k]; p = sc["designs"]; a, b = sc["delta_vs_pct_min"], sc["delta_vs_pct_opt"]
        lines.append(f"{LAB[k]} & {p['prop']['C']:.2f} & {p['prop']['eps']:.2f} & {p['prop']['J']:.1f} & {p['pct_min']['J']:.1f} & {p['pct_opt']['J']:.1f} & "
                     f"{sgn(a['dJ_pct'])} & {sgn(b['dJ_pct'])} & {sgn(a['dcaploss_pct'])} & {sgn(b['dcaploss_pct'])} & {sgn(a['dEviol_pct'],0)} & {sgn(b['dEviol_pct'],0)}\\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]
    open(f"{OUT}/table_hw_sens_{model}.tex", "w").write("\n".join(lines) + "\n")


def table_equal(scen=("v7", "TF")):
    lines = [r"\begin{table}[htbp]",
             r"\caption{\label{tEq}Capital plus losses (plus hardware) at the same exceedance. For a cap on $E_\mathrm{viol}$ (\%$\cdot$h/yr) each family minimises $J_\mathrm{cap}{+}J_\mathrm{hw}{+}J_\mathrm{loss}$ (kUSD/yr) subject to the weekly criterion (P95 $\le2\%$ in at least 95\% of the weeks): the percentile family has $\varepsilon_u$ fixed (1.9\% exact model, 2.0\% approximation (8)) and $C$ free, the proposed family has $C$ and $\varepsilon_u$ free. Caps: $E_\mathrm{viol}$ of the percentile design with optimised $C$ (cap 1) and of the proposed design (cap 2). Interpolated optimum between evaluated candidates (the grid optimum is in the machine-readable results). `Saving' = percentile minus proposed.}",
             r"\centering", r"\begin{adjustbox}{max width=\linewidth}", r"\begin{tabular}{@{}llllrrrrr}", r"\hline",
             r"Model & Costs & Cap & Cap value & Percentile $C$ & cap+hw+loss & Proposed $(C,\varepsilon_u)$ & cap+hw+loss & Saving (\%)\\", r"\hline"]
    for mname, lab in (("exact", "Exact, high-speed"), ("approx", "Approx.\\ (8), high-speed"), ("sub", "Approx.\\ (8), suburban")):
        if mname not in M:
            continue
        for sk in scen:
            if sk not in M[mname]["scenarios"]:
                continue
            for cn, cl in (("cap_pct_opt", "1"), ("cap_prop", "2")):
                e = M[mname]["scenarios"][sk]["equal_exceedance"][cn]
                a, b = e["pct"]["interp"], e["prop"]["interp"]; s = e["saving_interp"]
                lines.append(f"{lab} & {'v7' if sk=='v7' else 'with hardware'} & {cl} & {e['cap']:.1f} & {a['C']:.2f} & {a['caploss']:.1f} & ({b['C']:.2f}, {b['eps']:.2f}) & {b['caploss']:.1f} & {s['kUSD']:.1f} ({s['pct']:.1f})\\\\")
        lines.append(r"\hline")
    lines += [r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]
    open(f"{OUT}/table_equal_exceedance.tex", "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    for mn in M:
        table_tEx(mn); table_sens(mn)
    table_equal()
    print("tables written for", list(M))
