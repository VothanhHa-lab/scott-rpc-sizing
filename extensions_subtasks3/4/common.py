"""Shared helpers for sub-task 3.4 (line search, quantile rule, grid sensitivity).
Reads the code base /home/claude/code read-only; writes only to this folder."""
import sys, json, math
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing.params import RPC, GRID

CODE = "/home/claude/code"
LIM = GRID["vuf_lim"]            # 2 %
WY = RPC["weeks_per_year"]
W1 = RPC["cost_kUSD_per_MVA"] * 2.0 * RPC["crf"]     # kUSD/(MVA yr), both legs = 30.57
TOL = 1e-9


def order_k(N, p=0.95):
    """Index k (1-based) of the order statistic X_(k) returned by the 95 % quantile rule:
    numpy.quantile(..., method='inverted_cdf') = X_(ceil(p*N)).  round() removes float noise."""
    return int(math.ceil(round(p * N, 9)))


def design_quantile(x, p=0.95):
    x = np.sort(np.asarray(x, float))
    return float(x[order_k(len(x), p) - 1])


def load_summary(case):
    d = {"base": "results", "suburban": "results_sub"}.get(case, "results40")
    return json.load(open(f"{CODE}/{d}/{case}.json"))


def load_week(case, k):
    """Weekly P,Q (float64) exactly as used in the stored evaluations."""
    if case == "base":
        d = np.load(f"{CODE}/results/base_w{k:03d}.npz")
        return d["P"].astype(float), d["Q"].astype(float)
    if case == "suburban":
        d = np.load(f"{CODE}/results_sub/suburban_w{k:03d}.npz")
        return d["P"].astype(float), d["Q"].astype(float)
    from rpc_sizing.experiment import week_case, seed_of     # regenerated from the seeds
    return week_case(case, k, seed_of(case))


FIELDS = ["p95", "E_viol", "E_loss", "E_transfer", "vmax10", "share_above"]


def old_arrays(summary, Ssc, n_old=72):
    """Stored evaluations of the original 72 candidates -> arrays [cand, week]."""
    d = summary["design"][str(Ssc)]
    cands = d["cands"][:n_old]
    ev = d["evals"]
    A = {f: np.array([[ev[k][i][f] for k in range(len(ev))] for i in range(n_old)]) for f in FIELDS}
    return [tuple(c) for c in cands], A


def J_arrays(C, A, w=None):
    """Mean annual cost terms (kUSD/yr) of candidates; C: [cand]; A: field arrays [cand, week]."""
    w = w or {}
    cc = w.get("cost", RPC["cost_kUSD_per_MVA"]); pe = w.get("price", RPC["energy_price_USD_MWh"])
    pv = w.get("viol", RPC["viol_price_kUSD_per_pct_h"])
    cap = cc * 2 * np.asarray(C) * RPC["crf"]
    loss = pe * A["E_loss"].mean(axis=1) * WY / 1000
    viol = pv * A["E_viol"].mean(axis=1) * WY
    return cap + loss + viol, cap, loss, viol


def n_comply(A, tol=TOL):
    return (A["p95"] <= LIM + tol).sum(axis=1)


def select(cands, A, N, mask=None, w=None):
    """Minimum J among candidates meeting the compliance rule (>= ceil(0.95 N) weeks)."""
    C = np.array([c[1] for c in cands])
    J = J_arrays(C, A, w)[0]
    ok = n_comply(A) >= order_k(N)
    if mask is not None:
        ok = ok & mask
    idx = np.where(ok)[0]
    i = idx[np.argmin(J[idx])]
    return int(i), J
