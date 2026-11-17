import json, numpy as np
d = json.load(open("/home/claude/subtasks2/6/dss_results.json"))
R = d["rows"]
nz = [r for r in R if r["VUF_py"] > 1e-3]
z = [r for r in R if r["VUF_py"] <= 1e-3]
st = dict(
    n_total=len(R), n_VUF_nonzero=len(nz),
    max_VUF_rel_err_pct=max(abs(r["VUF_rel_err_vs_py_pct"]) for r in nz),
    max_VUF_abs_err_pp=max(abs(r["VUF_abs_err_vs_py_pp"]) for r in R),
    max_IUF_abs_err_pp=max(abs(r["IUF_abs_err_vs_py_pp"]) for r in R),
    max_S_rel_err_pct=max(max(r["Sa_rel_err_pct"], r["Sb_rel_err_pct"]) for r in R),
    max_series_vs_xfmr_rel_pct=max(abs(r["VUF_dss_series"] - r["VUF_dss"]) / r["VUF_dss"] * 100 for r in nz),
    max_zero_case_VUF_dss=max(r["VUF_dss"] for r in z), n_zero=len(z),
    all_converged=all(r["converged"] for r in R), max_iter=max(r["iterations"] for r in R),
)
A = [r for r in R if r["set"] == "A"]
cpA = [r for r in A if r["load_model"] == "CP" and r["VUF_py"] > 1e-3]
st["A_CP_exact_vs_eq8_rel_range_pct"] = [min((r["VUF_py"] - r["VUF_eq8"]) / r["VUF_eq8"] * 100 for r in cpA), max((r["VUF_py"] - r["VUF_eq8"]) / r["VUF_eq8"] * 100 for r in cpA)]
czA = [r for r in A if r["load_model"] == "CZ" and r["VUF_py"] > 1e-3]
st["A_CZ_exact_vs_eq8_rel_range_pct"] = [min((r["VUF_py"] - r["VUF_eq8"]) / r["VUF_eq8"] * 100 for r in czA), max((r["VUF_py"] - r["VUF_eq8"]) / r["VUF_eq8"] * 100 for r in czA)]
st["max_IUF_dss_vs_eq7_pp_caseA_CZ"] = max(abs(r["IUF_abs_err_vs_eq7_pp"]) for r in A if r["load_model"] == "CZ")
st["max_IUF_dss_vs_eq7_pp_caseA_CP"] = max(abs(r["IUF_abs_err_vs_eq7_pp"]) for r in A if r["load_model"] == "CP")
json.dump(st, open("/home/claude/subtasks2/6/summary_stats.json", "w"), indent=1)
print(json.dumps(st, indent=1))

# full markdown table
L = ["| set | case | load | Ssc | VUF eq.(8) % | VUF Python % | VUF OpenDSS % | rel. err % | abs. err pp | IUF eq.(7) % | IUF Python % | IUF OpenDSS % | max S err % |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in R:
    i7 = "" if r["IUF_eq7"] is None else f"{r['IUF_eq7']:.3f}"
    re_ = "n/a" if r["VUF_py"] <= 1e-3 else f"{r['VUF_rel_err_vs_py_pct']:.4f}"
    L.append(f"| {r['set']} | {r['id']} | {r['load_model']} | {r['Ssc_MVA']:.0f} | {r['VUF_eq8']:.4f} | {r['VUF_py']:.4f} | {r['VUF_dss']:.4f} | {re_} | {r['VUF_abs_err_vs_py_pp']:.1e} | {i7} | {r['IUF_py']:.3f} | {r['IUF_dss']:.3f} | {max(r['Sa_rel_err_pct'], r['Sb_rel_err_pct']):.1e} |")
open("/home/claude/subtasks2/6/comparison_table.md", "w").write("\n".join(L) + "\n")

# LaTeX tables for the paper
def row_A(r):
    return (f"{r['Ssc_MVA']:.0f} & {r['k']:g} & {r['dphi_deg']:.0f} & {r['IUF_eq7']:.2f} & {r['IUF_py']:.2f} & {r['IUF_dss']:.2f} & "
            f"{r['VUF_eq8']:.3f} & {r['VUF_py']:.3f} & {r['VUF_dss']:.3f} \\\\")
selA = [r for r in A if r["load_model"] == "CP" and r["k"] in (0.0, 0.5) and r["dphi_deg"] == 0] + \
       [r for r in A if r["load_model"] == "CP" and r["k"] == 1.0 and r["dphi_deg"] == 20]
selA = sorted(selA, key=lambda r: (r["Ssc_MVA"], r["k"]))
tA = "\n".join(row_A(r) for r in selA)
B = [r for r in R if r["set"] == "B"]
names = {"B1_none": "none", "B2_Ponly": "active power only", "B3_eq11": "eq.\\ (11)", "B4_full": "full"}
tB = []
for cid in names:
    row = [names[cid]]
    rr = {r["load_model"]: r for r in B if r["id"] == cid}
    row.append(f"{rr['CI']['VUF_eq8']:.2f}")
    for m in ("CI", "CP"):
        row += [f"{rr[m]['VUF_py']:.3f}", f"{rr[m]['VUF_dss']:.3f}"]
    tB.append(" & ".join(row) + " \\\\")
open("/home/claude/subtasks2/6/_tabA.tex", "w").write(tA + "\n")
open("/home/claude/subtasks2/6/_tabB.tex", "w").write("\n".join(tB) + "\n")
print(tA); print("\n".join(tB))
