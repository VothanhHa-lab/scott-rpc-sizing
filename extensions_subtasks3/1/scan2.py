import sys, json
sys.path.insert(0, '/home/claude/code')
import numpy as np
from rpc_sizing.rpc import KAPPA
C, EPS, SSC = 11.270562480978487, 1.0, 750.0
out = {}
cands = {}
for k in range(60):
    d = np.load(f'/home/claude/code/results/base_w{k:03d}.npz')
    P = d['P'].astype(float); Q = d['Q'].astype(float)
    S = np.hypot(P, Q)
    req = np.maximum(0, S - EPS / 100 * SSC) / 2
    sx = np.minimum(req, KAPPA * C)
    Pa = sx * P / np.maximum(S, 1e-9)
    for w in (1, 5):
        dP = Pa[w:] - Pa[:-w]
        for nm, i in (('Pa_inc', int(np.argmax(dP))), ('Pa_dec', int(np.argmin(dP)))):
            key = (nm, w)
            v = float(dP[i])
            if key not in cands or abs(v) > abs(cands[key][0]):
                cands[key] = (v, k, i)
        # reversal: Pa from >0 to <0 
        ok = (Pa[:-w] > 0.5) & (Pa[w:] < -0.5)
        if ok.any():
            m = np.where(ok, dP, 0); i = int(np.argmin(m))
            key = ('Pa_rev', w)
            if key not in cands or m[i] < cands[key][0]:
                cands[key] = (float(m[i]), k, i)
for k, v in cands.items(): print(k, v)
# print profiles of candidate reversal segments
def prof(k, i, pre=3, post=8):
    d = np.load(f'/home/claude/code/results/base_w{k:03d}.npz')
    P = d['P'].astype(float); Q = d['Q'].astype(float); S = np.hypot(P, Q)
    req = np.maximum(0, S - EPS / 100 * SSC) / 2; sx = np.minimum(req, KAPPA * C); Pa = sx * P / np.maximum(S, 1e-9)
    print('wk', k, 'i', i)
    for j in range(i - pre, i + post):
        print('  %d P %7.2f Q %6.2f S %6.2f req %6.2f Pa %6.2f' % (j - i, P[j], Q[j], S[j], req[j], Pa[j]))
for key in [('Pa_rev', 5)]:
    prof(cands[key][1], cands[key][2])
prof(33, 545385); prof(54, 500547, 3, 4); prof(15, 372158, 3, 4)
