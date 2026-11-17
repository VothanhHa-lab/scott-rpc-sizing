"""Scan the 60 stored base weeks for dynamic events (read-only on /home/claude/code)."""
import sys, json
sys.path.insert(0, '/home/claude/code')
import numpy as np
from rpc_sizing.rpc import KAPPA
C, EPS, SSC = 11.270562480978487, 1.0, 750.0
res = dict(inc=(0, -1, 0), dec=(0, -1, 0))
best = {'inc_req': (-1, None, None), 'dec_req': (1, None, None), 'inc_del': (-1, None, None), 'dec_del': (1, None, None)}
rev = {}   # window -> (drop, wk, i)
WIN = [1, 3, 5, 10, 20]
revbest = {w: (0, None, None, None, None) for w in WIN}
for k in range(60):
    d = np.load(f'/home/claude/code/results/base_w{k:03d}.npz')
    P = d['P'].astype(float); Q = d['Q'].astype(float)
    S = np.hypot(P, Q)
    req = np.maximum(0, S - EPS / 100 * SSC) / 2
    dl = np.minimum(req, KAPPA * C)
    for name, x in (('req', req), ('del', dl)):
        df = np.diff(x)
        i = int(np.argmax(df)); j = int(np.argmin(df))
        if df[i] > best['inc_' + name][0]: best['inc_' + name] = (float(df[i]), k, i)
        if df[j] < best['dec_' + name][0]: best['dec_' + name] = (float(df[j]), k, j)
    for w in WIN:
        dP = P[w:] - P[:-w]
        ok = (P[:-w] > 0) & (P[w:] < 0)
        if ok.any():
            m = np.where(ok, dP, 0)
            i = int(np.argmin(m))
            if m[i] < revbest[w][0]:
                revbest[w] = (float(m[i]), k, i, float(P[i]), float(P[i + w]))
print(json.dumps(best, indent=1))
print(json.dumps({str(k): v for k, v in revbest.items()}, indent=1))
# global P stats
