import numpy as np, json
from rpc_sizing.params import RPC
z = np.load('results/shortterm.npz'); res, cands = z['res'], z['cands']; W = RPC['weeks_per_year']
cap = lambda C: RPC['cost_kUSD_per_MVA']*2*C*RPC['crf']
J = np.array([cap(c[1]) for c in cands]) + RPC['energy_price_USD_MWh']*res[:,:,2].mean(0)*W/1000 + RPC['viol_price_kUSD_per_pct_h']*res[:,:,3].mean(0)*W
ok95 = np.mean(res[:,:,0] <= 2.0 + 1e-9, axis=0) >= 0.95
out = {}
for cap99 in [None, 2.5, 2.25, 2.1, 2.0]:
    ok = ok95.copy()
    if cap99: ok &= np.mean(res[:,:,1] <= cap99 + 1e-9, axis=0) >= 0.95
    i = np.where(ok)[0]; ib = i[np.argmin(J[i])]
    # best conventional (eps=2) under same constraints
    ic = [j for j in i if abs(cands[j][0]-2.0) < 1e-9]; jc = ic[np.argmin([cands[j][1] for j in ic])] if ic else None
    r = dict(eps=float(cands[ib][0]), C=float(cands[ib][1]), J=float(J[ib]), p99=float(res[:,ib,1].mean()),
             conv_C=float(cands[jc][1]) if jc is not None else None, conv_J=float(J[jc]) if jc is not None else None,
             conv_p99=float(res[:,jc,1].mean()) if jc is not None else None)
    out[str(cap99)] = r; print(cap99, {k: (round(v,3) if v is not None else None) for k,v in r.items()})
json.dump(out, open('results/shortterm_summary.json','w'), indent=1)
