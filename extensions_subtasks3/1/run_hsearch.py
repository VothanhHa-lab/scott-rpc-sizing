import sys, json, time
sys.path.insert(0, '/home/claude/subtasks3/1')
from run_dyn import *
t00 = time.time()
byid = {c['id']: c for c in CASES}
GRID_H = [8, 12, 16, 20, 25, 30, 40, 50, 60]
out = {'grid': GRID_H, 'cases': {}}
def band(c, H):
    o, P, Q = run(byid[c], False, H_ms=H)
    m = metrics(o, byid[c]['t0'])
    return m
for cid in ('a2', 'b3', 'b4'):
    r = {'grid': {}}
    for H in GRID_H:
        m = band(cid, H)
        r['grid'][str(H)] = dict(Vmin=m['Vmin'], Vmax=m['Vmax'], Vmin_pct=m['Vmin_pct'], Vmax_pct=m['Vmax_pct'], ok=m['band_ok'], Cdc_mF=m['Cdc_mF'], Ia=m['Ia'], Ib=m['Ib'])
        print(cid, H, '%.0f..%.0f (%.2f..%.2f %%) ok=%s [%.0fs]' % (m['Vmin'], m['Vmax'], m['Vmin_pct'], m['Vmax_pct'], m['band_ok'], time.time() - t00), flush=True)
    # bisection between last failing and first passing grid value
    fails = [H for H in GRID_H if not r['grid'][str(H)]['ok']]
    passes = [H for H in GRID_H if r['grid'][str(H)]['ok']]
    if not fails:
        r['Hmin'] = 8.0
    elif not passes:
        r['Hmin'] = None
    else:
        lo, hi = max(fails), min(passes)
        while hi - lo > 0.25:
            mid = 0.5 * (lo + hi)
            if band(cid, mid)['band_ok']: hi = mid
            else: lo = mid
        r['Hmin'] = hi
        m = band(cid, hi)
        r['at_Hmin'] = dict(Vmin=m['Vmin'], Vmax=m['Vmax'], Vmin_pct=m['Vmin_pct'], Vmax_pct=m['Vmax_pct'], Cdc_mF=m['Cdc_mF'])
    print(cid, 'Hmin', r['Hmin'], flush=True)
    out['cases'][cid] = r
json.dump(out, open('hsearch.json', 'w'), indent=1)
