"""Figures from the EMT runs (colour, Liberation Sans).  Reads tr_main*.npz / res_main*.json.
  figEMT_events.pdf : replacement candidate for Fig. 10 (steps and reversal)
  figEMT_ripple.pdf : ripple / modulation / filter comparison (sustained transfer)"""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
plt.rcParams.update({'font.family': 'Liberation Sans', 'font.size': 7.5, 'axes.linewidth': 0.6, 'pdf.fonttype': 42,
                     'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False, 'lines.linewidth': 0.9})
COL = {'ref8': '#8a8a8a', 'A': '#0072B2', 'A26': '#7B5EA7', 'B10': '#D55E00', 'B5': '#009E73', 'A_noFF': '#56B4E9', 'B10_noFF': '#E69F00'}
LAB = {'A26': 'A: H$_{dc}$=26.2 ms', 'ref8': 'H$_{dc}$=8 ms, no filter', 'A': 'A: H$_{dc}$=18 ms', 'B10': 'B: 8 ms + C$_f$=10 mF', 'B5': 'B: 8 ms + C$_f$=5 mF',
       'A_noFF': 'A, no FF', 'B10_noFF': 'B (10 mF), no FF'}
PRE = 0.6
tr = {}
for tag in ('main1', 'main2', 'main3', 'main4'):
    try:
        tr[tag] = np.load(f'tr_{tag}.npz')
    except Exception:
        pass
def get(name, key):
    for d in tr.values():
        if f'{name}__{key}' in d.files:
            return d[f'{name}__{key}'], d['t']
    raise KeyError(name)

# ---------------------------------------------------------------- events figure
cols = [('S4a_step+10_seg', '(a) +10 MW load step', (-0.05, 0.30), 0.5), ('S4b_step-10_seg', '(b) $-$10 MW load step (trip)', (-0.05, 0.30), 0.5),
        ('S3b_rev5s', '(c) traction to regeneration', (0.0, 4.0), None)]
fig, ax = plt.subplots(4, 3, figsize=(7.0, 7.6), gridspec_kw=dict(hspace=0.42, wspace=0.32))
for j, (sc, title, (a, b), tev) in enumerate(cols):
    off = PRE + (tev if tev is not None else 0.0)
    ms = tev is not None
    def X(t):
        return (t - off) * (1e3 if ms else 1.0)
    # row 0: load and transfer
    PL, t = get(f'{sc}|A26', 'PL'); sxa, _ = get(f'{sc}|A26', 'sx_a'); sxl, _ = get(f'{sc}|A26', 'sx_law')
    m = (t >= off + a) & (t <= off + b)
    ax[0, j].plot(X(t[m]), PL[m] / 1e6, color='k', label='load $P_L$')
    ax[0, j].plot(X(t[m]), sxa[m] / 1e6, color=COL['A26'], label='$|s_x|$ delivered ($\\alpha$ leg)')
    ax[0, j].plot(X(t[m]), sxl[m] / 1e6, color='#999999', ls='--', label='law (9)')
    ax[0, j].set_title(title, fontsize=8)
    ax[0, j].set_ylabel('MW / MVA')
    # row 1: instantaneous V_dc
    for cn in ('ref8', 'A26'):
        V, t = get(f'{sc}|{cn}', 'V')
        m = (t >= off + a) & (t <= off + b - (0.05 if not ms else 0.0))
        ax[1, j].plot(X(t[m]), V[m] / 1e3, color=COL[cn], lw=0.6 if cn == 'ref8' else 0.9, label=LAB[cn], zorder=2 if cn != 'ref8' else 1)
    Vr, t = get(f'{sc}|A26', 'Vreq'); m = (t >= off + a) & (t <= off + b)
    ax[1, j].plot(X(t[m]), Vr[m].max(axis=1) / 1e3, color='k', ls=':', label='$V_{dc}$ required for $m\\leq 0.95$')
    for lv in (3.15, 3.85):
        ax[1, j].axhline(lv, color='k', ls='--', lw=0.6)
    ax[1, j].set_ylim(2.6, 4.25); ax[1, j].set_ylabel('$v_{dc}$ (kV), instantaneous')
    # row 2: cycle-average deviation
    for cn in ('A26',):
        try:
            Va, t = get(f'{sc}|{cn}', 'Vavg')
        except KeyError:
            continue
        m = (t >= off + a) & (t <= off + b)
        ax[2, j].plot(X(t[m]), 100 * (Va[m] / 3500 - 1), color=COL[cn], ls='--' if 'noFF' in cn else '-', label=LAB[cn])
    ax[2, j].set_ylabel('20-ms mean $v_{dc}$ dev. (%)')
    if not ms: ax[2, j].set_ylim(-0.1, 0.1); ax[2, j].set_xlim(0, 3.9); ax[2, j].axhline(0, color='k', lw=0.4)
    # row 3: currents
    I, t = get(f'{sc}|A26', 'Ipu'); m = (t >= off + a) & (t <= off + b)
    ax[3, j].plot(X(t[m]), I[m, 0], color='#0072B2', label='$\\alpha$ leg')
    ax[3, j].plot(X(t[m]), I[m, 1], color='#CC79A7', ls='--', label='$\\beta$ leg')
    ax[3, j].axhline(1.0, color='k', ls='--', lw=0.6); ax[3, j].set_ylim(0, 1.15)
    ax[3, j].set_ylabel('leg current (pu, rms)')
    ax[3, j].set_xlabel('time from step (ms)' if ms else 'time (s)')
for r in range(4):
    for j in range(3):
        ax[r, j].tick_params(width=0.5, length=2.5)
ax[0, 0].legend(fontsize=6, loc='center right')
ax[3, 0].legend(fontsize=6, loc='upper left')
h1, l1 = ax[1, 0].get_legend_handles_labels(); h2, l2 = ax[2, 0].get_legend_handles_labels()
hh = h1 + h2; ll = l1 + [l+' (20-ms mean, with FF)' for l in l2]
# unique legend below the figure (two rows)
fig.legend(hh, ll, loc='lower center', ncol=2, fontsize=6.3, bbox_to_anchor=(0.5, 0.005), columnspacing=1.2, handlelength=1.8)
fig.savefig('/home/claude/urt_v8/figEMT_A26.pdf', bbox_inches='tight'); fig.savefig('/tmp/figEMT_A26.png', dpi=110, bbox_inches='tight')
