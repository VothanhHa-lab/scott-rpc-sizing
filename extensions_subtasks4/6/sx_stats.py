"""Per-week filter-loss statistic F = sum_t sx(t)^2 / C / 3600 (MVA h per week) and sx_max for given (eps, C) candidates.
sx from law (15) (rpc.compensate, Ssc 750) -- identical for the approximate and the exact VUF evaluation.
Usage: sx_stats.py <set> ; sets: exact_stored, approx_stored, exact_refine, sub_stored (writes results/sx_<set>.json)"""
import sys, os, json, time
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/claude/code")
import numpy as np
from rpc_sizing import rpc

SET = sys.argv[1]
CODE = "/home/claude/code"
if SET == "exact_stored":
    cands = json.load(open(f"{CODE}/results_exact/stepA2.json"))["cands"]; store = f"{CODE}/results/base_w%03d.npz"; nw = 60; ssc = 750.0
elif SET == "approx_stored":
    cands = json.load(open(f"{CODE}/results/base.json"))["design"]["750"]["cands"]; store = f"{CODE}/results/base_w%03d.npz"; nw = 60; ssc = 750.0
elif SET == "exact_refine":
    d = json.load(open("/home/claude/subtasks3/4/exact_refine.json"))["new"]
    cands = [(x["eps"], x["C"]) for x in d]; store = f"{CODE}/results/base_w%03d.npz"; nw = 60; ssc = 750.0
elif SET == "sub_stored":
    cands = json.load(open(f"{CODE}/results_sub/suburban.json"))["design"]["750"]["cands"]; store = f"{CODE}/results_sub/suburban_w%03d.npz"; nw = 40; ssc = 750.0
elif SET.startswith("file:"):
    cands = json.load(open(SET[5:]))["cands"]; store = f"{CODE}/results/base_w%03d.npz"; nw = 60; ssc = 750.0
    SET = os.path.basename(SET[5:]).replace(".json", "")
out = {"cands": cands, "F": [[0.0] * nw for _ in cands], "sxmax": [[0.0] * nw for _ in cands]}
t0 = time.time()
for k in range(nw):
    d = np.load(store % k); P = d["P"].astype(float); Q = d["Q"].astype(float)
    for j, (e, C) in enumerate(cands):
        sx, _ = rpc.compensate(P, Q, C, e, ssc)
        out["F"][j][k] = float(np.sum(sx ** 2) / C / 3600.0)
        out["sxmax"][j][k] = float(sx.max())
    if k % 10 == 0:
        print(SET, "week", k, round(time.time() - t0), "s", flush=True)
json.dump(out, open(f"/home/claude/subtasks4/6/results/sx_{SET}.json", "w"))
print("done", SET, round(time.time() - t0), "s")
