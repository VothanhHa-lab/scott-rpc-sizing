import sys, os, json
sys.path.insert(0, "/home/claude/code"); sys.path.insert(0, "/home/claude/subtasks/7")
import numpy as np
from window_budget import *
from analyse import load as load_json, methods
Ssc = 750.0
HERE = "/home/claude/subtasks/7"
CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)
FOLDS = {"A": (list(range(0, 30)), list(range(30, 60))),    # (evaluate, calibrate)
         "B": (list(range(30, 60)), list(range(0, 30)))}
QS = [0.8, 0.9, 0.95, 0.98, 0.99]
CGRID = np.arange(6.0, 14.01, 1.0)
BASE = load_json("base", "/home/claude/code/results")
CMIN0 = np.array([w["cmin"]["750"][0] for w in BASE["weeks"]])     # greedy (eps=0) C_min per week
CMIN = {e: np.array([w["cmin"]["750"][i] for w in BASE["weeks"]]) for i, e in enumerate(BASE["eps_grid"])}

def fold_tables(name, offset=0, cgrid=CGRID):
    ev, cal = FOLDS[name]
    Pc, Qc = zip(*[load_week(k) for k in cal])
    return Tables(Pc, Qc, Ssc, QS, cgrid, offset=offset, cache=CACHE, tag=f"fold{name}")

def fold_weeks(name):
    ev, _ = FOLDS[name]
    out = []
    for k in ev:
        P, Q = load_week(k)
        W = windows(P, Q)
        out.append((k, W, Feat(W[2], Ssc)))
    return out
