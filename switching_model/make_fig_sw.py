"""Figure of the switching-model check (white background, grid).  Runs the needed cases itself (about 20 s)."""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sw_rpc as M, sw_post as P, run_sw_cases as RC

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.linewidth': 0.6, 'grid.linewidth': 0.4,
                     'lines.linewidth': 0.8, 'legend.fontsize': 6.5, 'legend.frameon': False})
DES = dict(C=11.5, H_ms=26.2)
o_sw = RC.sim('S1_sustained', DES, dict(Nb=2, fc=1000.0, dt=1e-6))
o_avg = RC.sim('S1_sustained', DES, dict(avg_mode=True, dt=1e-6))
o_n1 = RC.sim('S1_sustained', DES, dict(Nb=1, fc=1000.0, dt=1e-6))
o_st = RC.sim('S4a_step+10_seg', DES, dict(Nb=2, fc=1000.0, dt=1e-6))
o_s6 = RC.sim('S6_step+20_pf90', DES, dict(Nb=2, fc=1000.0, dt=1e-6))
C = 11.5e6; Imax = math.sqrt(2) * C / M.VS0

fig, ax = plt.subplots(3, 2, figsize=(7.0, 6.6), gridspec_kw=dict(hspace=0.6, wspace=0.5))
for a in ax.flat:
    a.grid(True, color='0.85'); a.set_facecolor('white')

def band(a):
    for y in (3.15, 3.85):
        a.axhline(y, color='k', ls='--', lw=0.6)

# (a) V_dc, sustained transfer 0.94 C, 60 ms
t0 = 2.5
for o, c, lab in ((o_avg, '0.55', 'averaged switch'), (o_sw, 'C0', 'switching, 2 bridges/leg')):
    m = (o['t'] >= t0) & (o['t'] <= t0 + 0.06)
    ax[0, 0].plot((o['t'][m] - t0) * 1e3, o['V'][m] / 1e3, color=c, label=lab)
band(ax[0, 0]); ax[0, 0].set_ylim(3.1, 4.0)
ax[0, 0].set_xlabel('time (ms)'); ax[0, 0].set_ylabel('$v_\\mathrm{dc}$ (kV)')
ax[0, 0].set_title('(a) DC link, sustained transfer (S1)', loc='left'); ax[0, 0].legend(loc='upper center', ncol=2)
# (b) zoom 3 ms on the ripple near the minimum
m = (o_sw['t'] >= t0) & (o_sw['t'] <= t0 + 0.02)
tmin = o_sw['t'][m][np.argmin(o_sw['V'][m])]
for o, c, lab in ((o_avg, '0.55', 'averaged switch'), (o_n1, 'C3', '1 bridge/leg'), (o_sw, 'C0', '2 bridges/leg')):
    m = (o['t'] >= tmin - 1.5e-3) & (o['t'] <= tmin + 1.5e-3)
    ax[0, 1].plot((o['t'][m] - tmin) * 1e3, o['V'][m], color=c, label=lab)
ax[0, 1].set_xlabel('time around the minimum (ms)'); ax[0, 1].set_ylabel('$v_\\mathrm{dc}$ (V)')
ax[0, 1].set_title('(b) switching ripple on $v_\\mathrm{dc}$', loc='left'); ax[0, 1].legend(loc='upper center', ncol=3)
# (c) bridge currents of the beta leg, 2 bridges, one cycle
for o, ttl, a in ((o_sw, '(c) $\\beta$-leg bridge currents, 2 bridges/leg', ax[1, 0]), (o_n1, '(d) $\\beta$-leg current, 1 bridge/leg', ax[1, 1])):
    Nb = o['par']['Nb']
    m = (o['t'] >= t0) & (o['t'] <= t0 + 0.02)
    for j in range(Nb):
        a.plot((o['t'][m] - t0) * 1e3, o['I'][m, 1, j] / (Imax / Nb), color=('C0', 'C1')[j], lw=0.5, label=f'bridge {j + 1}')
    mm = (o_avg['t'] >= t0) & (o_avg['t'] <= t0 + 0.02)
    a.plot((o_avg['t'][mm] - t0) * 1e3, o_avg['I'][mm, 1, :].sum(axis=1) / Imax, color='k', lw=0.8, label='averaged switch')
    for y in (1, -1):
        a.axhline(y, color='k', ls='--', lw=0.6)
    a.set_ylim(-1.45, 1.45); a.set_xlabel('time (ms)'); a.set_ylabel('$i$ / rated peak of the bridge')
    a.set_title(ttl, loc='left'); a.legend(loc='upper left', ncol=3)
# (e) +10 MW step and (f) +20 MW stress step: V_dc envelope (max/min per 1 ms)
for o, ttl, a, tev in ((o_st, '(e) +10 MW step (S4a)', ax[2, 0], 0.5), (o_s6, '(f) +20 MW step, pf 0.90 (S6, stress)', ax[2, 1], 0.5)):
    T0 = 0.6 + tev
    m = (o['t'] >= T0 - 0.05) & (o['t'] <= T0 + 0.25)
    mp = (o['t'] >= T0 - 0.08) & (o['t'] <= T0 + 0.28)
    tt = o['t'][m]; vv = o['V'][m] / 1e3
    n = int(round(10e-3 / (tt[1] - tt[0]))); k = len(tt) // n
    te = tt[:k * n].reshape(k, n).mean(1); vmx = vv[:k * n].reshape(k, n).max(1); vmn = vv[:k * n].reshape(k, n).min(1)
    a.plot((te - T0) * 1e3, vmx, color='C0', label='$v_\\mathrm{dc}$ max/min per 10 ms'); a.plot((te - T0) * 1e3, vmn, color='C0')
    band(a); a.set_ylim(2.85, 3.9)
    a2 = a.twinx()
    Il = P.phasor(o['I'][mp].sum(axis=2).astype(float), o['t'][mp], int(round(0.02 / (tt[1] - tt[0]))))
    Il = Il[np.isin(o['t'][mp], tt)]
    a2.plot((tt - T0) * 1e3, np.abs(Il[:, 0]) / Imax, color='C2', label='$|I_{\\alpha,1}|$')
    a2.plot((tt - T0) * 1e3, np.abs(Il[:, 1]) / Imax, color='C1', label='$|I_{\\beta,1}|$')
    a2.axhline(1.0, color='C2', ls=':', lw=0.6); a2.set_ylim(0, 1.3); a2.set_ylabel('fundamental / rated')
    a.set_xlabel('time after step (ms)'); a.set_ylabel('$v_\\mathrm{dc}$ (kV)'); a.set_title(ttl, loc='left')
    h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    a.legend(h1 + h2, l1 + l2, loc='lower center', ncol=2)
fig.savefig('fig_switching_check.pdf', bbox_inches='tight'); fig.savefig('fig_switching_check.png', dpi=200, bbox_inches='tight')
print('saved')
