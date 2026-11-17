"""Build figure, table fragments, summary JSON and section.tex from the stored results."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = "/home/claude/subtasks/5/"
BLUE, ORANGE, GREEN, VERM, PURPLE = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7"
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8,
                     "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
                     "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})

R = {c: json.load(open(D + f"results_{c}.json")) for c in ["base", "suburban"]}
R10 = {c: json.load(open(D + f"results10_{c}.json")) for c in ["base", "suburban"]}
RA = {c: json.load(open(D + f"results_alphastar_{c}.json"))["best"] for c in ["base", "suburban"]}

f1 = lambda x: f"{x:.1f}"
f2 = lambda x: f"{x:.2f}"
f0 = lambda x: f"{x:.0f}"


def cols(c):
    r, r10 = R[c], R10[c]
    A = r["SAA_A"]
    return [("p95", "Percentile (6)", r["reference"]["p95"]),
            ("a5", "SAA-1s, $\\alpha=5$\\%", A["0.05"]),
            ("a2", "SAA-1s, $\\alpha=2$\\%", A["0.02"]),
            ("a1", "SAA-1s, $\\alpha=1$\\%", A["0.01"]),
            ("ast", f"SAA-1s, $\\alpha^\\star={100*RA[c]['alpha']:.1f}$\\%", RA[c]),
            ("t1", "SAA-10min, $\\alpha_{10}=1$\\%", r10["0.01"]["best"]),
            ("prop", "Proposed (9)--(11)", r["reference"]["proposed"])]


def table(c, full=True):
    cs = cols(c)
    rows = []

    def row(lab, key, fmt):
        rows.append(lab + " & " + " & ".join(fmt(m[key]) for _, _, m in cs) + "\\\\")
    row("Rating per leg $C$ (MVA)", "C", f1)
    row("Threshold $\\varepsilon_u$ (\\%)", "eps", lambda x: f"{x:g}")
    row("P95 of 10-min VUF (\\%)", "p95_mean", f2)
    row("Weeks meeting the P95 criterion (\\%)", "comply", lambda x: f0(100 * x))
    if full:
        row("P99 of 10-min VUF (\\%)", "p99", f2)
        row("Maximum 10-min VUF (\\%)", "vmax", f2)
        row("10-min values above 2\\% (\\%)", "share", lambda x: f1(100 * x))
        row("1-s values above 2\\% (\\%)", "inst_share", lambda x: f1(100 * x))
    row("Exceedance $E_\\mathrm{viol}$ (\\%$\\cdot$h/yr)", "Eviol", lambda x: "0" if x < 0.05 else f1(x))
    if full:
        row("Energy processed per leg (GWh/yr)", "Etr", lambda x: f1(x / 1000))
        row("Losses $E_\\mathrm{loss}$ (MWh/yr)", "Eloss", f0)
        rows.append("$J$: capital / losses / exceedance (kUSD/yr) & " + " & ".join(
            f"{m['Jcap']:.0f}/{m['Jloss']:.0f}/{m['Jviol']:.0f}" for _, _, m in cs) + "\\\\")
    row("Expected annual cost $J$ (kUSD/yr)", "J", f0)
    h1 = [" ", "Percentile", "SAA-1s", "SAA-1s", "SAA-1s", "SAA-1s", "SAA-10min", "Proposed"]
    h2 = ["", "sizing (6)", "$\\alpha=5$\\%", "$\\alpha=2$\\%", "$\\alpha=1$\\%",
          f"$\\alpha^\\star={100*RA[c]['alpha']:.1f}$\\%", "$\\alpha_{10}=1$\\%", "(9)--(11)"]
    head = " & ".join(h1[1:]).join(["", ""]) if False else (" & " + " & ".join(h1[1:]) + "\\\\\n" + " & " + " & ".join(h2[1:]) + "\\\\")
    return head, "\n".join(rows)


# ---------------- figure ----------------
fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.7))
for c, col, lab in [("base", BLUE, "high-speed"), ("suburban", ORANGE, "suburban")]:
    A = R[c]["SAA_A"]
    al = np.array([100 * v["alpha"] for v in A.values()])
    ax[0].plot(al, [100 * v["comply"] for v in A.values()], "o-", color=col, ms=3.5, lw=1.2, label=lab)
    ax[1].plot(al, [v["J"] for v in A.values()], "o-", color=col, ms=3.5, lw=1.2, label=f"SAA-1s, {lab}")
    ax[1].axhline(R[c]["reference"]["proposed"]["J"], color=col, ls="--", lw=1.0)
    ax[1].axhline(R[c]["reference"]["p95"]["J"], color=col, ls=":", lw=1.0)
    ax[0].plot([100 * RA[c]["alpha"]], [100 * RA[c]["comply"]], "*", color=col, ms=8, mec="k", mew=0.4)
ax[0].axhline(95, color="0.4", ls=":", lw=0.9)
ax[0].text(0.0075, 88, "95 % of weeks", color="0.3", fontsize=7)
for a in ax:
    a.set_xscale("log")
    a.set_xlim(7, 0.007)
    a.set_xticks([5, 2, 1, 0.5, 0.1, 0.01])
    a.set_xticklabels(["5", "2", "1", "0.5", "0.1", "0.01"])
    a.minorticks_off()
    a.set_xlabel("Chance-constraint level $\\alpha$ (%)")
ax[0].set_ylabel("Weeks meeting the P95 criterion (%)")
ax[1].set_ylabel("Expected annual cost $J$ (kUSD/yr)")
ax[0].legend(frameon=False, loc="lower right", fontsize=7, bbox_to_anchor=(1.0, 0.1))
ax[0].set_title("(a)", loc="left", fontsize=8, fontweight="bold")
ax[1].set_title("(b)", loc="left", fontsize=8, fontweight="bold")
ax[1].text(0.0075, 318, "dashed: proposed; dotted: percentile (6)", fontsize=6.5, color="0.3")
ax[1].set_ylim(300, 850)
ax[0].text(1.2, 5, "stars: calibrated $\\alpha^\\star$", fontsize=6.5, color="0.3")
fig.tight_layout()
fig.savefig(D + "figS_saa_alpha.pdf")

# ---------------- summary ----------------
S = {}
for c in ["base", "suburban"]:
    ref = R[c]["reference"]
    A = R[c]["SAA_A"]
    S[c] = dict(
        N_weeks=len(R[c]["weeks"]),
        percentile=ref["p95"], proposed=ref["proposed"], percentile_Copt=ref["p95_Copt"],
        SAA_1s={k: A[k] for k in ["0.05", "0.02", "0.01"]},
        SAA_1s_alpha_star=RA[c],
        SAA_joint_1s={a: R[c]["SAA_B"][a]["best"] for a in R[c]["SAA_B"]},
        SAA_10min={a: R10[c][a]["best"] for a in ["0.05", "0.02", "0.01"]},
        per_week_C_alpha=R[c]["per_week_C_alpha"],
    )
    P = ref["proposed"]
    S[c]["relative_to_proposed"] = {
        "SAA_1s_1pct": dict(dC_pct=100 * (A["0.01"]["C"] / P["C"] - 1), dJ_pct=100 * (A["0.01"]["J"] / P["J"] - 1)),
        "SAA_1s_alpha_star": dict(dC_pct=100 * (RA[c]["C"] / P["C"] - 1), dJ_pct=100 * (RA[c]["J"] / P["J"] - 1)),
        "SAA_10min_1pct": dict(dC_pct=100 * (R10[c]["0.01"]["best"]["C"] / P["C"] - 1), dJ_pct=100 * (R10[c]["0.01"]["best"]["J"] / P["J"] - 1)),
        "SAA_10min_2pct": dict(dC_pct=100 * (R10[c]["0.02"]["best"]["C"] / P["C"] - 1), dJ_pct=100 * (R10[c]["0.02"]["best"]["J"] / P["J"] - 1)),
    }
json.dump(S, open(D + "results_saa_summary.json", "w"), indent=1)

h, t = table("base", True)
open(D + "table_base.tex", "w").write(h + "\n\\hline\n" + t + "\n")
h2, t2 = table("suburban", False)
open(D + "table_suburban.tex", "w").write(h2 + "\n\\hline\n" + t2 + "\n")
print(json.dumps({c: S[c]["relative_to_proposed"] for c in S}, indent=1))
