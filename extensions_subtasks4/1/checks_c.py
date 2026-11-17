"""Busbar voltage used by the capacity limit (approximate, one fixed-point step with feeder-alpha r,x) vs |u_alpha|, |u_beta| of the exact model."""
import sys, json
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *
out = []
for k in (0, 17, 43):
    P, Q = load_week("base", k)
    C, eps = 11.2706, 1.0
    S = P + 1j * Q; mag = np.abs(S)
    sx, _ = rpc.compensate(P, Q, C, eps, SSC)
    frac = np.where(mag > 0, np.minimum(np.maximum(0.0, mag - eps / 100 * SSC) / 2, C) / np.maximum(mag, 1e-9), 0)
    U_appr = rpc.busbar_voltage(P * (1 - frac), Q * (1 - frac), SSC)       # what compensate() uses for the limit
    sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
    m = (mag > 0) & (sx > 0.5)                                              # samples where the converter is active
    _, (ua, ub) = solve(S[m] - sxv[m], sxv[m], SSC, n_iter=10, tol=1e-6)
    ua, ub = np.abs(ua), np.abs(ub)
    r = dict(k=k, n_active=int(m.sum()), U_approx_min=float(U_appr[m].min()), U_approx_mean=float(U_appr[m].mean()),
             exact_alpha_min=float(ua.min()), exact_alpha_mean=float(ua.mean()), exact_beta_min=float(ub.min()), exact_beta_mean=float(ub.mean()),
             diff_alpha_minus_approx_mean=float((ua - U_appr[m]).mean()), diff_alpha_minus_approx_min=float((ua - U_appr[m]).min()),
             diff_alpha_minus_approx_max=float((ua - U_appr[m]).max()),
             frac_time_limit_by_C=float(np.mean(sx[m] >= 0.96 * C * np.minimum(U_appr[m], 1) - 1e-9)))
    print(r, flush=True); out.append(r)
json.dump(out, open(OUT + "/data/checks_c.json", "w"), indent=1)
