"""Generate (baseline, correlated-delay) weeks for a case from one library per week; store P,Q,S+,S-,counts.
usage: python s1_generate.py CASE N_WEEKS"""
import sys, json, time
import numpy as np
from lg import *
case = sys.argv[1]; NW = int(sys.argv[2])
t0 = time.time()
meta = []
for k in range(NW):
    fn = f"data/{case}_w{k:03d}.npz"
    base, corr, lib, p, tt = week_both(case, k)
    st = library_stats(lib, p)
    arr = {}
    for nm, w in (("b", base), ("c", corr)):
        for key, dt in (("P", np.float32), ("Q", np.float32), ("Sp", np.float32), ("Sn", np.float32), ("nz", np.int8), ("na", np.int8), ("nh", np.int8)):
            arr[f"{nm}_{key}"] = w[key].astype(dt)
    arr["libstat"] = st
    np.savez_compressed(fn, **arr)
    print(case, k, round(time.time() - t0), "s", flush=True)
