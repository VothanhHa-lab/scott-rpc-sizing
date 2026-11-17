"""How often does the transfer |s_x| of the final design (C = 11.27 MVA, eps_u = 1 %, Ssc = 750 MVA) exceed the
level at which the 100 Hz ripple alone leaves the +/-10 % band (H_dc = 8 ms)?  Uses the stored 1 s load series of the
certification weeks (read-only access to /home/claude/code/results_exact), the same law (15) as the sizing code.
Usage: PYTHONDONTWRITEBYTECODE=1 nice -n 15 python3 duty_stats.py [outdir] [n_weeks]"""
import sys, json, glob, numpy as np
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/code')
from rpc_sizing import rpc
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
NW = int(sys.argv[2]) if len(sys.argv) > 2 else 10
C, EPS, SSC, H = 11.27, 1.0, 750.0, 8e-3
w = 2*np.pi*50
files = sorted(glob.glob('/home/claude/code/results_exact/cert_w*.npz'))[:NW]
sx_all = []
for fn in files:
    d = np.load(fn); sx, _ = rpc.compensate(d['P'], d['Q'], C, EPS, SSC); sx_all.append(sx)
sx = np.concatenate(sx_all); fr = sx/C
# ripple alone leaves +/-10 % when eps = (|s|/C)/(w H) > 0.19 (lower side: sqrt(1-eps) < 0.9)
thr10 = 0.19*w*H
out = dict(weeks=len(files), seconds=int(len(sx)), thr_frac_10pct=thr10,
           share_transfer_gt_0=float(np.mean(sx > 1e-6)), share_ge_thr10=float(np.mean(fr >= thr10)),
           share_ge_0p96=float(np.mean(fr >= 0.96 - 1e-9)), share_ge_0p5=float(np.mean(fr >= 0.5)),
           mean_frac=float(fr.mean()), p50_frac=float(np.quantile(fr, .5)), p95_frac=float(np.quantile(fr, .95)),
           max_frac=float(fr.max()))
print(json.dumps(out, indent=1))
json.dump(out, open(f'{OUT}/duty_stats.json', 'w'), indent=1)
