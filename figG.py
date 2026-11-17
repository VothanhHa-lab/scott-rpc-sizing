import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import stats
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8, "mathtext.fontset": "custom",
    "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic", "pdf.fonttype": 42,
    "axes.grid": True, "grid.alpha": 0.3, "legend.fontsize": 7, "axes.titlesize": 8})
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7F7F7F"
from analyse import load, methods
from rpc_sizing.experiment import CASES
from rpc_sizing.params import TRAIN, SEED0, RPC
from rpc_sizing import train as tr
p = dict(TRAIN); p.update(CASES['suburban']['train'])
e, g = tr.grade_profile(np.random.default_rng(SEED0), p['zone_length_m'])
P1, L1 = tr.run_train(p, np.random.default_rng(3), e, g, stop=True, details=True)
fig, ax = plt.subplots(1, 3, figsize=(6.85, 2.4))
t = np.arange(len(P1))/60
ax[0].plot(t, L1[:,1]*3.6, color=BLUE, lw=1, label='speed'); ax[0].set_ylabel('Speed (km/h)'); ax[0].set_xlabel('Time (min)')
a2 = ax[0].twinx(); a2.grid(False); a2.plot(t, P1, color=VERM, lw=0.8); a2.set_ylabel('$P_\\mathrm{el}$ (MW)', color=VERM)
ax[0].set_title('(a)'); ax[0].set_xlim(0, 12)
d = np.load('results_sub/suburban_w000.npz'); P = d['P'].astype(float); Q = d['Q'].astype(float)
i0, i1 = (24+7)*3600, (24+9)*3600
ax[1].plot((np.arange(i0,i1)-24*3600)/3600, P[i0:i1], color=BLUE, lw=0.5)
ax[1].set_xlabel('Time of day (h)'); ax[1].set_ylabel('$P_L$ (MW)'); ax[1].set_title('(b)')
s = load('suburban', 'results_sub'); ss = [750, 1000, 1500]
for k, st, lab, col in [('full',':','full',PURPLE), ('peak','-.','peak (5)',ORANGE), ('p95','--','P95 (6)',BLUE), ('proposed','-','proposed',VERM)]:
    ax[2].plot(ss, [methods(s, S)[k]['C'] for S in ss], st, color=col, marker='o', ms=3, lw=1.3, label=lab)
ax[2].set_xlabel('$S_\\mathrm{sc}$ (MVA)'); ax[2].set_ylabel('Rating per leg (MVA)'); ax[2].legend(fontsize=6.5); ax[2].set_title('(c)')
fig.tight_layout(); fig.savefig('figs/figG_suburban.pdf')
# paired test at 300 MVA
d3 = s['design']['750']; ev = d3['evals']; W = RPC['weeks_per_year']; m = methods(s, 750)
def Jw(i):
    C = d3['cands'][i][1]; cap = RPC['cost_kUSD_per_MVA']*2*C*RPC['crf']
    return np.array([cap + RPC['energy_price_USD_MWh']*w[i]['E_loss']*W/1000 + RPC['viol_price_kUSD_per_pct_h']*w[i]['E_viol']*W for w in ev])
diff = Jw(m['proposed']['idx']) - Jw(m['p95']['idx'])
h = stats.t.ppf(.975, len(diff)-1)*diff.std(ddof=1)/np.sqrt(len(diff))
print('paired %.1f ± %.1f, share cheaper %.2f, p=%.1e' % (diff.mean(), h, np.mean(diff<0), stats.wilcoxon(diff).pvalue))
print('train run: max P %.2f min P %.2f, duration %.1f min' % (P1.max(), P1.min(), len(P1)/60))
