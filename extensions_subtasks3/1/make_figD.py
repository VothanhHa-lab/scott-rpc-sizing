"""figD_dynamic.pdf for C*=11.27 MVA, eps_u*=1 %: three events, with/without power feed-forward."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8,
                     "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
                     "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
                     "pdf.fonttype": 42, "lines.linewidth": 1.0,
                     "axes.grid": True, "grid.alpha": 0.3,
                     "legend.fontsize": 7, "axes.titlesize": 8,
                     "savefig.bbox": "tight"})
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7F7F7F"
Z = np.load("dyn_traces.npz")
def tr(cid, ff, k): return Z[f"{cid}_{ff}__{k}"]
COLS = [("a2", 40.0, (-0.05, 0.40), "(a) +10 MW load step"),
        ("b3", 40.0, (-0.05, 0.40), "(b) $-$10 MW load step (breaker trip)"),
        ("c1", 30.0, (-4.0, 26.0), "(c) power reversal (regeneration)")]
fig, ax = plt.subplots(3, 3, figsize=(6.85, 5.6))
for j, (cid, t0, xl, title) in enumerate(COLS):
    t = tr(cid, True, "t") - t0
    ax[0, j].plot(t, tr(cid, True, "PL"), color=GREY, lw=0.9, label="$P_L$")
    ax[0, j].plot(t, tr(cid, True, "Pa"), color=BLUE, lw=1.1, label="$P_x$ ($\\alpha$ leg)")
    ax[0, j].plot(t, tr(cid, True, "Qa"), color=GREEN, lw=0.9, ls=":", label="$q$ ($\\alpha$ leg)")
    ax[0, j].set_title(title); ax[0, j].set_xlim(*xl)
    ax[1, j].plot(t, tr(cid, True, "Vdc") / 1e3, color=BLUE, lw=1.1, label="with feed-forward")
    ax[1, j].plot(t, tr(cid, False, "Vdc") / 1e3, color=VERM, lw=0.9, ls="--", label="without feed-forward")
    for v in (3.15, 3.85):
        ax[1, j].axhline(v, color="k", lw=0.7, ls="-.")
    ax[1, j].set_ylim(2.8, 4.05); ax[1, j].set_xlim(*xl)
    ax[2, j].plot(t, tr(cid, True, "Ia"), color=BLUE, lw=1.1, label="$\\alpha$ leg")
    ax[2, j].plot(t, tr(cid, True, "Ib"), color=VERM, lw=1.0, label="$\\beta$ leg, with FF")
    ax[2, j].plot(t, tr(cid, False, "Ib"), color=ORANGE, lw=0.9, ls="--", label="$\\beta$ leg, without FF")
    ax[2, j].axhline(1.0, color="k", lw=0.7, ls="-.")
    ax[2, j].set_ylim(0.0, 1.12); ax[2, j].set_xlim(*xl)
    ax[2, j].set_xlabel("Time since the start of the event (s)")
ax[0, 0].set_ylabel("MW, Mvar"); ax[1, 0].set_ylabel("$V_\\mathrm{dc}$ (kV)"); ax[2, 0].set_ylabel("$I_\\mathrm{RPC}/I_\\mathrm{rated}$")
ax[0, 0].legend(loc="upper left", fontsize=6.5); ax[1, 0].legend(loc="lower right", fontsize=6.5)
ax[2, 0].legend(loc="lower right", fontsize=6.5)
fig.tight_layout(); fig.savefig("figD_dynamic.pdf"); fig.savefig("figD_dynamic_preview.png", dpi=130); plt.close(fig)
print("ok")
