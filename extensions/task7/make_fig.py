import sys
from common import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8, "mathtext.fontset": "custom",
    "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic", "pdf.fonttype": 42,
    "axes.grid": True, "grid.alpha": 0.3, "legend.fontsize": 6.5, "axes.titlesize": 8})
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7F7F7F"
from rpc_sizing.params import RPC
name = sys.argv[1]
D = json.load(open(os.path.join(HERE, f"design_{name}.json")))
best = min(D["cands"], key=lambda c: c["J"]); C = best["C"]; vs, q = D["vstar"], D["q"]; iq = QS.index(q)
cmp_ = json.load(open(os.path.join(HERE, "compare.json")))
TAB = fold_tables("A"); G = TAB.get(C, iq)
# search windows in weeks 0..9
cand = []
store = {}
for k in range(10):
    P, Q = load_week(k); W = windows(P, Q); F = Feat(W[2], Ssc)
    sx, v = run(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F)
    s15, v15 = rpc.compensate(P, Q, C, 1.0, Ssc); s15 = s15.reshape(W[0].shape); v15 = v15.reshape(W[0].shape)
    rb = np.sqrt((v ** 2).mean(1)); r15 = np.sqrt((v15 ** 2).mean(1)); ru = np.sqrt(((W[2] / Ssc * 100) ** 2).mean(1))
    store[k] = (W, F, sx, v, s15, v15)
    for w in range(NW):
        cand.append((k, w, ru[w], r15[w], rb[w], sx[w].sum() / 3600, s15[w].sum() / 3600))
cand = np.array(cand)
okA = (cand[:, 2] > 2.8) & (cand[:, 3] < 2.0) & (cand[:, 4] < 2.0) & (cand[:, 4] > 1.6)
iA = np.where(okA)[0][np.argmax((cand[okA, 6] - cand[okA, 5]))]
okB = (cand[:, 4] > 2.0) & (cand[:, 3] < 2.0)
iB = np.where(okB)[0][np.argmax(cand[okB, 4] - cand[okB, 3])] if okB.any() else None
print("A", cand[iA], "B", None if iB is None else cand[iB], "n fail", int(okB.sum()), flush=True)
fig, ax = plt.subplots(3, 2, figsize=(6.85, 7.4))
for col, (idx, lab) in enumerate([(iA, "(a)"), (iB, "(b)")]):
    if idx is None: continue
    k, w = int(cand[idx, 0]), int(cand[idx, 1])
    W, F, sx, v, s15, v15 = store[k]
    t = np.arange(K) / 60.0
    # rerun for theta trace
    sxx, vv, th = run(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F, want_theta=True)
    u = W[2][w] / Ssc * 100
    a = ax[0, col]
    a.plot(t, u, color=GREY, lw=0.8, label="uncompensated")
    a.plot(t, v15[w], color=BLUE, lw=1.0, label=f"(9), $\\varepsilon_u$=1 %: rms {cand[idx,3]:.2f} %")
    a.plot(t, v[w], color=VERM, lw=1.0, label=f"window budget: rms {cand[idx,4]:.2f} %")
    a.plot(t, th[w], color=GREEN, lw=1.0, ls="--", label="threshold $\\theta_k$")
    a.axhline(2, color="k", lw=0.8, ls="-.")
    a.set_ylabel("VUF, 1-s values (%)"); a.set_xlabel("Time in 10-min window (min)")
    a.set_title(f"{lab} " + ("Window saved with less transfer" if col == 0 else "Late burst: budget fails, (9) holds") + f" (wk {k}, win. {w})", fontsize=7)
    a.set_ylim(0, 9.0); a.legend(loc="upper left", fontsize=5.8, framealpha=0.9)
    b = ax[1, col]
    b.plot(t, s15[w], color=BLUE, lw=1.0, label=f"(9): {cand[idx,6]*1000:.0f} kWh")
    b.plot(t, sx[w], color=VERM, lw=1.0, label=f"window budget: {cand[idx,5]*1000:.0f} kWh")
    b.axhline(KAPPA * C, color="k", lw=0.8, ls=":", label="$\\kappa C$")
    b.set_ylabel("Transfer $s_x$ per leg (MVA)"); b.set_xlabel("Time in 10-min window (min)"); b.set_ylim(0, 14.5); b.legend(loc="upper left", fontsize=6, framealpha=0.9)
# (e) stacked J bars
a = ax[2, 0]
M = json.load(open(os.path.join(HERE, "metrics.json")))["rows"]
names = [("percentile\n(6)", M["pct12"], GREY), ("proposed\n(9)", M["prop15"], BLUE),
         ("window budget\n(causal)", M["wb_causal"], VERM), ("causal,\n$\\theta_k\\leq$2 %", M["wb_cap2"], ORANGE),
         ("window budget\n(oracle)", M["wb_oracle"], PURPLE)]
x = np.arange(len(names)); bot = np.zeros(len(names))
for comp, hatch, lab in [("Jcap", None, "capital"), ("Jloss", "//", "losses"), ("Jviol", "xx", "exceedance")]:
    vals = np.array([n[1][comp] for n in names])
    a.bar(x, vals, bottom=bot, color=[n[2] for n in names], edgecolor="white", hatch=hatch, label=lab, width=0.7); bot += vals
for i, n in enumerate(names):
    a.text(i, bot[i] + 6, f"$C$={n[1]['C']:.1f}\n$J$={n[1]['J']:.0f}", ha="center", fontsize=5.8)
a.set_xticks(x); a.set_xticklabels([n[0] for n in names], fontsize=5.8); a.set_ylabel("Expected annual cost $J$ (kUSD/yr)"); a.set_ylim(0, 720)
h = [plt.Rectangle((0, 0), 1, 1, fc="w", ec="k", hatch=hh) for hh in (None, "//", "xx")]
a.legend(h, ["capital", "losses", "exceedance"], loc="upper right", fontsize=6.5, ncol=3); a.set_title("(c) Design at minimum $J$ (60 weeks)", fontsize=7)
# (f) frontier at fixed C0
s1 = json.load(open(os.path.join(HERE, "stage1.json")))["results"]
a = ax[2, 1]; Wk = RPC["weeks_per_year"]
e15 = [(s1[f"eq15_eps{e}"]["E_loss"] * Wk, s1[f"eq15_eps{e}"]["E_viol"] * Wk, e) for e in [0.0, 0.5, 1.0, 1.5, 2.0]]
a.plot([p[0] for p in e15], [p[1] for p in e15], "o-", color=BLUE, ms=4, label="(9), $\\varepsilon_u$ = 0 ... 2 %")
for p in e15: a.annotate(f"{p[2]:g}", (p[0], p[1]), textcoords="offset points", xytext=(4, 3), fontsize=6)
tb = [(v["E_loss"] * Wk, v["E_viol"] * Wk) for kx, v in s1.items() if kx.startswith("table_")]
a.plot(*zip(*tb), "s", color=VERM, ms=3, alpha=0.7, label="window budget (causal), $v^*$, $q$ grid")
ob = [(v["E_loss"] * Wk, v["E_viol"] * Wk) for kx, v in s1.items() if kx.startswith("oracle_")]
a.plot(*zip(*ob), "^", color=PURPLE, ms=4, label="oracle")
un = [(v["E_loss"] * Wk, v["E_viol"] * Wk) for kx, v in s1.items() if kx.startswith("uniform_")]
a.plot(*zip(*un), "d", color=ORANGE, ms=3, label="no forecast (uniform spend)")
a.set_xlabel("Losses $E_\\mathrm{loss}$ (MWh/yr)"); a.set_ylabel("Exceedance $E_\\mathrm{viol}$ (%$\\cdot$h/yr)")
a.set_title("(d) Trade-off at fixed $C$ = 10.44 MVA", fontsize=7); a.legend(fontsize=6, loc="upper right"); a.set_xlim(None, None)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_window_budget.pdf")); fig.savefig(os.path.join(HERE, "fig_window_budget.png"), dpi=130)
