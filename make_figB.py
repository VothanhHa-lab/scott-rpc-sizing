"""Figure 5 (figB_train.pdf): kinematic traction-load model, with legends and annotations."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rpc_sizing import train as tr
from rpc_sizing.experiment import base_params

plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8,
                     "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
                     "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
                     "pdf.fonttype": 42, "lines.linewidth": 1.0,
                     "axes.grid": True, "grid.alpha": 0.3,
                     "legend.fontsize": 7, "axes.titlesize": 8,
                     "savefig.bbox": "tight"})
BLUE, ORANGE, VERM, GREY = "#0072B2", "#E69F00", "#D55E00", "#555555"

p = base_params()
rng = np.random.default_rng(7)
e, g = p["_grade_edges"], p["_grades"]
P1, L1 = tr.run_train(p, rng, e, g, stop=False, details=True)
P2, L2 = tr.run_train(p, rng, e, g, stop=True,
                      restriction=(6000.0, 10000.0, 200 / 3.6), details=True)
t2 = np.arange(len(P2)) / 60
v2 = L2[:, 1] * 3.6
x2 = L2[:, 0]
istop = np.where(v2 < 1)[0]
t_stop0, t_stop1 = t2[istop[0]], t2[istop[-1]]
ir = np.where((x2 > 6000) & (x2 < 10000))[0]
t_r0, t_r1 = t2[ir[0]], t2[ir[-1]]

fig, ax = plt.subplots(2, 2, figsize=(6.85, 4.6))
for P_, L_, ls, lab, col in [(P1, L1, "-", "non-stop run", BLUE),
                             (P2, L2, "--", "stop + speed restriction", VERM)]:
    t = np.arange(len(P_)) / 60
    ax[0, 0].plot(t, L_[:, 1] * 3.6, ls, color=col, lw=1.1, label=lab)
    ax[0, 1].plot(t, L_[:, 2] / 1e3, ls, color=col, lw=1.1, label=lab)
    ax[1, 0].plot(t, P_, ls, color=col, lw=1.1, label=lab)

# shaded intervals of the second run in (a)-(c)
for a in (ax[0, 0], ax[0, 1], ax[1, 0]):
    a.axvspan(t_r0, t_r1, color=GREY, alpha=0.10, lw=0)
    a.axvspan(t_stop0, t_stop1, color=ORANGE, alpha=0.15, lw=0)
    a.set_xlabel("Time in the zone (min)")

# (a) speed
a = ax[0, 0]
a.set_ylabel("Speed (km/h)"); a.set_title("(a)")
a.set_ylim(-20, 345)
a.annotate("speed restriction\n200 km/h (km 6–10)", xy=((t_r0 + t_r1) / 2, 200),
           xytext=(3.2, 120), fontsize=7, ha="left",
           arrowprops=dict(arrowstyle="->", lw=0.6, color=GREY))
a.annotate("station stop", xy=((t_stop0 + t_stop1) / 2, 0), xytext=(10.6, 40),
           fontsize=7, ha="left", arrowprops=dict(arrowstyle="->", lw=0.6, color=GREY))
a.annotate("line speed 300 km/h", xy=(12.5, 300), xytext=(10.2, 318), fontsize=7, ha="left")

# (b) force
a = ax[0, 1]
a.set_ylabel("Tractive / braking force (kN)"); a.set_title("(b)")
a.axhline(0, color="k", lw=0.5)
a.text(0.6, 255, "traction (> 0)", fontsize=7)
a.text(0.6, -265, "electric braking (< 0)", fontsize=7)
a.set_ylim(-290, 310)

# (c) electrical power
a = ax[1, 0]
a.set_ylabel("$P_\\mathrm{el}$ of one train (MW)"); a.set_title("(c)")
a.axhline(0, color="k", lw=0.5)
a.annotate("regeneration\n($P_\\mathrm{el}$ < 0)", xy=(5.3, -7.0), xytext=(10.8, -6.5),
           fontsize=7, ha="left", arrowprops=dict(arrowstyle="->", lw=0.6, color=GREY))
a.text(11.2, 4.0, "maximum power\nabout 10–11 MW", fontsize=7, ha="left", va="top")

# (d) substation load
d = np.load("results/base_w000.npz")
P, Q = d["P"].astype(float), d["Q"].astype(float)
i0, i1 = (24 + 7) * 3600, (24 + 9) * 3600   # day 2, 07:00-09:00 (peak)
th = (np.arange(i0, i1) - 24 * 3600) / 3600
a = ax[1, 1]
a.plot(th, P[i0:i1], color=BLUE, lw=0.6, label="active power $P_L$")
a.plot(th, Q[i0:i1], color=ORANGE, lw=0.8, label="reactive power $Q_L$")
a.axhline(0, color="k", lw=0.5)
k = np.argmin(P[i0:i1])
a.annotate("net regeneration\n($P_L$ < 0)", xy=(th[k], P[i0 + k]), xytext=(8.35, -12),
           fontsize=7, ha="left", va="center",
           arrowprops=dict(arrowstyle="->", lw=0.6, color=GREY))
a.set_xlabel("Time of day (h), morning peak, week 1, day 2")
a.set_ylabel("Substation load (MW, Mvar)"); a.set_title("(d)")
a.set_ylim(-20, 68)
a.legend(loc="upper right", ncol=2)

from matplotlib.patches import Patch
from matplotlib.lines import Line2D
h = [Line2D([], [], color=BLUE, ls="-", lw=1.1), Line2D([], [], color=VERM, ls="--", lw=1.1),
     Patch(color=GREY, alpha=0.25), Patch(color=ORANGE, alpha=0.3)]
lab = ["non-stop run", "run with speed restriction and station stop",
       "speed restriction (second run)", "station stop (second run)"]
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.legend(h, lab, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.0))
fig.savefig("figs/figB_train.pdf")
fig.savefig("/tmp/figB_new.png", dpi=130)
print("stop", t_stop0, t_stop1, "restriction", t_r0, t_r1, "Pmin", P[i0:i1].min())
