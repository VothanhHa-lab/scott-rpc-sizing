"""Shared helpers for sub-task 4.1 (read-only use of /home/claude/code)."""
import sys, json, math, os
sys.path.insert(0, "/home/claude/code")
import numpy as np
from rpc_sizing import rpc
from rpc_sizing.network import solve
from rpc_sizing.params import RPC, GRID, SEED0

CODE = "/home/claude/code"
OUT = "/home/claude/subtasks4/1"
LIM = GRID["vuf_lim"]            # 2.0 (percent)
WY = RPC["weeks_per_year"]
SSC = 750.0

PATHS = {"base": CODE + "/results/base_w%03d.npz",
         "cert": CODE + "/results_exact/cert_w%03d.npz",
         "sub": CODE + "/results_sub/suburban_w%03d.npz"}
NW = {"base": 60, "cert": 90, "sub": 40}


def load_week(name, k):
    d = np.load(PATHS[name] % k)
    return d["P"].astype(float), d["Q"].astype(float)        # float32 store -> float64 (as in pass2/stepA2)


def q95(x, p=0.95):
    """Design quantile = X_(ceil(p N)) (numpy inverted_cdf)."""
    return float(np.quantile(np.asarray(x, float), p, method="inverted_cdf"))


def vuf_series_approx(P, Q, C, eps, ssc=SSC):
    sx, v = rpc.compensate(P, Q, C, eps, ssc)
    return v, np.abs(sx)


def vuf_series_exact(P, Q, C, eps, ssc=SSC):
    """Identical to exact_sizing.vuf_exact (copied to return |sx| too, not imported to avoid its CLI)."""
    S = P + 1j * Q
    mag = np.abs(S)
    if C > 0:
        sx, _ = rpc.compensate(P, Q, C, eps, ssc)
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
    else:
        sxv = np.zeros_like(S)
    v = np.zeros(len(S))
    m = mag > 0
    v[m], _ = solve(S[m] - sxv[m], sxv[m], ssc, n_iter=10, tol=1e-6)
    return v, np.abs(sxv)


def week_metrics(v, sx, C):
    """Per-week metrics from the 1-s VUF series v (%) and transfer |sx| (MVA)."""
    v10 = rpc.vuf10(v)
    exceed = np.maximum(0.0, v10 - LIM)
    E_viol = float(exceed.sum() / 6.0)
    E_loss = rpc.losses_MWh(sx, C)
    J_cap = RPC["cost_kUSD_per_MVA"] * 2.0 * C * RPC["crf"]
    J_loss = RPC["energy_price_USD_MWh"] * E_loss * WY / 1000.0
    J_viol = RPC["viol_price_kUSD_per_pct_h"] * E_viol * WY
    return dict(C=float(C), P95=rpc.p95(v10), P99=q95(v10, 0.99), vmax10=float(v10.max()),
                share_gt2_pct=100.0 * float(np.mean(v10 > LIM + 1e-9)),
                E_viol=E_viol, E_loss=E_loss, J_cap=J_cap, J_loss=J_loss, J_viol=J_viol,
                J=J_cap + J_loss + J_viol, E_transfer=float(np.sum(sx) / 3600.0), n10=int(len(v10)))


def eval_week(P, Q, C, eps, model, ssc=SSC):
    f = vuf_series_approx if model == "approx" else vuf_series_exact
    v, sx = f(P, Q, C, eps, ssc)
    m = week_metrics(v, sx, C)
    m["eps_u"] = float(eps)
    return m
