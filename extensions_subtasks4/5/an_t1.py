"""Summarise the monotonicity check (t1_monotone.py) and write table_mono.tex."""
import sys, json
SUF = sys.argv[1] if len(sys.argv) > 1 else ""
import numpy as np
from common5 import HERE, LIM

TOL = 1e-9
rows = []
summ = {}
for line in ("hs", "sub"):
    d = json.load(open(f"{HERE}/results_t1{SUF}_{line}.json"))
    for scen, key in (("none", "p95"), ("bg1", "p95_bg_worst")):
        for eps in d["eps"]:
            cs = [c for c in d["cases"] if c["eps"] == eps]
            n = len(cs); nmono = 0; nup = 0; rise = 0.0; nupc = 0; nfeas = 0; dev = []; worst_rise_case = None
            nonmono_cases = []
            gaps = []
            for c in cs:
                p = np.array(c[key]); C = np.array(c["C"])
                df = np.diff(p)
                up = df > TOL
                mono = not up.any()
                nmono += mono
                r = float(df.max()) if len(df) else 0.0
                if r > rise:
                    rise = r; worst_rise_case = dict(week=c["week"], C=float(C[int(df.argmax())]), rise=r)
                feas = p <= LIM + TOL
                nfeas += feas.any()
                # feasible set is an up-set on the grid?
                if feas.any():
                    i0 = int(np.argmax(feas))
                    upclosed = bool(feas[i0:].all())
                    nupc += upclosed
                    # smallest C such that all larger grid points are feasible
                    j = len(feas) - 1
                    while j >= 0 and feas[j]:
                        j -= 1
                    c_upc = float(C[j + 1]) if j + 1 < len(C) else float("nan")
                    c_first = float(C[i0])
                    step = float(C[1] - C[0])
                    if scen == "none":
                        dev.append(c["cmin_bisect"] - c_first)   # bisect value lies in (C_{i0-1}, C_{i0}]
                        gaps.append(step)
                if not mono:
                    nonmono_cases.append(dict(week=c["week"], rise=r))
            summ[f"{line}_{scen}_{eps}"] = dict(n=n, n_monotone=int(nmono), n_feasible=int(nfeas), n_upclosed=int(nupc),
                                              max_rise_pp=rise, worst=worst_rise_case,
                                              bisect_minus_gridfirst_range=[float(min(dev)), float(max(dev))] if dev else None,
                                              grid_step_MVA_range=[float(min(gaps)), float(max(gaps))] if gaps else None)
json.dump(summ, open(f"{HERE}/summary_t1{SUF}.json", "w"), indent=1)
for k, v in summ.items():
    print(k, v["n_monotone"], "/", v["n"], "monotone; feasible", v["n_feasible"], "upclosed", v["n_upclosed"], "max rise %.2e" % v["max_rise_pp"], v["bisect_minus_gridfirst_range"])
