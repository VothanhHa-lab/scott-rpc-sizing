"""Capital + hardware + loss against exceedance for the percentile family (eps 1.9) and the proposed family (eps 1.0, 0.75) - exact model, evaluated candidates."""
import sys, os, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from lib6 import *
import costmodel as cm
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 9, "pdf.fonttype": 42})
S = exact_set([f"{RES}/exact_extra.json"])
cmp = json.load(open(f"{RES}/compare_exact.json"))
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=False)
for ax, (key, ttl) in zip(axs, (("v7", "Cost model of (16), no hardware items"), ("TF", "With transformers and 100 Hz filter"))):
    hw = SCEN = {"v7": Hw("none", trafo=False), "TF": Hw("filter", "central", True)}[key]
    for eps, col, lab in ((1.9, "#d95f02", r"percentile, $\varepsilon_u$=1.9 %"), (1.0, "#1b9e77", r"proposed family, $\varepsilon_u$=1.0 %"), (0.75, "#7570b3", r"$\varepsilon_u$=0.75 %"), (1.5, "#999999", r"$\varepsilon_u$=1.5 %")):
        cs = sorted([c for c in S if abs(c.eps - eps) < 1e-9 and ok(c) and c.Ev * W > 1.0], key=lambda c: c.C)
        ax.plot([c.Ev * W for c in cs], [hw.CL(c) for c in cs], "-o", ms=3, lw=1.2, color=col, label=lab)
    sc = cmp["scenarios"][key]
    for cn, ls, lb in (("cap_pct_opt", "--", "cap 1: percentile, $C$ optimised"), ("cap_prop", ":", "cap 2: proposed design")):
        ax.axvline(sc["equal_exceedance"][cn]["cap"], color="k", lw=0.7, ls=ls, label=lb)
    ax.set_xlim(20, 110); ax.set_xlabel(r"$E_\mathrm{viol}$ (%$\cdot$h/yr)"); ax.set_title(ttl, fontsize=9)
    ax.grid(alpha=0.3)
axs[0].set_ylabel("capital + hardware + losses (kUSD/yr)")
axs[0].legend(fontsize=7, frameon=False)
fig.tight_layout()
fig.savefig("/home/claude/subtasks4/6/deliver/fig_equal_exceedance.pdf")
fig.savefig("/home/claude/subtasks4/6/deliver/fig_equal_exceedance.png", dpi=160)
print("saved")
