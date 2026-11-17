"""Model switch for sub-task 4.5: model 'v7' = capacity limit of rpc.compensate (approximate busbar voltage U),
model 'cons' = consistent capacity limit with the EXACT feeder-terminal voltage (agent 1, checks_d.py):
    s_x = min(req, KAPPA*C*min(|u_alpha|,|u_beta|,1)),  req = max(0,|S_L|-eps*Ssc)/2,
|u| from the exact phasor model with the transfer applied; start from the code's own limit, 3 fixed-point passes,
then the final solve for the VUF."""
from common5 import *
from fastsolve2 import solve_fast2
from rpc_sizing.rpc import KAPPA

NPASS = 3


def u2_model(P, Q, C, eps, model="v7"):
    """complex negative-sequence ratio (%), exact VUF magnitude, per-leg transfer (complex)."""
    S = P + 1j * Q
    mag = np.abs(S)
    m = mag > 0
    if C > 0:
        sx, _ = rpc.compensate(P, Q, C, eps, SSC)
        if model == "cons":
            req = np.maximum(0.0, mag - eps / 100.0 * SSC) / 2.0
            for _ in range(NPASS):
                sxv = np.where(m, sx * S / np.maximum(mag, 1e-9), 0)
                ua = np.ones(len(S)); ub = np.ones(len(S))
                _, _, ua[m], ub[m] = solve_fast2(S[m] - sxv[m], sxv[m], SSC)
                sx = np.minimum(req, KAPPA * C * np.minimum(np.minimum(ua, ub), 1.0))
        sxv = np.where(m, sx * S / np.maximum(mag, 1e-9), 0)
    else:
        sxv = np.zeros_like(S)
    u2 = np.zeros(len(S), complex); vm = np.zeros(len(S))
    r, vv, _, _ = solve_fast2(S[m] - sxv[m], sxv[m], SSC)
    u2[m] = 100.0 * r; vm[m] = vv
    return u2, vm, sxv


def p95_model(P, Q, C, eps, model="v7"):
    return rpc.p95(rpc.vuf10(u2_model(P, Q, C, eps, model)[1]))


def evaluate_model(P, Q, C, eps, model="v7"):
    _, v, sxv = u2_model(P, Q, C, eps, model)
    sx = np.abs(sxv)
    v10 = rpc.vuf10(v)
    return dict(C=float(C), eps=float(eps), p95=rpc.p95(v10),
                p99=float(np.quantile(v10, 0.99, method="inverted_cdf")),
                vmax=float(v10.max()), share=float(np.mean(v10 > LIM + 1e-9)),
                E_viol=float(np.maximum(0, v10 - LIM).sum() / 6), E_loss=rpc.losses_MWh(sx, C),
                E_tr=float(sx.sum() / 3600),
                sx_max=float(sx.max()))


def cmin_model(P, Q, eps, model="v7", tol=0.02, guess=None):
    """bisection for the smallest C with P95 <= LIM; warm start with a bracket around `guess` (e.g. the v7-model value)."""
    f = lambda C: p95_model(P, Q, C, eps, model) - LIM
    if f(0.0) <= 0:
        return 0.0
    hi = float(np.hypot(P, Q).max()) / 2 * 1.1 + 0.1
    lo = 0.0
    if guess is not None and guess > 0:
        for c in (guess * 0.98, guess, guess * 1.03, guess * 1.08, guess * 1.2):
            if f(c) <= 0:
                hi = c
                break
            lo = max(lo, c)
    else:
        if f(hi) > 0:
            return float("nan")
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return hi
