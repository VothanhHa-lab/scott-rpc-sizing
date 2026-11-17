"""HOOK for the exact suburban results of agent 5 (round 4, subtask 5).
Reads /home/claude/subtasks4/5/cache/ev_sub_wNNN.json (dict "eps_C" -> evaluation record with p95, E_viol, E_loss; the key format
f"{eps:.2f}_{C:.5f}" is that of t2b_designs.py), keeps the candidates present in ALL weeks, adds the filter statistic F from the suburban
weeks (law (15), Ssc 750) and writes results/exact_sub_records.json, which `compare.py subex` uses (percentile family eps 1.9).
Run after agent 5 has finished: nice -n 15 python3 sub_exact_hook.py && nice -n 15 python3 compare.py subex && python3 make_tables.py
If the evaluation records use other field names, adapt FIELDS."""
import sys, os, json, glob
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/claude/code")
import numpy as np
from rpc_sizing import rpc

CACHE = os.environ.get("HOOK_CACHE", "/home/claude/subtasks4/5/cache")
OUTF = os.environ.get("HOOK_OUT", "/home/claude/subtasks4/6/results/exact_sub_records.json")
FIELDS = dict(p95="p95", Ev="E_viol", El="E_loss")
files = sorted(glob.glob(f"{CACHE}/ev_sub_w*.json"))
if not files:
    raise SystemExit("no suburban exact caches yet")
weeks = [json.load(open(f)) for f in files]
keys = set(weeks[0])
for w in weeks[1:]:
    keys &= set(w)
print(len(files), "weeks,", len(keys), "common candidates")
recs = []
cands = sorted((tuple(float(x) for x in k.split("_")) for k in keys))
F = {c: [] for c in cands}
for i, f in enumerate(files):
    k = int(os.path.basename(f)[-8:-5])
    d = np.load(f"/home/claude/code/results_sub/suburban_w{k:03d}.npz"); P = d["P"].astype(float); Q = d["Q"].astype(float)
    for (e, C) in cands:
        sx, _ = rpc.compensate(P, Q, C, e, 750.0)
        F[(e, C)].append(float(np.sum(sx ** 2) / C / 3600.0))
for (e, C) in cands:
    key = f"{e:.2f}_{C:.5f}"
    p95 = np.array([w[key][FIELDS["p95"]] for w in weeks]); ev = [w[key][FIELDS["Ev"]] for w in weeks]; el = [w[key][FIELDS["El"]] for w in weeks]
    recs.append(dict(eps=e, C=C, n=len(weeks), comply=float(np.mean(p95 <= 2.0 + 1e-9)), Ev=float(np.mean(ev)), El=float(np.mean(el)), F=float(np.mean(F[(e, C)]))))
json.dump(dict(case="sub_exact", records=recs), open(OUTF, "w"))
print("written", len(recs))
