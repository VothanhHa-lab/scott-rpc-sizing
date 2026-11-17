"""Window-budget (10-min-aware) RPC compensation controller.

Causal controller that tracks, inside the current 10-min aggregation window,
the accumulated squared 1-s VUF  A_k = sum_{j<k} v_j^2  and chooses the
per-second threshold theta_k (in % VUF) of the law
        s_x = min{ max(0, |S_L| - theta_k S_sc)/2 , kappa C U(t) }          (15')
such that the window rms ends at or below the target v*:
        B_k = 600 v*^2 - A_k   (remaining budget),
        theta_k = largest theta with  Q_q[ sum_{j>=k} v_j(theta)^2 ] <= B_k,
where Q_q is the q-quantile over a calibration ensemble of windows of the same
class and state (previous weeks) of the remaining squared VUF under threshold theta.
The delivered power is limited exactly as in rpc.compensate (same kappa, busbar
voltage), so the capacity/current limit is identical to (15).

Vectorised over the 1008 windows of a week; python loop over the 600 s.
"""
import sys, os
sys.path.insert(0, "/home/claude/code")
import numpy as np
from rpc_sizing import rpc
from rpc_sizing.rpc import KAPPA, WIN, busbar_voltage
from rpc_sizing.params import RPC, GRID

NW, K, DEC = 1008, WIN, 10          # windows/week, s/window, decision period (s)
ND = K // DEC
NSLOT = 144                          # 10-min slots per day
THETA = np.r_[np.arange(0, 2.5, 0.125), np.arange(2.5, 5.0, 0.25),
              [5.5, 6.0, 7.0, 8.0, 10.0]]
TH_TOP = THETA[-1]


def load_week(k, d="/home/claude/code/results"):
    z = np.load(os.path.join(d, f"base_w{k:03d}.npz"))
    return z["P"].astype(float), z["Q"].astype(float)


def windows(P, Q, offset=0):
    """(NW,600) arrays of P, Q, S; offset rolls the window grid (s)."""
    if offset:
        P, Q = np.roll(P, -offset), np.roll(Q, -offset)
    P = P.reshape(NW, K); Q = Q.reshape(NW, K)
    return P, Q, np.hypot(P, Q)


def deliver(P, Q, S, req, C, Ssc):
    """Same physics as rpc.compensate (current limit at the actual busbar
    voltage); returns delivered s_x and the available limit."""
    frac = np.where(S > 0, np.minimum(req, C) / np.maximum(S, 1e-9), 0.0)
    U = busbar_voltage(P * (1 - frac), Q * (1 - frac), Ssc)
    avail = KAPPA * C * np.minimum(U, 1.0)
    return np.minimum(req, avail), avail, U


# ---------------------------------------------------------------- tables
# Forecast of the remaining squared VUF of the window, conditioned on
#   (i)  the traffic class of the clock time (night / peak / off-peak, from the
#        timetable) and
#   (ii) the state: causal 30-s mean of the uncompensated VUF at the decision
#        instant, in NB bins.
from rpc_sizing.params import TIMETABLE
BIN_EDGES = np.array([0.5, 1.5, 2.5, 3.5, 5.0])      # % VUF  -> 6 bins
LAG = 30                                             # s, state averaging
NMIN = 40                                            # min. cell population


def traffic_class(offset=0):
    """Class of every window of the week (0 night, 1 peak, 2 off-peak)."""
    t0 = (np.arange(NW) * K + offset) % 86400
    h = t0 // 3600
    cls = np.full(NW, 2)
    cls[(h < TIMETABLE["t_start_h"]) | (h >= TIMETABLE["t_end_h"])] = 0
    for a, b in TIMETABLE["peak_hours"]:
        cls[(h >= a) & (h < b)] = 1
    return cls


def state_bins(Sw, Ssc, edges=BIN_EDGES):
    """(NW,ND) bin of the causal LAG-s mean of u at each decision instant."""
    u = (Sw / Ssc * 100).reshape(-1)
    cs = np.concatenate([[0.0], np.cumsum(u)])
    t = np.arange(NW)[:, None] * K + DEC * np.arange(ND)[None, :]
    lo = np.maximum(t - LAG, 0)
    ub = (cs[t] - cs[lo]) / np.maximum(t - lo, 1)
    return np.searchsorted(edges, ub)


def build_table(Pc, Qc, C, Ssc, qs, offset=0, thetas=THETA, edges=BIN_EDGES):
    """G[q, class, bin, d, ith]: q-quantile (over calibration windows of the
    cell) of sum_{j >= DEC*d} v_j(theta)^2, v_j = min(u_j, max(theta, r_j)),
    u uncompensated VUF, r residual VUF under full capacity-limited
    compensation with rating C."""
    nb = len(edges) + 1
    us, rs, bs = [], [], []
    for P, Q in zip(Pc, Qc):
        Pw, Qw, Sw = windows(P, Q, offset)
        sx, _, _ = deliver(Pw, Qw, Sw, Sw / 2.0, C, Ssc)
        us.append((Sw / Ssc * 100).astype(np.float32))
        rs.append((np.abs(Sw - 2 * sx) / Ssc * 100).astype(np.float32))
        bs.append(state_bins(Sw, Ssc, edges).astype(np.int8))
    u = np.concatenate(us); r = np.concatenate(rs); bn = np.concatenate(bs)
    cls = np.tile(traffic_class(offset), len(Pc))
    G = np.zeros((len(qs), 3, nb, ND, len(thetas)), np.float32)
    rows = {c: np.where(cls == c)[0] for c in (1, 2)}
    for i, th in enumerate(thetas):
        W = np.minimum(u, np.maximum(np.float32(th), r)) ** 2
        Wb = W.reshape(-1, ND, DEC).sum(2)
        Rb = np.cumsum(Wb[:, ::-1], axis=1)[:, ::-1]
        for c in (1, 2):
            Rc, bc = Rb[rows[c]], bn[rows[c]]
            for d in range(ND):
                col = Rc[:, d]
                allq = np.quantile(col, qs)
                for b in range(nb):
                    m = bc[:, d] == b
                    G[:, c, b, d, i] = (np.quantile(col[m], qs) if m.sum() >= NMIN
                                        else allq)
    # enforce monotonicity in theta (quantile noise) 
    G = np.maximum.accumulate(G, axis=-1)
    return G


class Tables:
    """Tables on a C grid, linear interpolation in C. Cached on disk."""
    def __init__(self, Pc, Qc, Ssc, qs, cgrid, offset=0, cache=None, tag="",
                 edges=BIN_EDGES):
        self.qs, self.cgrid, self.offset = list(qs), np.asarray(cgrid, float), offset
        self.edges = edges
        self.T = {}
        for C in self.cgrid:
            f = None
            if cache:
                f = os.path.join(cache, f"tab_{tag}_off{offset}_C{C:.2f}_nb{len(edges)+1}.npy")
            if f and os.path.exists(f):
                G = np.load(f)
            else:
                G = build_table(Pc, Qc, C, Ssc, self.qs, offset, edges=edges)
                if f:
                    np.save(f, G)
            self.T[C] = G

    def get(self, C, iq):
        g = self.cgrid
        C = float(np.clip(C, g[0], g[-1]))
        j = int(np.clip(np.searchsorted(g, C) - 1, 0, len(g) - 2))
        a = (C - g[j]) / (g[j + 1] - g[j])
        return (1 - a) * self.T[g[j]][iq] + a * self.T[g[j + 1]][iq]


class Feat:
    """Per-week causal features used for the table look-up."""
    def __init__(self, Sw, Ssc, offset=0, edges=BIN_EDGES):
        self.cls = traffic_class(offset)
        self.bins = state_bins(Sw, Ssc, edges)


# ---------------------------------------------------------------- controller
def theta_from_table(Gk, B):
    """Largest theta with G <= B (linear interpolation). Gk (nw, nth).
    Returns theta and a 'hopeless' flag (even theta=0 forecast infeasible)."""
    cnt = (Gk <= B[:, None]).sum(1)
    hopeless = cnt == 0
    i = np.clip(cnt - 1, 0, len(THETA) - 2)
    r = np.arange(len(B))
    g0, g1 = Gk[r, i], Gk[r, i + 1]
    a = np.clip((B - g0) / np.maximum(g1 - g0, 1e-9), 0, 1)
    th = THETA[i] + a * (THETA[i + 1] - THETA[i])
    th = np.where(cnt >= len(THETA), TH_TOP, th)
    th = np.where(hopeless, 0.0, th)
    return th, hopeless


def run(Pw, Qw, Sw, C, Ssc, kind, vstar=2.0, G=None, feat=None,
        hopeless_rule="greedy", v_lim=2.0, theta_fixed=None, theta_max=None,
        want_theta=False, stats=None):
    """Run the controller on all windows (vectorised). kind: 'fixed' (law
    (15) with threshold theta_fixed), 'uniform' (no forecast), 'table'.
    Returns sx (NW,K), vuf (NW,K) [, theta (NW,K)]."""
    nw = Pw.shape[0]
    rr = np.arange(nw)
    A = np.zeros(nw)
    sx = np.empty((nw, K)); vuf = np.empty((nw, K))
    th_t = np.empty((nw, K)) if want_theta else None
    Btot = K * vstar ** 2
    theta = np.full(nw, float(theta_fixed if theta_fixed is not None else vstar))
    for k in range(K):
        if k % DEC == 0 and kind != "fixed":
            B = Btot - A
            if kind == "uniform":
                theta = np.sqrt(np.maximum(B, 0.0) / (K - k))
                hl = B < 0
            else:
                theta, hl = theta_from_table(
                    G[feat.cls, feat.bins[:, k // DEC], k // DEC], B)
            if theta_max is not None:
                theta = np.minimum(theta, theta_max)
            if hopeless_rule == "skip_certain":     # window certainly lost
                theta = np.where(A > K * v_lim ** 2, TH_TOP, theta)
            elif hopeless_rule == "skip_forecast":
                theta = np.where(hl, TH_TOP, theta)
        req = np.maximum(0.0, Sw[:, k] - theta * Ssc / 100.0) / 2.0
        s, av, _ = deliver(Pw[:, k], Qw[:, k], Sw[:, k], req, C, Ssc)
        if stats is not None:      # utilisation of the usable rating kappa*C*U
            stats["util_max"] = max(stats.get("util_max", 0.0),
                                    float(np.max(s / np.maximum(av / KAPPA, 1e-9))))
        v = np.abs(Sw[:, k] - 2 * s) / Ssc * 100.0
        A += v * v
        sx[:, k], vuf[:, k] = s, v
        if want_theta:
            th_t[:, k] = theta
    return (sx, vuf, th_t) if want_theta else (sx, vuf)


def oracle(Pw, Qw, Sw, C, Ssc, vstar=2.0, iters=22):
    """Non-causal bound: per-window constant threshold theta_w (perfect
    knowledge of the window) = largest theta with window rms <= v*."""
    def rms_of(th):
        req = np.maximum(0.0, Sw - th[:, None] * Ssc / 100.0) / 2.0
        s, _, _ = deliver(Pw, Qw, Sw, req, C, Ssc)
        v = np.abs(Sw - 2 * s) / Ssc * 100.0
        return np.sqrt((v ** 2).mean(1)), s, v
    nw = Pw.shape[0]
    lo = np.zeros(nw); hi = np.full(nw, TH_TOP)
    r_top = rms_of(hi)[0]; r_0 = rms_of(lo)[0]
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        ok = rms_of(mid)[0] <= vstar
        lo = np.where(ok, mid, lo); hi = np.where(ok, hi, mid)
    th = np.where(r_top <= vstar, TH_TOP, np.where(r_0 > vstar, 0.0, lo))
    _, s, v = rms_of(th)
    return s, v


# ---------------------------------------------------------------- evaluation
def evaluate_run(sx, vuf, C, lim=None):
    """Same metrics as rpc.evaluate on flattened (NW*K) series."""
    lim = GRID["vuf_lim"] if lim is None else lim
    sx = sx.reshape(-1); v = vuf.reshape(-1)
    v10 = rpc.vuf10(v)
    ex = np.maximum(0.0, v10 - lim)
    return dict(C=float(C), p95=rpc.p95(v10), vmax10=float(v10.max()),
                share_above=float(np.mean(v10 > lim + 1e-9)),
                E_viol=float(ex.sum() / 6.0), E_loss=rpc.losses_MWh(sx, C),
                E_transfer=float(sx.sum() / 3600.0), sx_max=float(sx.max()),
                dsx_max=float(np.abs(np.diff(sx)).max()))


def annual_J(ev):
    return rpc.annual_cost(ev)


def week_eval(Pw, Qw, Sw, C, Ssc, **kw):
    if kw.get("kind") == "oracle":
        sx, v = oracle(Pw, Qw, Sw, C, Ssc, vstar=kw.get("vstar", 2.0))
    else:
        sx, v = run(Pw, Qw, Sw, C, Ssc, **kw)
    return evaluate_run(sx, v, C)


def cmin_week(Pw, Qw, Sw, C_lo, C_hi, Ssc, tol=0.02, lim=2.0, **kw):
    """Smallest C with P95(VUF10) <= lim (bisection in [C_lo, C_hi];
    C_hi expanded if needed)."""
    f = lambda C: week_eval(Pw, Qw, Sw, C, Ssc, **kw)["p95"] - lim
    if f(C_lo) <= 0:
        return C_lo
    hi = C_hi
    while f(hi) > 0:
        hi *= 1.15
        if hi > 40:
            return np.nan
    lo = C_lo
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return hi
