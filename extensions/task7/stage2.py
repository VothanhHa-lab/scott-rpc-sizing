"""Stage 2: full design for selected controllers with the SAME design rule as (15):
weekly C_min by bisection (P95 of VUF10 <= 2 %), design C = 95 % quantile over
the 60 weeks (two-fold cross-fitted forecast tables), line search over C = f*C_des.
usage: python stage2.py name kind vstar q [hopeless_rule] [theta_max]"""
import time
from common import *
from rpc_sizing.params import RPC
Wk = RPC["weeks_per_year"]
FACT = [1.0, 1.1, 1.2, 1.35, 1.5, 1.75]
name, kind, vstar = sys.argv[1], sys.argv[2], float(sys.argv[3])
q = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != "-" else None
hr = sys.argv[5] if len(sys.argv) > 5 else "greedy"
tmax = float(sys.argv[6]) if len(sys.argv) > 6 else None
t0 = time.time()
TAB = {n: fold_tables(n) for n in FOLDS} if kind == "table" else {}
iq = QS.index(q) if q is not None else None
cmins = np.full(60, np.nan); weekdata = {}
for n in FOLDS:
    for k, W, F in fold_weeks(n):
        weekdata[k] = (n, W, F)

def kw_for(k, C):
    n, W, F = weekdata[k]
    kw = dict(kind=kind, vstar=vstar)
    if kind == "table":
        kw.update(G=TAB[n].get(C, iq), feat=F, hopeless_rule=hr, theta_max=tmax)
    elif kind == "uniform":
        kw.update(hopeless_rule=hr, theta_max=tmax)
    return kw

def ev_week(k, C):
    n, W, F = weekdata[k]
    if kind == "oracle":
        sx, v = oracle(*W, C, Ssc, vstar=vstar)
    else:
        sx, v = run(*W, C, Ssc, **{a: b for a, b in kw_for(k, C).items() if a != "kind"}, kind=kind)
    return evaluate_run(sx, v, C)

for k in range(60):
    n, W, F = weekdata[k]
    f = lambda C: ev_week(k, C)["p95"] - 2.0
    lo = max(CMIN0[k] - 0.05, 0.1); hi = CMIN[1.0][k] * 1.05
    if f(lo) <= 0:
        cmins[k] = lo; continue
    while f(hi) > 0:
        hi *= 1.1
    while hi - lo > 0.02:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0: hi = mid
        else: lo = mid
    cmins[k] = hi
cdes = float(np.quantile(cmins, 0.95, method="inverted_cdf"))
print(name, "cdes", cdes, "greedy cdes", np.quantile(CMIN0, 0.95, method="inverted_cdf"), "t", time.time() - t0, flush=True)
cands = []
for fct in FACT:
    C = cdes * fct
    evs = [ev_week(k, C) for k in range(60)]
    Jw = []
    for e in evs:
        J, cap, loss, viol = annual_J(e)
        Jw.append(J)
    Jm = float(np.mean(Jw))
    capc = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    d = dict(f=fct, C=C, J=Jm, Jcap=capc,
             Jloss=float(np.mean([RPC["energy_price_USD_MWh"] * e["E_loss"] * Wk / 1000 for e in evs])),
             Jviol=float(np.mean([RPC["viol_price_kUSD_per_pct_h"] * e["E_viol"] * Wk for e in evs])),
             comply=float(np.mean([e["p95"] <= 2.0 + 1e-6 for e in evs])),
             p95_mean=float(np.mean([e["p95"] for e in evs])), vmax=float(np.mean([e["vmax10"] for e in evs])),
             share=float(np.mean([e["share_above"] for e in evs])),
             Eviol=float(np.mean([e["E_viol"] for e in evs]) * Wk), Eloss=float(np.mean([e["E_loss"] for e in evs]) * Wk),
             Etr=float(np.mean([e["E_transfer"] for e in evs]) * Wk),
             dsx_max=float(max(e["dsx_max"] for e in evs)), sx_max=float(max(e["sx_max"] for e in evs)),
             Jweek=Jw, Eviol_wk=[e["E_viol"] for e in evs], Eloss_wk=[e["E_loss"] for e in evs],
             p95_wk=[e["p95"] for e in evs])
    cands.append(d)
    print(f"  f={fct} C={C:.2f} J={Jm:.1f} cap/loss/viol={d['Jcap']:.0f}/{d['Jloss']:.0f}/{d['Jviol']:.0f} comply={d['comply']:.2f} Eviol={d['Eviol']:.1f} Etr={d['Etr']:.0f}", flush=True)
best = min(cands, key=lambda d: d["J"])
json.dump(dict(name=name, kind=kind, vstar=vstar, q=q, hopeless=hr, theta_max=tmax, cmin_wk=cmins.tolist(), cdes=cdes,
               cands=cands, best_f=best["f"]), open(os.path.join(HERE, f"design_{name}.json"), "w"))
print("BEST", name, best["f"], best["C"], best["J"], "t", time.time() - t0)
