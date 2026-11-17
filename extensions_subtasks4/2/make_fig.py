import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 9, "axes.grid": True, "grid.alpha": .3})
D = "/home/claude/subtasks4/2/data"; R = "/home/claude/subtasks4/2/results"
# (a) duration curve of the alpha-leg current, pooled 60 weeks, ordered over the 18 h/day operating seconds
Is = []
for k in range(60):
    Is.append(np.load(f"{D}/legs_w{k:03d}.npz")["I_alpha_pu40"])
x = np.sort(np.concatenate(Is))[::-1]
n = len(x); frac = 100.0 * np.arange(1, n + 1) / n
sel = np.unique(np.concatenate([np.arange(0, 2000), np.geomspace(2000, n - 1, 1500).astype(int)]))
fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0))
a = ax[0]
a.loglog(frac[sel], x[sel], color="#1f77b4", lw=1.4, label=r"$I_\alpha/I_N$, $S_N=40$ MVA")
a.loglog(frac[sel], 2 * x[sel], color="#d62728", lw=1.4, label=r"$I_\alpha/I_N$, $S_N=20$ MVA")
for y, c in ((1.0, "k"), (1.3, "#555"), (1.5, "#555"), (2.0, "#555")):
    a.axhline(y, color=c, lw=.7, ls="--")
a.set_xlim(1e-5, 100); a.set_ylim(0.05, 4)
a.set_xlabel("share of all seconds exceeding (%)"); a.set_ylabel("loading of Scott leg $\\alpha$ (pu)")
a.legend(frameon=False, fontsize=8, loc="lower left"); a.set_title("(a) duration curve, 60 weeks", fontsize=9)
# (b) time series around the 65.8 MVA instant (week 15)
z = np.load(f"{D}/legs_w015.npz"); t0 = 65956; i = np.arange(t0 - 300, t0 + 301); t = i - t0
b = ax[1]
b.plot(t, z["S_alpha"][i] / 40, color="#1f77b4", label=r"$S_\alpha/40$ MVA")
b.plot(t, z["I_alpha_pu40"][i], color="#ff7f0e", label=r"$I_\alpha/I_N$")
b.plot(t, np.hypot(z["P_L"][i], z["Q_L"][i]) / 40, color="#7f7f7f", ls=":", label=r"$S_L/40$ MVA")
b.plot(t, z["I_rpc_alpha_pu"][i], color="#2ca02c", label=r"RPC $\alpha$ current / rated")
b.axhline(1.0, color="k", lw=.7, ls="--"); b.set_xlabel("time from the peak instant (s), week 15")
b.set_ylabel("pu"); b.legend(frameon=False, fontsize=7, loc="upper left", ncol=1); b.set_title("(b) peak of the 65.8 MVA week", fontsize=9)
b.set_ylim(0, 2.0)
plt.tight_layout(); plt.savefig(f"{R}/fig_leg_loading.pdf"); plt.savefig(f"{R}/fig_leg_loading.png", dpi=170)
