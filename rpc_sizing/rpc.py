"""Capacity-constrained RPC compensation, VUF aggregation and sizing.

Notation (per converter leg): the beta leg draws s_x = P_x + jq from feeder
beta and the alpha leg injects it into feeder alpha, so that
    S_alpha = S_L - s_x,  S_beta = s_x,
    VUF ~ |S_L - 2 s_x| / S_sc     (general form of (8), section 2).
Compensation is applied along S_L (expression (11)); with the threshold
policy u = eps_u the requested power per leg is
    s_x* = max(0, |S_L| - eps_u S_sc) / 2,
and the delivered power is limited by the leg rating C and by the rated
current at the actual busbar voltage:  |s_x| <= kappa C U_pu(t).
"""
import numpy as np
from .params import RPC, GRID, feeder_rx

WIN = 600  # samples (1 s) per 10-min aggregation window
# usable share of the leg rating for the power transfer; the remainder is the
# headroom of the beta leg for the converter losses and the DC-voltage control
KAPPA = 0.96


def busbar_voltage(P, Q, Ssc):
    r, x = feeder_rx(Ssc)
    return 1.0 - (r * P + x * Q)


def compensate(P, Q, C, eps_u, Ssc, current_limit=True):
    """Return per-leg transfer |s_x| (MVA) and the instantaneous VUF (%)."""
    S = np.hypot(P, Q)
    req = np.maximum(0.0, S - eps_u / 100.0 * Ssc) / 2.0
    if current_limit and C > 0:
        # alpha-busbar voltage with the transfer applied (one fixed-point step)
        frac = np.where(S > 0, np.minimum(req, C) / np.maximum(S, 1e-9), 0.0)
        U = busbar_voltage(P * (1 - frac), Q * (1 - frac), Ssc)
        avail = KAPPA * C * np.minimum(U, 1.0)
    else:
        avail = KAPPA * C
    sx = np.minimum(req, avail)
    vuf = np.abs(S - 2.0 * sx) / Ssc * 100.0
    return sx, vuf


def vuf10(vuf_inst):
    """10-min values: rms aggregation (IEC 61000-4-30) of the 1 s values."""
    n = len(vuf_inst) // WIN
    v = vuf_inst[: n * WIN].reshape(n, WIN)
    return np.sqrt(np.mean(v ** 2, axis=1))


def p95(v10):
    return float(np.quantile(v10, 0.95, method="inverted_cdf"))


def losses_MWh(sx, C):
    """Energy loss of both legs over the record (1 s samples), MWh."""
    if C <= 0:
        return 0.0
    k0, k1, k2 = RPC["k0"], RPC["k1"], RPC["k2"]
    p = 2.0 * (k0 * C + k1 * sx + k2 * sx ** 2 / C)   # MW
    return float(p.sum() / 3600.0)


def evaluate(P, Q, C, eps_u, Ssc, lim=None):
    lim = GRID["vuf_lim"] if lim is None else lim
    sx, v = compensate(P, Q, C, eps_u, Ssc)
    v10 = vuf10(v)
    exceed = np.maximum(0.0, v10 - lim)
    return dict(
        C=C, eps_u=eps_u,
        p95=p95(v10), vmax10=float(v10.max()),
        share_above=float(np.mean(v10 > lim + 1e-9)),
        E_viol=float(exceed.sum() / 6.0),            # %.h per record
        E_loss=losses_MWh(sx, C),                     # MWh per record
        E_transfer=float(sx.sum() / 3600.0),          # MWh per leg
        sx_max=float(sx.max()),
    )


def annual_cost(ev, weeks=None):
    """J = w1*C + w2*E_loss + w3*E_viol in kUSD/yr (record = one week)."""
    w = RPC["weeks_per_year"] if weeks is None else weeks
    cap = RPC["cost_kUSD_per_MVA"] * 2.0 * ev["C"] * RPC["crf"]
    loss = RPC["energy_price_USD_MWh"] * ev["E_loss"] * w / 1000.0
    viol = RPC["viol_price_kUSD_per_pct_h"] * ev["E_viol"] * w
    return cap + loss + viol, cap, loss, viol


def c_min(P, Q, eps_u, Ssc, lim=None, tol=0.01):
    """Smallest C with P95[VUF_10min] <= lim for the given policy (bisection)."""
    lim = GRID["vuf_lim"] if lim is None else lim
    if eps_u > lim + 1e-12:
        raise ValueError("eps_u must not exceed the VUF limit")
    f = lambda C: p95(vuf10(compensate(P, Q, C, eps_u, Ssc)[1])) - lim
    if f(0.0) <= 0:
        return 0.0
    hi = float(np.hypot(P, Q).max()) / 2.0 * 1.1 + 0.1
    if f(hi) > 0:
        return np.nan
    lo = 0.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return hi


def peak_rating(P, Q, Ssc, lim=None):
    lim = GRID["vuf_lim"] if lim is None else lim
    return max(0.0, float(np.hypot(P, Q).max()) - lim / 100.0 * Ssc) / 2.0


def full_rating(P, Q):
    return float(np.hypot(P, Q).max()) / 2.0
