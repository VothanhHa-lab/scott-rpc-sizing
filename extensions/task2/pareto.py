"""Pareto front of annualised cost (capital+loss) vs residual exceedance E_viol, base case Ssc=750.
Uses the stored per-candidate, per-week evaluations in results/base.json (no recomputation)."""
import sys, json
sys.path.insert(0, "/home/claude/code")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import analyse as A
from rpc_sizing.params import GRID

OUT = "/home/claude/subtasks/2"
SSC = 750
s = A.load("base", "/home/claude/code/results")
d = s["design"][str(SSC)]
ev, cands = d["evals"], d["cands"]
n = len(cands)
M = A.methods(s, SSC)

rows = []
for i in range(n):
    m = A.metrics(ev, i)
    J, cap, loss, viol = A.cost_terms(ev, i)
    rows.append(dict(i=i, C=m["C"], eps=m["eps"], comply=m["comply"], cost=cap + loss, cap=cap,
                     loss=loss, Eviol=m["Eviol"], J=J))
feas = [r for r in rows if r["comply"] >= 0.95 - 1e-9]
print("candidates", n, "feasible (>=95 % weeks)", len(feas))

# non-dominated set (minimise both)
def dominated(r, pool):
    return any((q["cost"] <= r["cost"] + 1e-12 and q["Eviol"] <= r["Eviol"] + 1e-12 and
                (q["cost"] < r["cost"] - 1e-12 or q["Eviol"] < r["Eviol"] - 1e-12)) for q in pool)
front = sorted([r for r in feas if not dominated(r, feas)], key=lambda r: r["cost"])
fidx = {r["i"] for r in front}
print("Pareto-optimal:", len(front))
for r in front:
    print(f"  i={r['i']:2d} C={r['C']:6.2f} eps={r['eps']:.2f} cost={r['cost']:7.1f} Eviol={r['Eviol']:7.2f}")

# supported points / w3 selection
def pick(w3):
    return min(feas, key=lambda r: r["cost"] + w3 * r["Eviol"])
w_grid = np.logspace(-1.5, 2.5, 4001)
sel = [pick(w)["i"] for w in w_grid]
intervals = []
start = 0
for k in range(1, len(w_grid) + 1):
    if k == len(w_grid) or sel[k] != sel[start]:
        intervals.append((sel[start], w_grid[start], w_grid[k - 1])); start = k
print("w3 intervals (index, lo, hi):")
for i, lo, hi in intervals:
    r = rows[i]; print(f"  i={i} C={r['C']:.2f} eps={r['eps']} w3 in [{lo:.2f},{hi:.2f}]")
W3 = [0.5, 1, 2, 5, 10]
sel_tab = []
for w in W3:
    r = pick(w)
    sel_tab.append(dict(w3=w, i=r["i"], C=r["C"], eps=r["eps"], cost=r["cost"], Eviol=r["Eviol"],
                        J=r["cost"] + w * r["Eviol"]))
    print(f"w3={w:>4}: C={r['C']:.2f} eps={r['eps']} cost={r['cost']:.1f} Eviol={r['Eviol']:.1f} J={sel_tab[-1]['J']:.1f}")
# exact range where the proposed design (idx) is selected
ip = M["proposed"]["idx"]
rng_prop = [(lo, hi) for i, lo, hi in intervals if i == ip]
print("proposed idx", ip, "selected for w3 in", rng_prop)
# regret of the proposed design when true w3 differs
for w in W3:
    r = pick(w); rp = rows[ip]
    print(f"w3={w}: J(proposed)={rp['cost']+w*rp['Eviol']:.1f} vs optimum {r['cost']+w*r['Eviol']:.1f} "
          f"(+{100*((rp['cost']+w*rp['Eviol'])/(r['cost']+w*r['Eviol'])-1):.1f} %)")

meth = {k: dict(idx=v["idx"], C=v["C"], eps=v["eps"], cost=rows[v["idx"]]["cost"],
                Eviol=rows[v["idx"]]["Eviol"], on_front=v["idx"] in fidx,
                dominated_by=[q["i"] for q in feas if dominated(rows[v["idx"]], [q])]) for k, v in M.items()}
for k, v in meth.items():
    print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items()})

json.dump(dict(candidates=rows, front=[r["i"] for r in front], methods=meth, w3_selection=sel_tab,
               w3_intervals=[dict(i=i, C=rows[i]["C"], eps=rows[i]["eps"], w3_lo=lo, w3_hi=hi) for i, lo, hi in intervals]),
          open(f"{OUT}/pareto.json", "w"), indent=1)

# ------------------------------------------------------------------ figure
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8,
                     "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans",
                     "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold",
                     "pdf.fonttype": 42, "lines.linewidth": 1.0, "axes.grid": True, "grid.alpha": 0.3,
                     "legend.fontsize": 7, "axes.titlesize": 8, "savefig.bbox": "tight"})
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY, YEL = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7F7F7F", "#F0E442"
fig, (a, b) = plt.subplots(1, 2, figsize=(6.85, 2.9), gridspec_kw=dict(width_ratios=[1.35, 1]))
# (a) cost-violation plane
dom = [r for r in feas if r["i"] not in fidx]
a.scatter([r["cost"] for r in dom], [r["Eviol"] for r in dom], s=9, color="#BBBBBB", zorder=2,
          label="dominated candidates")
a.plot([r["cost"] for r in front], [r["Eviol"] for r in front], "o-", color=BLUE, ms=3.5, lw=1.0, zorder=3,
       label="Pareto front")
sty = dict(full=("s", PURPLE, "full"), peak=("D", ORANGE, "peak (5)"), p95=("^", GREEN, "percentile (6)"),
           p95_Copt=("v", SKY, r"percentile, $C$ opt."), proposed=("*", VERM, "proposed"))
for k, (mk, col, lab) in sty.items():
    r = rows[meth[k]["idx"]]
    a.scatter([r["cost"]], [r["Eviol"]], marker=mk, s=70 if mk == "*" else 32, color=col, edgecolor="k",
              linewidth=0.5, zorder=5, label=lab)
a.set_yscale("symlog", linthresh=1.0, linscale=0.6)
a.set_ylim(-0.1, 300)
a.set_yticks([0, 1, 10, 100]); a.set_yticklabels(["0", "1", "10", "100"])
a.set_xlim(280, 1250)
a.set_xlabel(r"Capital + loss cost (kUSD/yr)")
a.set_ylabel(r"$\bar E_{\mathrm{viol}}$ (%$\cdot$h/yr)")
a.set_title("(a) Cost versus residual exceedance", loc="left")
a.legend(loc="upper right", frameon=True, framealpha=0.9, handletextpad=0.3, borderpad=0.3, labelspacing=0.25)
# (b) design selected as function of w3
wsel = np.logspace(-1, 2, 800)
Cs = np.array([pick(w)["C"] for w in wsel]); Es = np.array([pick(w)["eps"] for w in wsel])
b.step(wsel, Cs, where="post", color=BLUE, lw=1.4)
b.set_xscale("log"); b.set_xlim(0.1, 100)
b.set_xlabel(r"Penalty $w_3$ (kUSD/(%$\cdot$h))")
b.set_ylabel(r"Selected rating $C$ (MVA per leg)", color=BLUE)
b.tick_params(axis="y", colors=BLUE)
b.axvline(2.0, color=VERM, lw=0.8, ls="--")
b.text(1.9, 15.5, r"$w_3=2$ (base)", color=VERM, fontsize=7, rotation=90, va="top", ha="right")
b2 = b.twinx(); b2.grid(False)
b2.step(wsel, Es, where="post", color=ORANGE, lw=1.2, ls="-")
b2.set_ylabel(r"Selected threshold $\varepsilon_u$ (%)", color="#B07800")
b2.tick_params(axis="y", colors="#B07800"); b2.set_ylim(-0.1, 2.1)
for w in W3:
    b.plot([w], [pick(w)["C"]], "o", color=BLUE, ms=3.5, mec="k", mew=0.4, zorder=5)
b.set_title(r"(b) Design selected by (10) as $w_3$ varies", loc="left")
fig.tight_layout(w_pad=1.2)
fig.savefig(f"{OUT}/fig_pareto.pdf")
print("saved")
