"""Reproduction tables (markdown + LaTeX) from data/summary.json + stored/recomputed JSON.
Run after export_csv.py (approx, exact, cert) and make_tables.py."""
import sys, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

S = json.load(open(f"{OUT}/data/summary.json"))
RB = json.load(open(f"{OUT}/data/repro_approx_base.json"))
RS = json.load(open(f"{OUT}/data/repro_approx_sub.json"))

# ---- v7 values as printed in the PDF (pdftotext of manuscript.pdf, Tables 6, 12, 13, 14) ----
T6_COLS = ["Full compensation", "Peak sizing (11)", "Percentile sizing (12)", "Percentile, C optimised", "Proposed (15)-(17)"]
T6_TAGS = ["hs_approx_full", "hs_approx_peak11", "hs_approx_percentile12", "hs_approx_percentile_Copt", "hs_approx_proposed"]
T6_V7 = {
    "C": [32.9, 25.4, 11.9, 12.5, 10.4],
    "eps_u": [0, 2.0, 2.0, 2.0, 1.0],
    "P95_mean": [0.00, 1.96, 1.99, 1.98, 1.50],
    "comply_pct": [100, 100, 95, 100, 100],
    "vmax_mean": [0.01, 2.00, 2.72, 2.63, 2.79],
    "share_mean_pct": [0.0, 0.0, 4.3, 3.6, 1.1],
    "Eviol_yr": [0, 0, 53.2, 40.1, 27.8],
    "Etr_GWh_yr": [45.9, 10.9, 10.6, 10.6, 22.8],
    "Eloss_yr": [2449, 1500, 818, 850, 1001],
    "Jcap": [1005, 776, 363, 382, 319],
    "Jloss": [196, 120, 65, 68, 80],
    "Jviol": [0, 0, 106, 80, 56],
    "J": [1201, 896, 534, 530, 455],
}
T12_ROWS = [  # label, tag, v7: C, eps, J(8), Jexact, Jcap, Jloss, Jcap+Jloss, Jviol, Eviol, P95 mean, P95 max, compliance %
    ("Percentile (12), approx. (8)", "hs_exact_of_approx_percentile12", dict(C=11.87, eps=2.0, J8=534.4, J=654.9, Jcap=362.6, Jloss=65.5, Jcl=428.1, Jviol=226.8, Eviol=113.4, P95=2.07, P95max=2.11, comp=0)),
    ("Percentile, corrected, exact", "hs_exact_percentile_corrected", dict(C=11.83, eps=1.9, J8=None, J=576.0, Jcap=361.3, Jloss=66.9, Jcl=428.2, Jviol=147.8, Eviol=73.9, P95=1.98, P95max=2.02, comp=95)),
    ("Percentile, corrected, C optimised, exact", "hs_exact_percentile_corrected_Copt", dict(C=13.01, eps=1.9, J8=None, J=558.8, Jcap=397.4, Jloss=71.7, Jcl=469.1, Jviol=89.7, Eviol=44.9, P95=1.96, P95max=1.98, comp=100)),
    ("Proposed, approx. (8)", "hs_exact_of_approx_proposed", dict(C=10.44, eps=1.0, J8=454.6, J=497.0, Jcap=319.0, Jloss=80.0, Jcl=399.0, Jviol=98.0, Eviol=49.0, P95=1.58, P95max=1.69, comp=100)),
    ("Proposed, exact", "hs_exact_proposed", dict(C=11.27, eps=1.0, J8=None, J=489.3, Jcap=344.4, Jloss=83.7, Jcl=428.1, Jviol=61.3, Eviol=30.6, P95=1.46, P95max=1.59, comp=100)),
]
T14_V7 = dict(P95_unc=2.98, full=34.9, peak=27.4, p95C=8.02, Cstar=7.80, eps=0.75, Ev12=67.0, Evp=26.8, J12=426, Jp=361, red=15)


def f(x, d):
    return f"{x:.{d}f}"


def flag(code, v7, tol):
    return "ok" if abs(code - v7) <= tol else "DIFF"


lines = []
tex = []
diffs = []

# ---------- Table 6 ----------
lines.append("## Table 6 (v7) - high-speed, approximation (8), Ssc = 750 MVA, 60 weeks: code vs v7 print\n")
lines.append("| Quantity | " + " | ".join(T6_COLS) + " |")
lines.append("|---|" + "---|" * 5)
rows6 = [("C (MVA)", "C", 2, 0.05), ("eps_u (%)", "eps_u", 2, 0.005), ("P95 of 10-min VUF, mean (%)", "P95_mean", 2, 0.005),
         ("Weeks meeting P95 (%)", "comply_pct", 0, 0.5), ("Max 10-min VUF, mean of weekly max (%)", "vmax_mean", 2, 0.005),
         ("10-min values > 2 % (%)", "share_mean_pct", 1, 0.05), ("E_viol (%.h/yr)", "Eviol_yr", 1, 0.05),
         ("Energy per leg (GWh/yr)", "Etr_GWh_yr", 1, 0.05), ("E_loss (MWh/yr)", "Eloss_yr", 0, 0.5),
         ("J_cap (kUSD/yr)", "Jcap", 0, 0.5), ("J_loss (kUSD/yr)", "Jloss", 0, 0.5), ("J_viol (kUSD/yr)", "Jviol", 0, 0.5),
         ("J (kUSD/yr)", "J", 1, 0.5)]
for lab, key, d, tol in rows6:
    cells = []
    for i, tag in enumerate(T6_TAGS):
        s = S[tag]
        val = 100.0 * s["comply_weeks"] / s["n_weeks"] if key == "comply_pct" else s[key]
        v7 = T6_V7[key][i]
        ok = flag(round(val, d), v7, tol)
        if ok != "ok":
            diffs.append(("Table 6", lab, T6_COLS[i], val, v7))
        cells.append(f"{f(val, d)} ({v7}) {'' if ok == 'ok' else '**DIFF**'}")
    lines.append(f"| {lab} | " + " | ".join(cells) + " |")
lines.append("\nCell format: code value (v7 print). Weeks meeting P95 uses P95 <= 2 % + 1e-9.\n")

# ---------- Table 12 ----------
lines.append("## Table 12 (v7) - exact-model evaluation of the designs (60 base weeks): code vs v7 print\n")
lines.append("| Sizing | C (MVA) | eps_u (%) | J exact | J_cap | J_loss | J_cap+J_loss | J_viol | E_viol | P95 mean (max) | compliance (weeks of 60) |")
lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
for lab, tag, v in T12_ROWS:
    s = S[tag]
    items = [("C", s["C"], v["C"], 0.006), ("J", s["J"], v["J"], 0.06), ("Jcap", s["Jcap"], v["Jcap"], 0.06), ("Jloss", s["Jloss"], v["Jloss"], 0.06),
             ("Jviol", s["Jviol"], v["Jviol"], 0.06), ("Eviol", s["Eviol_yr"], v["Eviol"], 0.06), ("P95", s["P95_mean"], v["P95"], 0.006),
             ("P95max", s["P95_max"], v["P95max"], 0.006), ("comp", 100.0 * s["comply_weeks"] / s["n_weeks"], v["comp"], 0.8)]
    for name, c, v7, tol in items:
        if abs(c - v7) > tol:
            diffs.append(("Table 12", lab, name, c, v7))
    lines.append(f"| {lab} | {f(s['C'],2)} ({v['C']}) | {f(s['eps_u'],1)} | {f(s['J'],1)} ({v['J']}) | {f(s['Jcap'],1)} ({v['Jcap']}) | {f(s['Jloss'],1)} ({v['Jloss']}) | "
                 f"{f(s['Jcap']+s['Jloss'],1)} ({v['Jcl']}) | {f(s['Jviol'],1)} ({v['Jviol']}) | {f(s['Eviol_yr'],1)} ({v['Eviol']}) | "
                 f"{f(s['P95_mean'],2)} ({f(s['P95_max'],2)}) [{v['P95']} ({v['P95max']})] | {s['comply_weeks']} [{v['comp']} %] |")
lines.append("\nCell format: code (v7 print). J (8) column of v7 = approximation-(8) objective: percentile 534.4, proposed 454.6 (see Table 6 reproduction).\n")

# ---------- Table 13 (certification) ----------
from scipy import stats
SB = json.load(open(CODE + "/results_exact/stepB.json"))
cb = np.array(SB["cmin"]); NB = cb.shape[0]
C_prop, C_corr = S["hs_exact_proposed"]["C"], S["hs_exact_percentile_corrected"]["C"]
lines.append("## Table 13 (v7) - certification on N = 90 independent weeks (exact model)\n")
lines.append("Upper part (order statistics C_(k+1) of the 90 weekly exact minimum ratings in stepB.json; confidence = 1 - BinomCDF(k; 90, rho)):\n")
lines.append("| k | C_(k+1), eps=1.0 | v7 | C_(k+1), eps=1.9 | v7 | conf rho=5 % | v7 | conf rho=10 % | v7 |")
lines.append("|---|---|---|---|---|---|---|---|---|")
V7_13 = [(8.65, 12.35, 99.0, 99.99), (8.54, 12.25, 94.3, 99.92), (8.50, 11.98, 83.4, 99.5), (8.36, 11.73, 66.4, 98.3), (8.30, 11.70, 47.0, 95.3)]
x1 = np.sort(cb[:, 0])[::-1]; x2 = np.sort(cb[:, 1])[::-1]
for k in range(5):
    c5 = 100 * (1 - stats.binom.cdf(k, NB, 0.05)); c10 = 100 * (1 - stats.binom.cdf(k, NB, 0.10))
    v = V7_13[k]
    for nm, c, v7, tol in (("C1", x1[k], v[0], 0.006), ("C19", x2[k], v[1], 0.006), ("rho5", c5, v[2], 0.06), ("rho10", c10, v[3], 0.006)):
        dec = 2 if nm.startswith("C") else (1 if nm == "rho5" else (2 if v7 >= 99.9 else 1))   # v7 prints 99.99, 99.92 with 2 decimals, the rest with 1
        if abs(round(c, dec) - v7) > tol:
            diffs.append(("Table 13", f"k={k}", nm, float(c), v7))
    lines.append(f"| {k} | {x1[k]:.2f} | {v[0]} | {x2[k]:.2f} | {v[1]} | {c5:.1f} | {v[2]} | {c10:.2f} | {v[3]} |")
lines.append("\nLower part (direct exact evaluation of the designs on the 90 cert weeks, P95 > 2 % + 1e-9 counted as violation):\n")
lines.append("| Quantity | Proposed, exact (code) | v7 | Percentile, corrected (code) | v7 |")
lines.append("|---|---|---|---|---|")
cert = {}
for nm, tag, Cd in (("prop", "cert_exact_proposed", C_prop), ("corr", "cert_exact_percentile_corrected", C_corr)):
    s = S[tag]
    nv_direct = NB - s["comply_weeks"]
    j = 0 if nm == "prop" else 1
    nv_cmin = int(np.sum(cb[:, j] > Cd + 1e-9))
    cp = float(stats.beta.ppf(0.95, nv_direct + 1, NB - nv_direct))
    cert[nm] = dict(C=Cd, nv_direct=nv_direct, nv_stepB=nv_cmin, emp=nv_direct / NB, cp95=cp,
                    conf5=100 * float(stats.binom.cdf(nv_direct, NB, 0.05)), conf10=100 * float(stats.binom.cdf(nv_direct, NB, 0.10)))
    cert[nm]["conf5"] = 100 - cert[nm]["conf5"] if False else 100 * (1 - float(stats.binom.cdf(nv_direct, NB, 0.05)))
    cert[nm]["conf10"] = 100 * (1 - float(stats.binom.cdf(nv_direct, NB, 0.10)))
    cert[nm]["P95_max_cert"] = s["P95_max"]
lines.append(f"| Design rating C (MVA) | {cert['prop']['C']:.2f} | 11.27 | {cert['corr']['C']:.2f} | 11.83 |")
lines.append(f"| n_v of 90, direct exact evaluation | {cert['prop']['nv_direct']} | 0 | {cert['corr']['nv_direct']} | 3 |")
lines.append(f"| n_v of 90, from stepB.json (C_min > C_design) | {cert['prop']['nv_stepB']} | 0 | {cert['corr']['nv_stepB']} | 3 |")
lines.append(f"| empirical rate (%) | {100*cert['prop']['emp']:.1f} | 0 | {100*cert['corr']['emp']:.1f} | 3.3 |")
lines.append(f"| Clopper-Pearson one-sided 95 % upper bound (%) | {100*cert['prop']['cp95']:.1f} | 3.3 | {100*cert['corr']['cp95']:.1f} | 8.4 |")
lines.append(f"| Confidence rho=5 % / 10 % (%) | {cert['prop']['conf5']:.1f} / {cert['prop']['conf10']:.2f} | 99.0 / 99.99 | {cert['corr']['conf5']:.1f} / {cert['corr']['conf10']:.1f} | 66.4 / 98.3 |")
lines.append(f"| max weekly P95 on the cert weeks (%) | {cert['prop']['P95_max_cert']:.3f} | - | {cert['corr']['P95_max_cert']:.3f} | - |")
for nm, ex_nv in (("prop", 0), ("corr", 3)):
    if cert[nm]["nv_direct"] != ex_nv or cert[nm]["nv_stepB"] != ex_nv:
        diffs.append(("Table 13", nm, "n_v", cert[nm]["nv_direct"], ex_nv))
lines.append("")

# ---------- Table 14 (suburban, Ssc 750 row) ----------
sp, sc = S["sub_approx_proposed"], S["sub_approx_percentile12"]
p95unc = np.mean([rpc.p95(rpc.vuf10(np.hypot(*load_week("sub", k)) / SSC * 100)) for k in range(40)])
red = 100 * (1 - sp["J"] / sc["J"])
lines.append("## Table 14 (v7), Ssc = 750 MVA row - suburban, 40 weeks, approximation (8)\n")
lines.append("| Quantity | code | v7 |")
lines.append("|---|---|---|")
t14 = [("P95 VUF no compensation, mean over weeks (%)", p95unc, 2.98, 2, 0.005), ("Full (MVA)", RS["c_full"], 34.9, 1, 0.05), ("Peak (MVA)", RS["c_peak"], 27.4, 1, 0.05),
       ("P95 (12) rating (MVA)", sc["C"], 8.02, 2, 0.005), ("C* (MVA)", sp["C"], 7.80, 2, 0.005), ("eps_u* (%)", sp["eps_u"], 0.75, 2, 0.005),
       ("E_viol (12) (%.h/yr)", sc["Eviol_yr"], 67.0, 1, 0.05), ("E_viol proposed (%.h/yr)", sp["Eviol_yr"], 26.8, 1, 0.05),
       ("J (12) (kUSD/yr)", sc["J"], 426, 0, 0.5), ("J proposed (kUSD/yr)", sp["J"], 361, 0, 0.5), ("J proposed, one decimal (kUSD/yr)", sp["J"], 361.5, 1, 0.05),
       ("Objective reduction (%)", red, 15, 0, 0.5)]
for lab, c, v7, d, tol in t14:
    ok = abs(round(c, d) - v7) <= tol
    if not ok:
        diffs.append(("Table 14", lab, "", float(c), v7))
    lines.append(f"| {lab} | {c:.{d}f} | {v7} {'' if ok else '**DIFF**'} |")
lines.append(f"\nSuburban compliance: proposed {sp['comply_weeks']}/40 weeks, percentile (12) {sc['comply_weeks']}/40; J terms proposed {sp['Jcap']:.1f}/{sp['Jloss']:.1f}/{sp['Jviol']:.1f}.\n")

# ---------- reference table ----------
ex = S["hs_exact_proposed"]
ref = [("High-speed, approx. (8), Ssc 750", RB["prop"]["C"], 10.44, RB["prop"]["eps"], 1.0, S["hs_approx_proposed"]["J"], 454.6),
       ("High-speed, exact phasor in the loop (J re-evaluated directly on all 60 weeks)", ex["C"], 11.27, ex["eps_u"], 1.0, ex["J"], 489.3),
       ("Suburban, approx. (8), Ssc 750", sp["C"], 7.80, sp["eps_u"], 0.75, sp["J"], 361.5)]
lines.append("## Reference table (WORKFLOW step 1)\n")
lines.append("| Result | C* code (MVA) | C* v7 | eps* code (%) | eps* v7 | J code (kUSD/yr) | J v7 |")
lines.append("|---|---|---|---|---|---|---|")
for lab, c, c7, e, e7, J, J7 in ref:
    lines.append(f"| {lab} | {c:.3f} | {c7} | {e:.2f} | {e7} | {J:.2f} | {J7} |")
    if abs(round(c, 2) - c7) > 0.005 or abs(e - e7) > 1e-9 or abs(round(J, 1) - J7) > 0.05:
        diffs.append(("Reference", lab, "", (c, e, J), (c7, e7, J7)))
lines.append(f"| Certification, proposed (exact), 90 new weeks | violating weeks {cert['prop']['nv_direct']}/90 | 0/90 | | | | |")
lines.append(f"| Certification, corrected percentile (exact), 90 new weeks | violating weeks {cert['corr']['nv_direct']}/90 | 3/90 | | | | |")
lines.append("")

json.dump(dict(diffs=diffs, cert=cert, sub=dict(p95unc=float(p95unc), red=float(red))), open(f"{OUT}/data/report_diffs.json", "w"), indent=1, default=float)
open(f"{OUT}/reproduction.md", "w").write("# Reproduction of the v7 reference results (step 1)\n\n" + "\n".join(lines))
print("\n".join(lines))
print("DIFFS:", diffs)
