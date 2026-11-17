"""Extras at the chosen design: hopeless-window rules, clock misalignment,
rate/utilisation checks, window time series for the figure.
usage: python extras.py <design name>"""
import time
from common import *
from rpc_sizing.params import RPC
Wk = RPC["weeks_per_year"]
name = sys.argv[1]
D = json.load(open(os.path.join(HERE, f"design_{name}.json")))
best = min(D["cands"], key=lambda c: c["J"]); C = best["C"]; vs, q = D["vstar"], D["q"]; iq = QS.index(q)
print("design", name, "C", C, flush=True)
t0 = time.time()
TAB = {n: fold_tables(n) for n in FOLDS}
WK = {n: fold_weeks(n) for n in FOLDS}
def Jmean(evs):
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    loss = np.mean([e["E_loss"] for e in evs]) * Wk * RPC["energy_price_USD_MWh"] / 1000
    viol = np.mean([e["E_viol"] for e in evs]) * Wk * RPC["viol_price_kUSD_per_pct_h"]
    return dict(J=float(cap + loss + viol), Jloss=float(loss), Jviol=float(viol), Eviol=float(np.mean([e["E_viol"] for e in evs]) * Wk),
                comply=float(np.mean([e["p95"] <= 2 + 1e-6 for e in evs])), Etr=float(np.mean([e["E_transfer"] for e in evs]) * Wk),
                p95=float(np.mean([e["p95"] for e in evs])))
out = dict(name=name, C=C, vstar=vs, q=q)
# --- hopeless-window rules
hl = {}
for rule in ["greedy", "skip_certain", "skip_forecast"]:
    evs = []
    for n in FOLDS:
        G = TAB[n].get(C, iq)
        for k, W, F in WK[n]:
            evs.append(week_eval(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F, hopeless_rule=rule))
    hl[rule] = Jmean(evs); print(rule, hl[rule], flush=True)
out["hopeless"] = hl
# --- utilisation / ramps
st = {}; dsx_b = []; dsx_15 = []; util15 = 0.0
for n in FOLDS:
    G = TAB[n].get(C, iq)
    for k, W, F in WK[n][:10]:
        sx, v = run(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F, stats=st)
        dsx_b.append(np.abs(np.diff(sx.reshape(-1))))
        P, Q = load_week(k)
        s15, _ = rpc.compensate(P, Q, C, 1.0, Ssc); dsx_15.append(np.abs(np.diff(s15)))
db, d15 = np.concatenate(dsx_b), np.concatenate(dsx_15)
out["rates"] = dict(util_max=st["util_max"], kappa=KAPPA, dsx_max_budget=float(db.max()), dsx_max_15=float(d15.max()),
                    dsx_p9999_budget=float(np.quantile(db, 0.9999)), dsx_p9999_15=float(np.quantile(d15, 0.9999)),
                    n_weeks=20)
print(out["rates"], flush=True)
# --- clock misalignment (controller windows shifted by tau against the measurement grid)
mis = {}
cg = np.array([np.floor(C), np.floor(C) + 1.0])
for tau in [60, 300]:
    evs = []
    for n in FOLDS:
        ev_w, cal = FOLDS[n]
        Pc, Qc = zip(*[load_week(k) for k in cal])
        T = Tables(Pc, Qc, Ssc, QS, cg, offset=tau, cache=CACHE, tag=f"fold{n}")
        G = T.get(C, iq)
        for k in ev_w:
            P, Q = load_week(k)
            W = windows(P, Q, offset=tau); F = Feat(W[2], Ssc, offset=tau)
            sx, v = run(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F)
            sx = np.roll(sx.reshape(-1), tau); v = np.roll(v.reshape(-1), tau)
            evs.append(evaluate_run(sx, v, C))
    mis[str(tau)] = Jmean(evs); print("offset", tau, mis[str(tau)], time.time() - t0, flush=True)
out["misalign"] = mis
json.dump(out, open(os.path.join(HERE, "extras.json"), "w"), indent=1)
