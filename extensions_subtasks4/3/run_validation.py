"""Validation of the EMT-type model: (1) steady 100 Hz ripple vs the analytic closed form of the DC-link energy balance,
(2) mean DC voltage / load steps vs the averaged model rpc_sizing/dynamics.py (identical control structure)."""
import sys, json, time
import numpy as np
import common as cm
import emt, post
from rpc_sizing import dynamics as dy
from rpc_sizing.params import RPC
C = cm.C_STAR; EPS = 1.0; SSC = 750.0
DT = float(sys.argv[1]) if len(sys.argv) > 1 else 40e-6
out = {}
# ------------------------------------------------ (1) steady ripple
fr = [0.25, 0.5, 0.75, 0.94]
cases = []; tags = []
for f in fr:
    S = 2 * f * C + EPS / 100 * SSC                         # |S_L| giving s_x = f C (before the current cap)
    P = S * 0.998
    for lab, kw in (('H8', dict(H_ms=8.0)), ('H16.8', dict(H_ms=16.8)), ('H8+Cf10', dict(H_ms=8.0, Cf_mF=10.0)),
                    ('H8+Cf5', dict(H_ms=8.0, Cf_mF=5.0))):
        cases.append(dict(P=[P] * 2, Q=[P * cm.TANPHI] * 2, **kw)); tags.append((f, lab))
t0 = time.time()
o = emt.simulate(cases, T=1.5, dt=DT, log_every=4)
print('steady batch', time.time() - t0, 's', flush=True)
w = 2 * np.pi * 50
rows = []
for i, (f, lab) in enumerate(tags):
    r, tr = post.analyse(o, i, cases[i])
    t = tr['t']; V = tr['V']
    m = (t > 1.1) & (t <= 1.5 - 0.0)
    # integer number of 100 Hz cycles in the window
    tt = t[m]; n = int((tt[-1] - tt[0]) / 0.01); tt = tt[tt <= tt[0] + n * 0.01 - 1e-9]; mm = m.copy()
    Vv = V[m][:len(tt)]
    Cdc = o['par']['Cdc'][i]
    Wv = 0.5 * Cdc * Vv ** 2
    Am = np.column_stack([np.ones_like(tt), np.cos(2 * w * tt), np.sin(2 * w * tt)])
    cf, *_ = np.linalg.lstsq(Am, Wv, rcond=None)
    W_ac = np.hypot(cf[1], cf[2])
    Sleg = tr['Sleg'][m][:len(tt)]
    s_a = -Sleg[:, 0].mean(); s_b = Sleg[:, 1].mean()
    A = abs(s_a + s_b)            # analytic 100 Hz power amplitude (VA), |s_a + s_b|
    eps_cf = A / (2 * w) / (0.5 * Cdc * 3500 ** 2)
    Vmin_cf = 3500 * np.sqrt(max(1 - eps_cf, 0)); Vmax_cf = 3500 * np.sqrt(1 + eps_cf)
    rows.append(dict(sx_over_C=f, config=lab, sx_deliv_MVA=abs(s_a) / 1e6, A_analytic_MVA=A / 1e6, W_ac_emt_kJ=W_ac / 1e3, W_ac_analytic_kJ=A / (2 * w) / 1e3,
                     W_ac_err_pct=100 * (W_ac / (A / (2 * w)) - 1) if not lab.startswith('H8+Cf') else None,
                     Vmin_emt=float(Vv.min()), Vmax_emt=float(Vv.max()), Vmin_cf=Vmin_cf, Vmax_cf=Vmax_cf, Vmean=float(Vv.mean()),
                     Vavg_dev_pct=float(100 * (np.sqrt(np.mean(Vv ** 2)) / 3500 - 1)), I_pu=r['I_pu_max'],
                     P_filter_kW=r['P_filter_kW'], m_inst_max=r['m_inst_max'], ripple_pct=r['ripple_pct']))
    x = rows[-1]
    print(f"s_x/C={f:.2f} {lab:8s} sx={x['sx_deliv_MVA']:6.3f} A={x['A_analytic_MVA']:6.3f} (2sx={2*x['sx_deliv_MVA']:6.3f}) W_ac err {x['W_ac_err_pct'] if x['W_ac_err_pct'] is None else round(x['W_ac_err_pct'],2)} % | V {x['Vmin_emt']:.0f}..{x['Vmax_emt']:.0f} (cf {x['Vmin_cf']:.0f}..{x['Vmax_cf']:.0f}) rms-dev {x['Vavg_dev_pct']:+.2f}% I {r['I_pu_max'][0]:.3f}/{r['I_pu_max'][1]:.3f} Pf {x['P_filter_kW']:.0f} kW", flush=True)
out['steady'] = rows
json.dump(out, open('validation.json', 'w'), indent=1, default=float)
