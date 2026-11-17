"""Regenerates fig8_neutral.pdf (Fig. A5 of Online Resource 2, label f8) in Liberation Sans.
(a) t_ns = L_ns/v (Eq. 6); (b) C_dc,min = 2 P t_ns /(V0^2 (1-beta^2)) (Eq. 10), V0 = 3 kV, beta = 0.7."""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/',1)[0])
from common import *
setup(8.5)   # 160 mm = \textwidth of the manuscript; scales by 1.09 to 174 mm (Springer) -> 8-10 pt in both
out = sys.argv[1] if len(sys.argv)>1 else 'fig8_neutral.pdf'
lw = 1.5
fig, ax = plt.subplots(1, 2, figsize=(160*MM, 160*MM*3.4/8.6))
a = ax[0]
v = np.linspace(100, 350, 200)                 # km/h
for L, ls in [(30,'-'), (100,'--'), (200,'-.'), (400,':')]:
    a.plot(v, L/(v/3.6)*1000, ls, color='k', lw=lw+(0.2 if ls==':' else 0), label=rf'$L_\mathrm{{ns}}$ = {L} m')
a.set_xlabel('Train speed $v$ (km/h)'); a.set_ylabel(r'$t_\mathrm{ns}$ (ms)'); a.set_title('(a)')
a.set_yscale('log')
a.set_ylim(top=10**4.7)   # head-room (old limit: 1.75e4) so that the legend does not hide the 400 m curve
a.legend(loc='upper right', ncol=2, handlelength=2.2, columnspacing=1.0, borderpad=0.5)

b = ax[1]
P = np.linspace(0.05, 2.5, 200)                # MW
V0, beta = 3000.0, 0.7
for t, ls in [(0.1,'-'), (0.3,'--'), (1.0,'-.'), (3.0,':')]:
    C = 2*P*1e6*t/(V0**2*(1-beta**2))*1e3      # mF
    b.plot(P, C, ls, color='k', lw=lw+(0.2 if ls==':' else 0), label=rf'$t_\mathrm{{ns}}$ = {t} s')
for yb in (3, 30):
    b.axhline(yb, color=BLUE, lw=0.9, ls=(0, (4, 2)))
b.text(0.55, 9.0, 'typical $C_\\mathrm{dc}$ range\n3–30 mF', fontsize=8, color=BLUE, va='center')
b.set_yscale('log')
b.set_xlabel('DC-link power $P$ (MW)'); b.set_ylabel(r'$C_\mathrm{dc,min}$ (mF)'); b.set_title('(b)')
b.legend(loc='lower right', handlelength=2.2, borderpad=0.5)
fig.tight_layout(pad=0.4, w_pad=1.2)
fig.savefig(out)
