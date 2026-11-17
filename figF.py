import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8, "mathtext.fontset": "custom",
    "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic", "pdf.fonttype": 42,
    "axes.grid": True, "grid.alpha": 0.3, "legend.fontsize": 7, "axes.titlesize": 8})
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7F7F7F"
from rpc_sizing import rpc
from rpc_sizing.network import solve
d = np.load('results/base_w000.npz'); P, Q = d['P'].astype(float), d['Q'].astype(float)
S = P + 1j*Q; m = np.abs(S) > 0.5
idx = np.where(m)[0][::40]
va = np.abs(S[idx]) / 750 * 100
ve, _ = solve(S[idx], np.zeros(len(idx)), 750)
r = json.load(open('results/netval_0_20.json'))
fig, ax = plt.subplots(1, 2, figsize=(6.85, 2.7))
ax[0].plot(va, ve, '.', ms=1.5, color=BLUE, alpha=0.6)
x = np.linspace(0, va.max(), 10); ax[0].plot(x, x, '-', color=VERM, lw=1.0, label='exact = (4)')
ax[0].set_xlabel('VUF from (4) (%)'); ax[0].set_ylabel('VUF, exact phasor model (%)'); ax[0].set_title('(a)'); ax[0].legend(loc='upper left')
k = np.arange(1, 21)
for n, mk, lab, col in [('p95', 'o', 'percentile sizing (6)', BLUE), ('prop', 's', 'proposed', VERM)]:
    ax[1].plot(k, [x[n]['p95_apx'] for x in r], mk, mfc='none', color=col, ms=4, label=lab + ', (4)')
    ax[1].plot(k, [x[n]['p95_ex'] for x in r], mk, color=col, ms=4, label=lab + ', exact')
ax[1].axhline(2, color='k', lw=0.8, ls='-.'); ax[1].set_ylim(1.3, 2.2)
ax[1].set_xlabel('Simulated week'); ax[1].set_ylabel('P95 of VUF$_{10\\,min}$ (%)'); ax[1].set_title('(b)')
ax[1].legend(loc='center right', fontsize=6.5)
fig.tight_layout(); fig.savefig('figs/figF_exact.pdf')
