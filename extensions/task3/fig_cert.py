import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 9, "pdf.fonttype": 42})
B = json.load(open("/home/claude/code/results_exact/stepB.json")); A = json.load(open("/home/claude/code/results_exact/stepA.json"))
a = json.load(open("analysis3.json")); cb = np.array(B["cmin"]); cm = np.array(A["cmin"])
BLUE, ORANGE, VERM, GREEN = "#0072B2", "#E69F00", "#D55E00", "#009E73"
fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
for j, (e, col, lab) in enumerate([(1.0, BLUE, r"$\varepsilon_u=1.0\,\%$"), (1.9, ORANGE, r"$\varepsilon_u=1.9\,\%$")]):
    x = np.sort(cb[:, j]); ax[0].step(x, np.arange(1, len(x) + 1) / len(x), where="post", color=col, label=lab + ", 90 fresh weeks")
    ax[0].axvline(a["prop"]["C"] if j == 0 else a["conv"]["C"], color=col, ls="--", lw=1)
x = np.sort(cm[:, 4]); ax[0].step(x, np.arange(1, 61) / 60, where="post", color="0.5", lw=1, label=r"$\varepsilon_u=1.0\,\%$, 60 base weeks")
ax[0].axhline(.95, color="k", ls=":", lw=.8)
ax[0].set_xlabel("weekly minimum rating $C_{\\min}^{(k)}$ (MVA)"); ax[0].set_ylabel("empirical CDF"); ax[0].legend(fontsize=7, loc="lower right", frameon=False)
ax[0].text(.02, .97, "(a)", transform=ax[0].transAxes, va="top", fontweight="bold")
k = np.arange(0, 8)
from scipy import stats
for rho, col in [(0.05, VERM), (0.10, GREEN)]:
    ax[1].plot(k, 1 - stats.binom.cdf(k, 90, rho), "o-", color=col, ms=4, label=r"$\rho=%d\,\%%$" % (rho * 100))
ax[1].axhline(.95, color="k", ls=":", lw=.8)
ax[1].set_xlabel(r"$k$ (rating $=(k{+}1)$-th largest of 90 weekly minima)"); ax[1].set_ylabel(r"confidence $1-\beta$"); ax[1].legend(fontsize=7, frameon=False)
ax[1].text(.02, .05, "(b)", transform=ax[1].transAxes, va="bottom", fontweight="bold")
for a_ in ax:
    a_.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("figH_certification.pdf")
