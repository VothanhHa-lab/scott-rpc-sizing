"""Figures B-E and the new sizing figure (vector PDF)."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyse import load, methods, weekly_cmin, cost_terms, metrics
from rpc_sizing.params import TRAIN, SEED0
from rpc_sizing import train as tr, rpc
from rpc_sizing.experiment import base_params

plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8,
                     "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
                     "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
                     "pdf.fonttype": 42, "lines.linewidth": 1.0,
                     "axes.grid": True, "grid.alpha": 0.3,
                     "legend.fontsize": 7, "axes.titlesize": 8,
                     "savefig.bbox": "tight"})
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7F7F7F"
MCOL = dict(full=PURPLE, peak=ORANGE, p95=BLUE, proposed=VERM)
OUT = "figs"
import os; os.makedirs(OUT, exist_ok=True)
SSC = 750
s = load("base")
M = methods(s, SSC)
Cp, ep = M["proposed"]["C"], M["proposed"]["eps"]
Cc = M["p95"]["C"]

# ---------------- Figure B: train load -----------------------------------
p = base_params()
rng = np.random.default_rng(7)
e, g = p["_grade_edges"], p["_grades"]
P1, L1 = tr.run_train(p, rng, e, g, stop=False, details=True)
P2, L2 = tr.run_train(p, rng, e, g, stop=True,
                      restriction=(6000.0, 10000.0, 200 / 3.6), details=True)
fig, ax = plt.subplots(2, 2, figsize=(6.85, 4.4))
for P_, L_, ls, lab, col in [(P1, L1, "-", "non-stop run", BLUE),
                        (P2, L2, "--", "stop + speed restriction", VERM)]:
    t = np.arange(len(P_)) / 60
    ax[0, 0].plot(t, L_[:, 1] * 3.6, ls, color=col, lw=1.1, label=lab)
    ax[0, 1].plot(t, L_[:, 2] / 1e3, ls, color=col, lw=1.1, label=lab)
    ax[1, 0].plot(t, P_, ls, color=col, lw=1.1, label=lab)
ax[0, 0].set_ylabel("Speed (km/h)"); ax[0, 0].set_title("(a)")
ax[0, 1].set_ylabel("Tractive / braking force (kN)"); ax[0, 1].set_title("(b)")
ax[1, 0].set_ylabel("$P_\\mathrm{el}$ of one train (MW)"); ax[1, 0].set_title("(c)")
for a in (ax[0, 0], ax[0, 1], ax[1, 0]):
    a.set_xlabel("Time in the zone (min)")
ax[0, 0].legend(loc="lower left")
d = np.load("results/base_w000.npz")
P, Q = d["P"].astype(float), d["Q"].astype(float)
i0, i1 = (24 + 7) * 3600, (24 + 9) * 3600   # day 2, 07:00-09:00 (peak)
th = (np.arange(i0, i1) - 24 * 3600) / 3600
ax[1, 1].plot(th, P[i0:i1], color=BLUE, lw=0.6, label="$P_L$")
ax[1, 1].plot(th, Q[i0:i1], color=ORANGE, lw=0.6, label="$Q_L$")
ax[1, 1].set_xlabel("Time of day (h)"); ax[1, 1].set_ylabel("Substation load (MW, Mvar)")
ax[1, 1].set_title("(d)"); ax[1, 1].legend(loc="upper right")
fig.tight_layout(); fig.savefig(f"{OUT}/figB_train.pdf"); plt.close(fig)

# ---------------- Figure C: VUF before/after -----------------------------
S = np.hypot(P, Q)
v_none = rpc.vuf10(S / SSC * 100)
v_conv = rpc.vuf10(rpc.compensate(P, Q, Cc, 2.0, SSC)[1])
v_prop = rpc.vuf10(rpc.compensate(P, Q, Cp, ep, SSC)[1])
fig, ax = plt.subplots(1, 2, figsize=(6.85, 2.8))
day = slice(144, 288)  # day 2
tt = np.arange(144) / 6
ax[0].step(tt, v_none[day], where="post", color=GREY, lw=0.9, label="no compensation")
ax[0].step(tt, v_conv[day], where="post", color=BLUE, lw=0.9, ls="--",
           label=f"P95 sizing, C={Cc:.1f} MVA")
ax[0].step(tt, v_prop[day], where="post", color=VERM, lw=1.1,
           label=f"proposed, C={Cp:.1f} MVA, $\\varepsilon_u$={ep:.2f}%")
ax[0].axhline(2, color="k", lw=0.8, ls="-."); ax[0].set_xlim(0, 24)
ax[0].set_xlabel("Time of day (h)"); ax[0].set_ylabel("VUF$_{10\\,min}$ (%)")
ax[0].set_title("(a)"); ax[0].legend(loc="upper left")
for v, c, ls, lab in [(v_none, GREY, "-", "no compensation"),
                      (v_conv, BLUE, "--", "P95 sizing"),
                      (v_prop, VERM, "-", "proposed")]:
    x = np.sort(v); y = 1 - np.arange(1, len(x) + 1) / len(x)
    ax[1].plot(x, y * 100, ls, color=c, lw=1.1,
               label=f"{lab}: {100*np.mean(v > 2):.1f}% > 2%")
ax[1].axvline(2, color="k", lw=0.8, ls="-."); ax[1].axhline(5, color="0.4", lw=0.6, ls=":")
ax[1].set_yscale("log"); ax[1].set_ylim(0.1, 100)
ax[1].set_xlabel("VUF$_{10\\,min}$ (%)"); ax[1].set_ylabel("Share of 10-min values exceeding (%)")
ax[1].set_title("(b)"); ax[1].legend(loc="lower left")
fig.tight_layout(); fig.savefig(f"{OUT}/figC_vuf.pdf"); plt.close(fig)
stats_C = dict(share_none=float(np.mean(v_none > 2)), share_conv=float(np.mean(v_conv > 2)),
               share_prop=float(np.mean(v_prop > 2)), p95_none=rpc.p95(v_none),
               p95_conv=rpc.p95(v_conv), p95_prop=rpc.p95(v_prop),
               max_conv=float(v_conv.max()), max_prop=float(v_prop.max()))

# ---------------- Figure D: dynamic RPC -----------------------------------
dd = np.load("results/dyn.npz")
t = dd["t_True"]
fig, ax = plt.subplots(3, 1, figsize=(6.85, 5.4), sharex=True)
ax[0].plot(t, dd["PL_True"], color=GREY, lw=0.9, label="$P_L$")
ax[0].plot(t, dd["Pa_True"], color=BLUE, lw=1.1, label="$P_x$ ($\\alpha$ leg)")
ax[0].plot(t, dd["Qa_True"], color=GREEN, lw=0.9, ls=":", label="$q$ ($\\alpha$ leg)")
ax[0].set_ylabel("MW, Mvar"); ax[0].legend(loc="upper right", ncol=3); ax[0].set_title("(a)")
ax[1].plot(t, dd["Vdc_True"] / 1e3, color=BLUE, lw=1.1, label="with power feed-forward")
ax[1].plot(t, dd["Vdc_False"] / 1e3, color=VERM, lw=0.9, ls="--", label="without feed-forward")
for v in (3.15, 3.85):
    ax[1].axhline(v, color="k", lw=0.7, ls="-.")
ax[1].set_ylim(3.0, 3.95); ax[1].set_ylabel("$V_\\mathrm{dc}$ (kV)"); ax[1].legend(loc="lower left"); ax[1].set_title("(b)")
ax[2].plot(t, dd["Ia_True"], color=BLUE, lw=1.1, label="$\\alpha$ leg")
ax[2].plot(t, dd["Ib_True"], color=VERM, lw=0.9, ls="--", label="$\\beta$ leg")
ax[2].axhline(1.0, color="k", lw=0.7, ls="-.")
ax[2].set_ylabel("$I_\\mathrm{RPC}/I_\\mathrm{rated}$"); ax[2].set_xlabel("Time (s)")
ax[2].legend(loc="lower right"); ax[2].set_title("(c)")
fig.tight_layout(); fig.savefig(f"{OUT}/figD_dynamic.pdf"); plt.close(fig)

# ---------------- Figure E: convergence -----------------------------------
fig, ax = plt.subplots(1, 1, figsize=(3.31, 2.6))
from scipy import stats
for e_, ls, lab, col in [(2.0, "--", "P95 sizing ($\\varepsilon_u$=2%)", BLUE),
                    (ep, "-", f"threshold policy ($\\varepsilon_u$={ep:.2f}%)", VERM)]:
    x = weekly_cmin(s, SSC, e_)
    n = np.arange(1, len(x) + 1)
    m = np.cumsum(x) / n
    sd = np.array([x[:k].std(ddof=1) if k > 1 else np.nan for k in n])
    h = stats.t.ppf(0.975, np.maximum(n - 1, 1)) * sd / np.sqrt(n)
    q = np.array([np.quantile(x[:k], 0.95, method="inverted_cdf") for k in n])
    ax.plot(n, m, ls, color=col, lw=1.1, label=lab + ", mean")
    ax.fill_between(n, m - h, m + h, color=col, alpha=0.2, lw=0)
    ax.plot(n, q, ":", color=col, lw=1.0, label="95% quantile over weeks")
    ax.plot(n, x, ".", color=col, alpha=0.5, ms=2.5)
ax.set_xlabel("Number of simulated weeks $N$"); ax.set_ylabel("$C_{95}$ per leg (MVA)")
ax.legend(loc="center right", fontsize=7); ax.set_xlim(1, len(x))
fig.tight_layout(); fig.savefig(f"{OUT}/figE_convergence.pdf"); plt.close(fig)

# ---------------- Figure 10 (new): sizing vs eps_u and Ssc ----------------
d750 = s["design"][str(SSC)]
nf = len(s["c_fact"])
fig, ax = plt.subplots(1, 2, figsize=(6.85, 2.8))
eg = s["eps_grid"]
Jb, Cb, Cd = [], [], []
for i, e_ in enumerate(eg):
    j = min(range(i * nf, i * nf + nf), key=lambda k: cost_terms(d750["evals"], k)[0])
    Jb.append(cost_terms(d750["evals"], j)); Cb.append(d750["cands"][j][1])
    Cd.append(d750["c_design"][i])
Jb = np.array(Jb)
ax[0].bar(eg, Jb[:, 1], width=0.18, color=BLUE, label="capital")
ax[0].bar(eg, Jb[:, 2], width=0.18, bottom=Jb[:, 1], color=ORANGE, label="losses")
ax[0].bar(eg, Jb[:, 3], width=0.18, bottom=Jb[:, 1] + Jb[:, 2], color=VERM,
          label="VUF exceedance")
ax[0].set_xlabel("Compensation threshold $\\varepsilon_u$ (%)"); ax[0].set_ylabel("$J$ (kUSD/yr)")
a2 = ax[0].twinx(); a2.grid(False)
a2.plot(eg, Cd, "o-", color="k", ms=3, lw=1, label="$C_{\\min}(\\varepsilon_u)$")
a2.plot(eg, Cb, "s--", color="k", ms=3, lw=1, label="$C^*(\\varepsilon_u)$")
a2.set_ylabel("Rating per leg (MVA)"); a2.set_ylim(0, 16)
h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
ax[0].legend(h1 + h2, l1 + l2, loc="upper center", ncol=2, fontsize=6.5)
ax[0].set_ylim(0, 700); ax[0].set_title("(a)")
ss = [500, 750, 1000, 1500, 2000]
rows = {k: [] for k in ("full", "peak", "p95", "proposed")}
for S_ in ss:
    mm = methods(s, S_)
    for k in rows:
        rows[k].append(mm[k]["C"])
for k, st, lab in [("full", ":", "full compensation"), ("peak", "-.", "peak sizing (5)"),
                   ("p95", "--", "P95 sizing (6)"), ("proposed", "-", "proposed (9)-(11)")]:
    ax[1].plot(ss, rows[k], st, color=MCOL[k], marker="o", ms=3, lw=1.3, label=lab)
ax[1].set_xlabel("$S_\\mathrm{sc}$ (MVA)"); ax[1].set_ylabel("Rating per leg (MVA)")
ax[1].legend(fontsize=7); ax[1].set_title("(b)")
fig.tight_layout(); fig.savefig(f"{OUT}/fig10_sizing.pdf"); plt.close(fig)

json.dump(stats_C, open("results/figC_stats.json", "w"), indent=1)
print(stats_C)
