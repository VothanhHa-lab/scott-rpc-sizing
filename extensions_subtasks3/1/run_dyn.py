"""Dynamic check of the RPC constraints for the final design (C*=11.27 MVA, eps_u*=1 %, Ssc=750 MVA).
Uses the unchanged averaged model /home/claude/code/rpc_sizing/dynamics.py (read-only import)."""
import sys, json, time
sys.path.insert(0, '/home/claude/code')
import numpy as np
from rpc_sizing import dynamics as dy
from rpc_sizing.params import RPC

C, EPS, SSC = 11.270562480978487, 1.0, 750.0
VREF = RPC['Vdc_ref']; VMIN, VMAX = RPC['Vdc_min'], RPC['Vdc_max']
NPRE, NLEN = 30, 61

def week(k):
    d = np.load(f'/home/claude/code/results/base_w{k:03d}.npz')
    return d['P'].astype(float), d['Q'].astype(float)

def window(k, i):
    P, Q = week(k); a = i - NPRE
    return P[a:a + NLEN].copy(), Q[a:a + NLEN].copy(), a

def synthetic(P0):
    pf = 0.998
    Q0 = P0 * np.tan(np.arccos(pf))
    return np.full(NLEN, P0), np.full(NLEN, Q0), None

# case: (label, kind, source, step MW at 40 s or None, t_onset)
CASES = [
 dict(id='a1', ev='a', label='largest increase of requested transfer (week 16, +5.17 MVA in 1 s)', src=('wk', 15, 372158), step=None, t0=30.0),
 dict(id='a2', ev='a', label='+10 MW step at t=40 s on the stored segment (week 1)', src=('wk', 0, 462113), step=+10.0, t0=40.0),
 dict(id='a3', ev='a', label='+10 MW step, constant 15 MW baseline (full 5.0 MVA change)', src=('syn', 15.0), step=+10.0, t0=40.0),
 dict(id='b1', ev='b', label='largest decrease of delivered transfer (week 55, -9.35 MVA in 1 s)', src=('wk', 54, 500547), step=None, t0=30.0),
 dict(id='b2', ev='b', label='largest decrease of requested transfer (week 16, -10.13 MVA in 1 s)', src=('wk', 15, 372761), step=None, t0=30.0),
 dict(id='b3', ev='b', label='-10 MW step at t=40 s on the stored segment (week 1; existing case)', src=('wk', 0, 462113), step=-10.0, t0=40.0),
 dict(id='b4', ev='b', label='-10 MW step, constant 25 MW baseline (full 5.0 MVA change)', src=('syn', 25.0), step=-10.0, t0=40.0),
 dict(id='c1', ev='c', label='power reversal, fastest fall of P over 5 s (week 12: 33.6 to -8.8 MW)', src=('wk', 11, 27645), step=None, t0=30.0),
 dict(id='c2', ev='c', label='power reversal, fastest 1-s fall of P through zero (week 34: 21.1 to -0.7 MW in 1 s)', src=('wk', 33, 545385), step=None, t0=30.0),
]

def run(case, ff, H_ms=8.0, keep=False):
    s = case['src']
    if s[0] == 'wk':
        P, Q, a = window(s[1], s[2])
    else:
        P, Q, a = synthetic(s[1])
    o = dy.simulate(P, Q, C, EPS, SSC, t_step=(40.0 if case['step'] is not None else None),
                    step_MW=(case['step'] or 0.0), ff=ff, H_ms=H_ms)
    return o, P, Q

def metrics(o, t0):
    t, v = o['t'], o['Vdc']
    out = dict(Vmin=float(v.min()), Vmax=float(v.max()),
               Vmin_pct=float(100 * (v.min() / VREF - 1)), Vmax_pct=float(100 * (v.max() / VREF - 1)),
               Ia=float(o['Ia'].max()), Ib=float(o['Ib'].max()),
               Pa_min=float(o['Pa'].min()), Pa_max=float(o['Pa'].max()),
               Cdc_mF=float(o['Cdc_mF']))
    # settling time of V_dc into a +-2 % (70 V) band, measured from the onset t0 of the load change
    for nm, tol in (('ts2', 0.02), ('ts1', 0.01)):
        bad = np.where((t >= t0) & (np.abs(v - VREF) > tol * VREF))[0]
        out[nm] = float(t[bad[-1]] - t0) if len(bad) else 0.0
    # time of the extremes
    out['t_Vmax'] = float(t[np.argmax(v)]); out['t_Vmin'] = float(t[np.argmin(v)])
    out['band_ok'] = bool(v.min() >= VMIN and v.max() <= VMAX)
    out['I_ok'] = bool(max(out['Ia'], out['Ib']) <= 1.0)
    return out

if __name__ == '__main__':
    t00 = time.time()
    res = {'design': dict(C=C, eps_u=EPS, Ssc=SSC, Vref=VREF, H_ms=8.0), 'cases': {}}
    traces = {}
    for c in CASES:
        r = {'label': c['label'], 'ev': c['ev'], 'step': c['step'], 't0': c['t0']}
        for ff in (True, False):
            o, P, Q = run(c, ff)
            r['ff' if ff else 'noff'] = metrics(o, c['t0'])
            traces[f"{c['id']}_{ff}"] = {k: o[k][::10] for k in ('t', 'Vdc', 'Pa', 'Qa', 'Pb', 'PL', 'QL', 'Ia', 'Ib')}
        r['load_Pmax'] = float(P.max()); r['load_Pmin'] = float(P.min())
        res['cases'][c['id']] = r
        print(c['id'], 'ff Vdc %.0f..%.0f Ia %.3f Ib %.3f | noff Vdc %.0f..%.0f (%.1f..%.1f %%) ts2 %.2f Ia %.3f Ib %.3f  [%.0fs]' % (
            r['ff']['Vmin'], r['ff']['Vmax'], r['ff']['Ia'], r['ff']['Ib'], r['noff']['Vmin'], r['noff']['Vmax'],
            r['noff']['Vmin_pct'], r['noff']['Vmax_pct'], r['noff']['ts2'], r['noff']['Ia'], r['noff']['Ib'], time.time() - t00), flush=True)
    json.dump(res, open('dyn_results.json', 'w'), indent=1)
    np.savez_compressed('dyn_traces.npz', **{f'{k}__{kk}': vv for k, d in traces.items() for kk, vv in d.items()})
