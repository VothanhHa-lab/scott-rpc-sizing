import json, numpy as np
R = json.load(open('dyn_results.json'))['cases']
Z = np.load('dyn_traces.npz')
def dPa(cid):
    pa = Z[f'{cid}_True__Pa']; n = 500   # 2 ms samples -> 1 s
    # exclude the first 3 s (initialisation)
    pa = pa[1500:]
    return float(np.max(np.abs(pa[n:] - pa[:-n]))), float(pa.max() - pa.min())
def t98(cid, t0):
    t = Z[f'{cid}_True__t']; pa = Z[f'{cid}_True__Pa']
    i0 = np.argmin(np.abs(t - (t0 - 0.01))); i1 = np.argmin(np.abs(t - (t0 + 1.0)))
    d = pa[i1] - pa[i0]
    k = np.where(np.abs(pa[i0:i1 + 1] - pa[i1]) > 0.02 * abs(d))[0]
    return float(t[i0 + k[-1]] - t0) if len(k) else 0.0
rows = []
for cid in ['a1', 'a2', 'b1', 'b2', 'b3', 'b4', 'c1', 'c2']:
    r = R[cid]; d1, rng = dPa(cid)
    r['dPa_1s'] = d1
    if r['step'] is not None: r['t98_Pa_s'] = t98(cid, r['t0'])
    print(cid, 'dPa(1s) %.2f' % d1, 't98', r.get('t98_Pa_s'))
json.dump(R, open('dyn_results_full.json', 'w'), indent=1)
