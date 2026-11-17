"""Validation part 2: load steps, EMT (cycle-averaged V_dc) vs averaged model dynamics.py."""
import sys, json, time
import numpy as np
import common as cm
import emt, post
from rpc_sizing import dynamics as dy
C = cm.C_STAR; EPS = 1.0; SSC = 750.0
DT = float(sys.argv[1]) if len(sys.argv) > 1 else 40e-6
TEV = 0.3
def seg(k, a):               # week-k segment, 3 s, knots a..a+3
    P, Q = cm.week(k); return P[a:a + 3].copy(), Q[a:a + 3].copy()
base = {}
a0 = 462083 + 38             # week-1 segment of the old check (step at 15.1 MW)
base['a2/b3 seg (week 1, 15.1 MW)'] = seg(0, a0)
base['const 15 MW'] = cm.const(15.0, 2)
base['const 25 MW'] = cm.const(25.0, 2)
cases = []; tags = []
for bname, (P, Q) in base.items():
    for stp in (+10.0, -10.0):
        for ff in (1, 0):
            if bname == 'const 15 MW' and stp < 0: continue
            if bname == 'const 25 MW' and stp > 0: continue
            cases.append(dict(P=P, Q=Q, dP_MW=stp, dQ_Mvar=stp * cm.TANPHI, t_ev=TEV, ramp=1e-3, ff=ff, H_ms=8.0,
                              meas_sogi=0.0, tau_ref=2e-3))      # 'averaged-model-equivalent' settings
            tags.append((bname, stp, ff, 'tau_i=2ms'))
            cases.append(dict(P=P, Q=Q, dP_MW=stp, dQ_Mvar=stp * cm.TANPHI, t_ev=TEV, ramp=1e-3, ff=ff, H_ms=8.0))   # production settings
            tags.append((bname, stp, ff, 'production'))
print(len(cases), 'cases', flush=True)
t0 = time.time()
o = emt.simulate(cases, T=0.6 + 1.5, dt=DT, log_every=4)
print('time', time.time() - t0, flush=True)
rows = []
for i, (bname, stp, ff, mode) in enumerate(tags):
    r, tr = post.analyse(o, i, cases[i])
    # averaged model
    c = cases[i]
    Pd = np.asarray(c['P']); Qd = np.asarray(c['Q'])
    ad = dy.simulate(Pd, Qd, C, EPS, SSC, t_step=TEV, step_MW=stp, ff=bool(ff), H_ms=8.0)
    Vd = ad['Vdc']; td = ad['t']
    m = td >= 0.0
    Vd_min, Vd_max = Vd.min(), Vd.max()
    # EMT cycle-averaged V_dc relative to the step window
    t = tr['t']; sel = t >= o['T_pre']
    Va = tr['Vavg'][sel]
    # compare time series: EMT Vavg(t - T_pre) vs dyn Vdc at same times (interp), over 0..1.5 s
    tt = t[sel] - o['T_pre']
    msk = (tt > 0.05) & (tt < 1.4)
    Vd_i = np.interp(tt[msk], td, Vd)
    rms = float(np.sqrt(np.mean((Va[msk] - Vd_i) ** 2)))
    rows.append(dict(base=bname, step_MW=stp, ff=ff, mode=mode, emt_Vavg_min=float(r['Vavg_min_V']), emt_Vavg_max=float(r['Vavg_max_V']),
                     emt_Vinst_min=r['Vmin_V'], emt_Vinst_max=r['Vmax_V'], dyn_min=float(Vd_min), dyn_max=float(Vd_max),
                     dyn_min_pct=100 * (Vd_min / 3500 - 1), dyn_max_pct=100 * (Vd_max / 3500 - 1),
                     rms_diff_V=rms, t_rec2_emt_ms=r.get('t_recover_2pct_ms'), I_emt=r['I_pu_max'], I_dyn=[float(ad['Ia'].max()), float(ad['Ib'].max())]))
    x = rows[-1]
    print(f"{bname:28s} {stp:+5.0f} MW ff={ff} {mode:9s} EMT avg {x['emt_Vavg_min']:.0f}..{x['emt_Vavg_max']:.0f} inst {x['emt_Vinst_min']:.0f}..{x['emt_Vinst_max']:.0f} | dyn {x['dyn_min']:.0f}..{x['dyn_max']:.0f} | rms diff {rms:.1f} V | I emt {r['I_pu_max'][0]:.3f}/{r['I_pu_max'][1]:.3f} dyn {x['I_dyn'][0]:.3f}/{x['I_dyn'][1]:.3f} | t2 {x['t_rec2_emt_ms']:.0f} ms", flush=True)
json.dump(rows, open('validation2.json', 'w'), indent=1, default=float)
