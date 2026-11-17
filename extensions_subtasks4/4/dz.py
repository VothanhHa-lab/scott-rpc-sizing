"""Design (line search) with the approximate model (8) and the rpc design rule of experiment.py/analyse.py,
extended by the absolute grid of sub-task 3.4 (union grid, explicit compliance test).

design(weeks) -> dict with weekly C_min(eps), C_hat(eps), candidate table, selected optimum (proposed),
the 'percentile' (eps = 2 %, C = C_hat) and the 'percentile, C optimised' designs.

weeks: list of (P, Q) float arrays (1 s, one week each); Ssc in MVA.
Costs: J = w1 C + w2 E_loss + w3 E_viol (kUSD/yr), exactly analyse.cost_terms.
"""
import sys, math, time
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing.params import RPC, GRID
from rpc_sizing.experiment import EPS_GRID, C_FACT

LIM = GRID["vuf_lim"]
WY = RPC["weeks_per_year"]
W1 = RPC["cost_kUSD_per_MVA"] * 2.0 * RPC["crf"]
FIELDS = ["p95", "E_viol", "E_loss", "E_transfer", "vmax10", "share_above"]


def order_k(N, p=0.95):
    return int(math.ceil(round(p * N, 9)))


def evalw(P, Q, C, e, Ssc):
    ev = rpc.evaluate(P, Q, C, e, Ssc)
    return [ev[f] for f in FIELDS]


def Jterms(C, A):
    """A: array [week, field] for one candidate."""
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    loss = RPC["energy_price_USD_MWh"] * A[:, 2].mean() * WY / 1000
    viol = RPC["viol_price_kUSD_per_pct_h"] * A[:, 1].mean() * WY
    return cap + loss + viol, cap, loss, viol


def design(weeks, Ssc=750.0, log=None, abs_grid=True, eps_list=None):
    t0 = time.time()
    N = len(weeks)
    eps_list = list(EPS_GRID) if eps_list is None else eps_list
    # 1. weekly minimum ratings
    cm = np.array([[rpc.c_min(P, Q, e, Ssc) for e in eps_list] for (P, Q) in weeks])
    if log: log(f"cmin done {time.time()-t0:.0f}s")
    k = order_k(N)
    chat = np.array([np.sort(cm[~np.isnan(cm[:, i]), i])[k - 1] if (~np.isnan(cm[:, i])).sum() >= k else np.nan
                     for i in range(len(eps_list))])
    S_peak = np.array([np.hypot(P, Q).max() for P, Q in weeks])
    # 2. candidates: Chat*factors, then absolute grid up to Jbest/w1
    cache = {}

    def get(e, C):
        key = (round(float(e), 6), round(float(C), 6))
        if key not in cache:
            cache[key] = np.array([evalw(P, Q, C, e, Ssc) for (P, Q) in weeks])
        return cache[key]

    cands = []
    for i, e in enumerate(eps_list):
        if np.isnan(chat[i]):
            continue
        for f in C_FACT:
            cands.append((float(e), float(chat[i] * f)))
    best = None
    for e, C in cands:
        A = get(e, C)
        if (A[:, 0] <= LIM + 1e-9).sum() >= k:
            J = Jterms(C, A)[0]
            if best is None or J < best:
                best = J
    if log: log(f"factor candidates done {time.time()-t0:.0f}s, best J {best:.1f}")
    if abs_grid:
        Cmax = best / W1
        grid = [round(0.25 * i, 2) for i in range(0, 21)]
        c = 5.0
        while c < Cmax + 0.5:
            c += 0.5; grid.append(round(c, 2))
        grid = [g for g in grid if g <= Cmax + 0.5]
        for i, e in enumerate(eps_list):
            if np.isnan(chat[i]):
                continue
            for g in grid:
                if 0 < g < 0.95 * chat[i]:        # fewer than ceil(0.95 N) weeks can comply below ~Chat
                    continue
                cands.append((float(e), float(g)))
    # also C = 0 per eps = 2 (no compensation) and peak ratings are not needed for the line search
    uniq = sorted(set((round(e, 6), round(C, 6)) for e, C in cands))
    rows = []
    for e, C in uniq:
        A = get(e, C)
        J, cap, loss, viol = Jterms(C, A)
        rows.append(dict(eps=e, C=C, J=J, cap=cap, loss=loss, viol=viol,
                         n_comply=int((A[:, 0] <= LIM + 1e-9).sum()),
                         p95_mean=float(A[:, 0].mean()), vmax=float(A[:, 4].mean()),
                         share=float(A[:, 5].mean()), Eviol_yr=float(A[:, 1].mean() * WY),
                         Eloss_yr=float(A[:, 2].mean() * WY), Etr_yr=float(A[:, 3].mean() * WY)))
    ok = [r for r in rows if r["n_comply"] >= k]
    prop = min(ok, key=lambda r: r["J"])
    ok2 = [r for r in ok if abs(r["eps"] - LIM) < 1e-9]
    if LIM in [float(e) for e in eps_list]:
        ch = chat[[float(e) for e in eps_list].index(LIM)]
        p95 = min([r for r in rows if abs(r["eps"] - LIM) < 1e-9 and abs(r["C"] - ch) < 1e-5], key=lambda r: r["C"])
        p95c = min(ok2, key=lambda r: r["J"])
    else:
        p95 = p95c = None
    if log: log(f"design done {time.time()-t0:.0f}s: C*={prop['C']:.2f} eps*={prop['eps']} J={prop['J']:.1f}")
    return dict(N=N, k=k, eps_list=[float(e) for e in eps_list], cmin=cm.tolist(), chat=chat.tolist(),
                S_peak=S_peak.tolist(), proposed=prop, percentile=p95, percentile_Copt=p95c,
                n_cands=len(rows), table=rows)


def evaluate_design(weeks, C, eps, Ssc=750.0):
    """Cost and compliance of a given (C, eps) on a set of weeks."""
    A = np.array([evalw(P, Q, C, eps, Ssc) for (P, Q) in weeks])
    J, cap, loss, viol = Jterms(C, A)
    return dict(C=C, eps=eps, J=J, cap=cap, loss=loss, viol=viol, n_comply=int((A[:, 0] <= LIM + 1e-9).sum()),
                N=len(weeks), p95_mean=float(A[:, 0].mean()), vmax=float(A[:, 4].mean()), share=float(A[:, 5].mean()),
                Eviol_yr=float(A[:, 1].mean() * WY), Eloss_yr=float(A[:, 2].mean() * WY),
                p95_weeks=A[:, 0].tolist(), Eviol_weeks=A[:, 1].tolist())


def weekly_cmin(weeks, eps, Ssc=750.0):
    return np.array([rpc.c_min(P, Q, eps, Ssc) for (P, Q) in weeks])
