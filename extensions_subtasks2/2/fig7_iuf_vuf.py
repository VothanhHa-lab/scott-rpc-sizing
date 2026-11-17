"""Regenerates fig7_iuf_vuf.pdf (Fig. 7 of the manuscript, label f7) in Liberation Sans.
Curves: Eq. (7) IUF=|1-k e^{j dphi}|/|1+k e^{j dphi}| and Eq. (8) VUF ~ |S_alpha-S_beta|/S_sc (k=0 case).
Simulation markers: digitised from the vector PDF of the previous version (see NOTES.md); the
values at k=0.5 (32.87 %) and k=1, dphi=20 deg (17.28 %) agree with Table t5."""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/',1)[0])
from common import *
setup(8.5)   # 160 mm = \textwidth of the manuscript; scales by 1.09 to 174 mm (Springer) -> 8-10 pt in both
out = sys.argv[1] if len(sys.argv)>1 else 'fig7_iuf_vuf.pdf'

# --- simulation markers (digitised from previous fig7_iuf_vuf.pdf; k = 0, 1/8, ..., 1) ---
k_sim = np.arange(9)/8
iuf_sim_0  = np.array([100.00, 77.42, 59.50, 44.94, 32.87, 22.71, 14.03, 6.54, 0.00])      # dphi = 0 deg
iuf_sim_20 = np.array([100.00, 78.81, 61.86, 48.21, 37.24, 28.64, 22.34, 18.52, 17.28])    # dphi = 20 deg
dS_sim = 8.42                                  # MVA, S_alpha - S_beta of the simulated cases (k = 0, Table t5: 1.684 % x 500 MVA)
vuf_sim = {1000: 0.826, 2000: 0.414, 4000: 0.207}   # %, digitised

def iuf(k, d):
    z = k*np.exp(1j*np.radians(d))
    return 100*np.abs(1-z)/np.abs(1+z)

fig, ax = plt.subplots(1, 2, figsize=(160*MM, 160*MM*3.4/8.6))
a = ax[0]
k = np.linspace(0, 1, 201)
lw = 1.4
msz, mew = 4.6, 1.2
mk = dict(mfc='white', mec=VERM, mew=mew, ms=msz, ls='none', zorder=5)
a.plot(k, iuf(k, 0), '-', color='k', lw=lw, label=r'$\mathrm{\Delta}\varphi$ = 0°')
a.plot(k_sim, iuf_sim_0, 'o', label=r'Simulation, $\mathrm{\Delta}\varphi$ = 0°', **mk)
a.plot(k, iuf(k, 10), '--', color='k', lw=lw, label=r'$\mathrm{\Delta}\varphi$ = 10°')
a.plot(k, iuf(k, 20), '-.', color='k', lw=lw, label=r'$\mathrm{\Delta}\varphi$ = 20°')
a.plot(k_sim, iuf_sim_20, 's', label=r'Simulation, $\mathrm{\Delta}\varphi$ = 20°', **mk)
a.plot(k, iuf(k, 30), ':', color='k', lw=lw+0.2, label=r'$\mathrm{\Delta}\varphi$ = 30°')
a.set_xlabel(r'Load ratio $k = S_\beta/S_\alpha$'); a.set_ylabel('IUF (%)')
a.set_title('(a)'); a.set_ylim(0, 102)
a.legend(loc='upper right', fontsize=8, handlelength=2.0, borderpad=0.4, labelspacing=0.22, handletextpad=0.6)

b = ax[1]
SL = np.linspace(0, 60, 121)
styles = {1000:'-', 2000:'--', 4000:'-.', 8000:':'}
for ssc, ls in styles.items():
    b.plot(SL, 100*SL/ssc, ls, color='k', lw=lw+(0.2 if ls==':' else 0), label=rf'$S_\mathrm{{sc}}$ = {ssc} MVA')
b.axhline(2, color=VERM, lw=1.2)
b.text(1, 2.15, '2 % limit', color=VERM, fontsize=8)
b.plot([dS_sim]*3, list(vuf_sim.values()), 'o', label='Simulation', **mk)
b.set_xlabel(r'$|S_\alpha - S_\beta|$ (MVA)'); b.set_ylabel('VUF (%)')
b.set_title('(b)'); b.set_ylim(0, 6)
b.legend(loc='upper left', handlelength=2.2, borderpad=0.5, labelspacing=0.35)
fig.tight_layout(pad=0.4, w_pad=1.2)
fig.savefig(out)
