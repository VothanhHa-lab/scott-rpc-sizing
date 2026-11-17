import sys, json
sys.path.insert(0, '/home/claude/subtasks3/1')
from run_dyn import *
from rpc_sizing import rpc as _rpc
byid = {c['id']: c for c in CASES}
out = {}
for H in (13.0, 15.0):
    for cid in ('a2', 'b3', 'b4'):
        o, P, Q = run(byid[cid], False, H_ms=H)
        m = metrics(o, byid[cid]['t0'])
        out[f'{cid}_H{H:g}'] = dict(Vmin=m['Vmin'], Vmax=m['Vmax'], Vmin_pct=m['Vmin_pct'], Vmax_pct=m['Vmax_pct'], Cdc_mF=m['Cdc_mF'], ok=m['band_ok'])
        print(cid, H, '%.0f..%.0f (%.2f..%.2f %%) Cdc %.1f ok=%s' % (m['Vmin'], m['Vmax'], m['Vmin_pct'], m['Vmax_pct'], m['Cdc_mF'], m['band_ok']), flush=True)
# agreement of dynamic model with quasi-static (15), existing segment (case b3, ff), excl. 1 s around the step
Z = np.load('dyn_traces.npz')
t = Z['b3_True__t']; Pa = Z['b3_True__Pa']; Qa = Z['b3_True__Qa']
d = np.load('/home/claude/code/results/base_w000.npz'); a0 = 462083
Pz = d['P'].astype(float)[a0:a0 + 61]; Qz = d['Q'].astype(float)[a0:a0 + 61]; Pz[40:] -= 10.0
sdyn = np.hypot(Pa, Qa)
ts = np.array([k + f for k in range(60) for f in (0.3, 0.6, 0.9) if not (38.9 < k + f < 40.2)])
idx = [int(np.argmin(np.abs(t - x))) for x in ts]
Pi = np.interp(t[idx], np.arange(61), Pz); Qi = np.interp(t[idx], np.arange(61), Qz)
sxi, _ = _rpc.compensate(Pi, Qi, C, EPS, SSC)
err = np.abs(sdyn[idx] - sxi)
out['agree_max'] = float(err.max()); out['agree_p95'] = float(np.quantile(err, 0.95))
print('agreement max %.3f MVA, p95 %.3f' % (err.max(), np.quantile(err, 0.95)))
json.dump(out, open('extra.json', 'w'), indent=1)
