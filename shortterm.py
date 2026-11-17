"""Short-term constraint: P99 of the 10-min VUF (in >=95 % of weeks)."""
import json, numpy as np
from rpc_sizing import rpc
from analyse import load
from rpc_sizing.params import RPC
s = load('base'); d = s['design']['750']; eg = s['eps_grid']; nf = len(s['c_fact'])
W = RPC['weeks_per_year']
# extend the C grid upward for the short-term constraint
cands = []
for i, e in enumerate(eg):
    for f in [1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0, 2.5, 3.0]:
        cands.append((e, d['c_design'][i] * f))
cands += [(2.0, c) for c in np.arange(11.0, 24.5, 0.5)]
res = np.zeros((60, len(cands), 4))   # p95, p99, E_loss, E_viol
for k in range(60):
    z = np.load(f'results/base_w{k:03d}.npz'); P, Q = z['P'].astype(float), z['Q'].astype(float)
    for j, (e, C) in enumerate(cands):
        sx, v = rpc.compensate(P, Q, C, e, 750.0)
        v10 = rpc.vuf10(v)
        res[k, j] = [rpc.p95(v10), float(np.quantile(v10, 0.99, method='inverted_cdf')),
                     rpc.losses_MWh(sx, C), float(np.maximum(0, v10 - 2).sum() / 6)]
    print(k, flush=True)
np.savez('results/shortterm.npz', res=res, cands=np.array(cands))
