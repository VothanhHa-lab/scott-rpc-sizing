"""Robustness: cap on the threshold (theta_max) vs clock misalignment tau of the controller windows."""
import time
from common import *
from rpc_sizing.params import RPC
Wk = RPC["weeks_per_year"]
name = "tab_v1.9_q0.99"
D = json.load(open(os.path.join(HERE, f"design_{name}.json")))
best = min(D["cands"], key=lambda c: c["J"]); C = best["C"]; vs, q = D["vstar"], D["q"]; iq = QS.index(q)
cg = np.array([np.floor(C), np.floor(C) + 1.0])
t0 = time.time()
def Jm(evs):
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    loss = np.mean([e["E_loss"] for e in evs]) * Wk * RPC["energy_price_USD_MWh"] / 1000
    viol = np.mean([e["E_viol"] for e in evs]) * Wk * RPC["viol_price_kUSD_per_pct_h"]
    return dict(J=float(cap + loss + viol), Jviol=float(viol), comply=float(np.mean([e["p95"] <= 2 + 1e-6 for e in evs])),
                p95=float(np.mean([e["p95"] for e in evs])), vmax=float(np.mean([e["vmax10"] for e in evs])))
out = {}
for tau in [0, 60, 300]:
    TT = {}
    for n in FOLDS:
        ev_w, cal = FOLDS[n]
        Pc, Qc = zip(*[load_week(k) for k in cal])
        TT[n] = Tables(Pc, Qc, Ssc, QS, cg, offset=tau, cache=CACHE, tag=f"fold{n}")
    data = []
    for n in FOLDS:
        G = TT[n].get(C, iq)
        for k in FOLDS[n][0]:
            P, Q = load_week(k); W = windows(P, Q, offset=tau); data.append((G, W, Feat(W[2], Ssc, offset=tau)))
    for tm in [None, 4.0, 3.0, 2.5, 2.0]:
        evs = []
        for G, W, F in data:
            sx, v = run(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F, theta_max=tm)
            evs.append(evaluate_run(np.roll(sx.reshape(-1), tau), np.roll(v.reshape(-1), tau), C))
        out[f"tau{tau}_tmax{tm}"] = Jm(evs); print(tau, tm, out[f"tau{tau}_tmax{tm}"], time.time() - t0, flush=True)
    # (15) with eps=1 is insensitive to tau by construction
json.dump(out, open(os.path.join(HERE, "robust.json"), "w"), indent=1)
