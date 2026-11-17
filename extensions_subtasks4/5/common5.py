"""Shared helpers of sub-task 4.5 (exact phasor model in the sizing loop, both lines).
Imports /home/claude/code read-only; writes only to this folder."""
import sys, json, os, math, time, hashlib
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing import network as net
from rpc_sizing.network import solve, _z, M, E, A
from rpc_sizing.experiment import week_case, seed_of, CASES
from rpc_sizing.params import SEED0, RPC, GRID
sys.path.insert(0, "/home/claude/subtasks4/5")
from fastsolve import solve_fast

HERE = "/home/claude/subtasks4/5"
CODE = "/home/claude/code"
SSC = 750.0
LIM = 2.0
W1 = RPC["cost_kUSD_per_MVA"] * 2.0 * RPC["crf"]
WY = RPC["weeks_per_year"]
EPS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 1.9]
C_FACT = [1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0, 2.5]
SEED_HS_NEW = SEED0 + 950000
SEED_SUB_NEW = SEED0 + 960000
THETA_S = np.arctan(10.0)
USE_C = os.environ.get("NO_CSOLVER") is None   # C re-implementation of network.solve (check_fastsolve.py)


def order_k(N, p=0.95):
    return int(math.ceil(round(p * N, 9)))


def design_quantile(x, p=0.95):
    x = np.sort(np.asarray(x, float))
    return float(x[order_k(len(x), p) - 1])


def load_week(line, k):
    if line == "hs":
        d = np.load(f"{CODE}/results/base_w{k:03d}.npz")
    elif line == "sub":
        d = np.load(f"{CODE}/results_sub/suburban_w{k:03d}.npz")
    elif line == "hs_new":
        d = np.load(f"{HERE}/newweeks/hs_new_w{k:03d}.npz")
    elif line == "sub_new":
        d = np.load(f"{HERE}/newweeks/sub_new_w{k:03d}.npz")
    else:
        raise ValueError(line)
    return d["P"].astype(float), d["Q"].astype(float)


def solve_c(S_alpha, S_beta, Ssc, S_b=100.0, n_iter=10, tol=1e-6):
    """Copy of rpc_sizing.network.solve; returns the COMPLEX ratio U2/U1 (pu) in addition,
    so that a background phasor can be added.  |U2/U1|*100 equals the VUF of network.solve."""
    Zs = _z(S_b / Ssc, 10.0)
    zT = _z(GRID["uk"] * S_b / GRID["trafo_leg_MVA"], 30.0)
    sa = np.asarray(S_alpha, complex) / S_b
    sb = np.asarray(S_beta, complex) / S_b
    n = sa.size
    U = np.tile(E, (n, 1))
    Ia = np.zeros(n, complex); Ib = np.zeros(n, complex)
    for _ in range(n_iter):
        u = U @ M.T
        ua = u[:, 0] - zT * Ia
        ub = u[:, 1] - zT * Ib
        Ia_new = np.conj(sa / ua)
        Ib_new = np.conj(sb / ub)
        Iph = 3.0 * np.stack([Ia_new, Ib_new], axis=1) @ M
        U_new = E[None, :] - Zs * Iph
        err = np.max(np.abs(U_new - U))
        U, Ia, Ib = U_new, Ia_new, Ib_new
        if err < tol:
            break
    U1 = (U[:, 0] + A * U[:, 1] + A ** 2 * U[:, 2]) / 3
    U2 = (U[:, 0] + A ** 2 * U[:, 1] + A * U[:, 2]) / 3
    return U2 / U1, np.abs(U2) / np.abs(U1) * 100.0


def u2_exact(P, Q, C, eps):
    """Complex negative-sequence ratio (in %, i.e. 100*U2/U1) of the substation at every second,
    and the per-leg transfer sxv (complex, MVA).  Same code path as exact_sizing.vuf_exact."""
    S = P + 1j * Q
    mag = np.abs(S)
    if C > 0:
        sx, _ = rpc.compensate(P, Q, C, eps, SSC)
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
    else:
        sxv = np.zeros_like(S)
    u2 = np.zeros(len(S), complex)
    vm = np.zeros(len(S))
    m = mag > 0
    r, vv = (solve_fast if USE_C else solve_c)(S[m] - sxv[m], sxv[m], SSC)
    u2[m] = 100.0 * r
    vm[m] = vv
    return u2, vm, sxv


def vuf_exact(P, Q, C, eps):
    """Identical to exact_sizing.vuf_exact (magnitude only)."""
    u2, vm, sxv = u2_exact(P, Q, C, eps)
    return vm, sxv


def p95_exact(P, Q, C, eps):
    return rpc.p95(rpc.vuf10(vuf_exact(P, Q, C, eps)[0]))


def window_moments(u2):
    n = len(u2) // rpc.WIN
    z = u2[: n * rpc.WIN].reshape(n, rpc.WIN)
    return dict(m2=(np.abs(z) ** 2).mean(1), mean=z.mean(1))


def v10_bg(mom, b, psi):
    """10-min rms of |b e^{j psi} + u2(t)| (exact for a constant background phasor in the window)."""
    bgp = b * np.exp(1j * psi)
    val = b * b + mom["m2"] + 2 * np.real(np.conj(bgp) * mom["mean"])
    return np.sqrt(np.maximum(val, 0.0))


def evaluate_exact(P, Q, C, eps):
    v, sxv = vuf_exact(P, Q, C, eps)
    sx = np.abs(sxv)
    v10 = rpc.vuf10(v)
    return dict(C=float(C), eps=float(eps), p95=rpc.p95(v10),
                p99=float(np.quantile(v10, 0.99, method="inverted_cdf")),
                vmax=float(v10.max()), share=float(np.mean(v10 > LIM + 1e-9)),
                E_viol=float(np.maximum(0, v10 - LIM).sum() / 6), E_loss=rpc.losses_MWh(sx, C),
                E_tr=float(sx.sum() / 3600))


def J_parts(C, E_loss_mean, E_viol_mean):
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    loss = RPC["energy_price_USD_MWh"] * E_loss_mean * WY / 1000
    viol = RPC["viol_price_kUSD_per_pct_h"] * E_viol_mean * WY
    return cap + loss + viol, cap, loss, viol


def J_of(evs):
    return J_parts(evs[0]["C"], np.mean([e["E_loss"] for e in evs]), np.mean([e["E_viol"] for e in evs]))


def cmin_exact(P, Q, eps, tol=0.02):
    """Identical logic to exact_sizing.cmin_exact (bisection, tol 0.02 MVA)."""
    f = lambda C: p95_exact(P, Q, C, eps) - LIM
    if f(0.0) <= 0:
        return 0.0
    hi = float(np.hypot(P, Q).max()) / 2 * 1.1 + 0.1
    if f(hi) > 0:
        return float("nan")
    c0 = rpc.c_min(P, Q, min(eps, LIM), SSC)
    lo, h = 0.0, hi
    for c in ((c0, c0 * 1.05, c0 * 1.1, c0 * 1.2) if np.isfinite(c0) else ()):
        if c > 0 and f(c) <= 0:
            h = c
            break
        lo = max(lo, c)
    hi = h
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return hi


def save_json(obj, path):
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w"), indent=1, default=float)
    os.replace(tmp, path)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cp_upper(k, n, conf=0.95):
    from scipy import stats
    return 1.0 if k >= n else float(stats.beta.ppf(conf, k + 1, n - k))
