"""Scope-of-validity table (ranking of assumptions by their effect on C*, J) -> tables_4_4.tex (appended), scope.json"""
import json
S = json.load(open("results_summary.json"))
t8 = {r["case"]: r["new"] for r in json.load(open("/home/claude/subtasks3/4/t8_updated.json"))["t8"]}
b = t8["base"]
rel = lambda a, c: 100 * (a - c) / c
rows = []
def add(name, line, C0, J0, C1, J1, how):
    rows.append(dict(assumption=name, line=line, C0=C0, J0=J0, C1=C1, J1=J1, dC=rel(C1, C0), dJ=rel(J1, J0), how=how))
for case, nm in (("power_x1.25", "train power +25\\%"), ("power_x0.75", "train power $-25$\\%"), ("freq_x1.5", "traffic +50\\%"), ("freq_x0.5", "traffic $-50$\\%"),
                 ("poisson", "independent Poisson arrivals instead of timetable"), ("no_regen", "no regenerative braking at all")):
    add(nm, "HS", b["C"], b["J"], t8[case]["C"], t8[case]["J"], "Table 9 (own seeds; 40 weeks vs 60)")
c = S["corr_base"]; add("correlated delay episodes", "HS", c["independent"]["proposed"]["C"], c["independent"]["proposed"]["J"], c["correlated"]["proposed"]["C"], c["correlated"]["proposed"]["J"], "same 40 seeds")
r = S["regen_suburban"]["designs"]; add("no return to the 110 kV grid", "Sub", r["v7"]["proposed"]["C"], r["v7"]["proposed"]["J"], r["noreturn_onboard"]["proposed"]["C"], r["noreturn_onboard"]["proposed"]["J"], "same 40 weeks")
r = S["regen_base"]["designs"]; add("no return to the 110 kV grid", "HS", r["v7"]["proposed"]["C"], r["v7"]["proposed"]["J"], r["noreturn_onboard"]["proposed"]["C"], r["noreturn_onboard"]["proposed"]["J"], "same 40 weeks")
for nm, line in (("cat_suburban", "Sub"), ("cat_base", "HS")):
    d = S[nm]["designs"]; add("catenary 0.2 $\\Omega$/km, 29~kV limit, return allowed", line, d["A_lumped_return"]["proposed"]["C"], d["A_lumped_return"]["proposed"]["J"], d["C_catenary_return"]["proposed"]["C"], d["C_catenary_return"]["proposed"]["J"], "same %d weeks" % S[nm]["n_weeks"])
rows.sort(key=lambda x: -abs(x["dC"]))
json.dump(rows, open("scope.json", "w"), indent=1)
tex = r"""%% ---------------------------------------------------------------------------------------------
%% Table SC: scope of validity -- shift of the design rating by the load assumptions (S_sc = 750 MVA, approximation (8))
\begin{table}[htbp]
\caption{\label{tScope}Shift of the design rating $C^*$ and of the annual objective $\bar J$ by the load assumptions, sorted by $|\Delta C^*|$ (HS: high-speed, Sub: suburban). Rows marked $^\dagger$ come from Table~\ref{t8} (own random seeds, so the change includes sampling noise of a few per cent); the other rows use the same seeds as their reference.}
\centering
\begin{tabular}{@{}llrrrr@{}}
\hline
Assumption changed & Line & $C^*$ (MVA) & $\Delta C^*$ (\%) & $\bar J$ (kUSD/yr) & $\Delta\bar J$ (\%)\\
\hline
"""
for x in rows:
    dag = "$^\\dagger$" if "Table 9" in x["how"] else ""
    tex += "%s%s & %s & %.2f & %+.1f & %.1f & %+.1f\\\\\n" % (x["assumption"], dag, x["line"], x["C1"], x["dC"], x["J1"], x["dJ"])
tex += r"""\hline
\end{tabular}
\end{table}
"""
open("tables_4_4.tex", "a").write("\n" + tex)
print(tex)
