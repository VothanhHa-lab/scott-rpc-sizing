"""Stage 1: tables for both folds + scan of (v*, q) at the fixed rating C=10.44
(the design of proposed (15)); also (15) reference at the same C and the oracle."""
import time
from common import *
C0 = 10.4387
t0 = time.time()
TAB = {n: fold_tables(n) for n in FOLDS}
print("tables built", time.time() - t0, flush=True)
VS = [1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
res = {}
def aggJ(evs):
    Js = [annual_J(e) for e in evs]
    m = {k: float(np.mean([e[k] for e in evs])) for k in ["p95", "E_viol", "E_loss", "E_transfer", "share_above"]}
    m["Ewk"] = {k: [e[k] for e in evs] for k in ["E_viol", "E_loss"]}
    return m
from rpc_sizing.params import RPC
Wk = RPC["weeks_per_year"]
def J_of(m, C):
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    return cap + RPC["energy_price_USD_MWh"] * m["E_loss"] * Wk / 1000 + RPC["viol_price_kUSD_per_pct_h"] * m["E_viol"] * Wk
for name in FOLDS:
    weeks = fold_weeks(name)
    for vs in VS:
        for iq, q in enumerate(QS):
            evs = []
            G = TAB[name].get(C0, iq)
            for k, W, F in weeks:
                evs.append(week_eval(*W, C0, Ssc, kind="table", vstar=vs, G=G, feat=F))
            res.setdefault(f"table_v{vs}_q{q}", {})[name] = {kk: float(np.mean([e[kk] for e in evs])) for kk in ["p95", "E_viol", "E_loss", "E_transfer", "share_above"]}
        evs = [week_eval(*W, C0, Ssc, kind="uniform", vstar=vs) for k, W, F in weeks]
        res.setdefault(f"uniform_v{vs}", {})[name] = {kk: float(np.mean([e[kk] for e in evs])) for kk in ["p95", "E_viol", "E_loss", "E_transfer", "share_above"]}
        evs = [week_eval(*W, C0, Ssc, kind="oracle", vstar=vs) for k, W, F in weeks]
        res.setdefault(f"oracle_v{vs}", {})[name] = {kk: float(np.mean([e[kk] for e in evs])) for kk in ["p95", "E_viol", "E_loss", "E_transfer", "share_above"]}
    for eps in [0.0, 0.5, 1.0, 1.5, 2.0]:
        evs = []
        for k, W, F in weeks:
            P, Q = load_week(k)
            evs.append(rpc.evaluate(P, Q, C0, eps, Ssc))
        res.setdefault(f"eq15_eps{eps}", {})[name] = {kk: float(np.mean([e[kk] for e in evs])) for kk in ["p95", "E_viol", "E_loss", "E_transfer", "share_above"]}
    print(name, "done", time.time() - t0, flush=True)
# pooled means (equal fold sizes) and J at C0
out = {}
for key, d in res.items():
    m = {kk: 0.5 * (d["A"][kk] + d["B"][kk]) for kk in d["A"]}
    m["J"] = J_of(m, C0)
    out[key] = m
json.dump(dict(C0=C0, results=out, per_fold=res), open(os.path.join(HERE, "stage1.json"), "w"), indent=1)
for key, m in sorted(out.items(), key=lambda kv: kv[1]["J"]):
    print(f"{key:24s} J={m['J']:.1f} Eviol={m['E_viol']:.3f} Eloss={m['E_loss']:.2f} Etr={m['E_transfer']:.0f} p95={m['p95']:.2f}")
