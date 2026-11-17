"""Pick EMT operating windows from the 60 stored base weeks (law (15), C=11.27 MVA, eps_u=1 %, Ssc=750)."""
import json, numpy as np
import common as cm
from rpc_sizing import rpc as R
from rpc_sizing.params import RPC
C, EPS, SSC = cm.C_STAR, 1.0, 750.0
best_plateau = []      # (min over 4 s of sx/C, week, start)
lowU = []              # lowest alpha-busbar voltage
big = []
W = 4
res = {}
for k in range(60):
    P, Q = cm.week(k)
    S = np.hypot(P, Q)
    sx, vuf = R.compensate(P, Q, C, EPS, SSC)
    req = np.maximum(0, S - EPS / 100 * SSC) / 2
    frac = np.where(S > 0, np.minimum(req, C) / np.maximum(S, 1e-9), 0.0)
    U = R.busbar_voltage(P * (1 - frac), Q * (1 - frac), SSC)
    # sliding-minimum of sx/C over W s windows
    x = sx / C
    from scipy.ndimage import minimum_filter1d
    mf = minimum_filter1d(x, W)
    j = int(np.argmax(mf)); best_plateau.append((float(mf[j]), k, j - W // 2 if False else j - (W - 1) // 2 * 0))
    # sustained (mean over 10 s)
    cs = np.cumsum(np.insert(x, 0, 0)); m10 = (cs[10:] - cs[:-10]) / 10
    jm = int(np.argmax(m10)); res.setdefault('mean10', []).append((float(m10[jm]), k, jm))
    jU = int(np.argmin(U)); lowU.append((float(U[jU]), k, jU, float(S[jU]), float(sx[jU]), float(P[jU]), float(Q[jU])))
    jS = int(np.argmax(S)); big.append((float(S[jS]), k, jS, float(U[jS]), float(sx[jS])))
best_plateau.sort(reverse=True); lowU.sort(); big.sort(reverse=True)
res['plateau4s_top'] = best_plateau[:6]
res['mean10_top'] = sorted(res['mean10'], reverse=True)[:6]; del res['mean10']
res['lowU_top'] = lowU[:6]
res['maxS_top'] = big[:6]
print(json.dumps(res, indent=1))
json.dump(res, open('scan_points.json', 'w'), indent=1)
