"""Phase of the substation negative-sequence voltage of a Scott transformer.

Derivation (ideal Scott transformer, balanced source behind Z_s, voltages in pu):
  u_alpha = -j, u_beta = 1  ->  I_alpha = -j conj(S_alpha), I_beta = conj(S_beta)
  primary currents I_ph = 3 M^T I_s ; negative-sequence current
  I_2 = (I_A + a^2 I_B + a I_C)/3 = I_beta - j I_alpha = -conj(S_alpha - S_beta)
  U_2 = -Z_s I_2  ->  U_2/U_1 ~ e^{j theta_s} conj(S_alpha - S_beta)/S_sc ,
  theta_s = atan(X/R) of the source (X/R = 10 -> 84.29 deg).
This script checks the closed form against the exact phasor model of
/home/claude/code/rpc_sizing/network.py (copied here, returning complex U2/U1).
Read-only use of the authors' code: it is imported by path, not modified.
"""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import network as nw
from rpc_sizing.params import GRID

def solve_complex(S_alpha, S_beta, Ssc, S_b=100.0, n_iter=40, tol=1e-10):
    A, M, E, _z = nw.A, nw.M, nw.E, nw._z
    Zs = _z(S_b / Ssc, 10.0)
    zT = _z(GRID["uk"] * S_b / GRID["trafo_leg_MVA"], 30.0)
    sa = np.asarray(S_alpha, complex) / S_b
    sb = np.asarray(S_beta, complex) / S_b
    n = sa.size
    U = np.tile(E, (n, 1)); Ia = np.zeros(n, complex); Ib = np.zeros(n, complex)
    for _ in range(n_iter):
        u = U @ M.T
        ua = u[:, 0] - zT * Ia; ub = u[:, 1] - zT * Ib
        Ia_n = np.conj(sa / ua); Ib_n = np.conj(sb / ub)
        Iph = 3.0 * np.stack([Ia_n, Ib_n], axis=1) @ M
        U_n = E[None, :] - Zs * Iph
        err = np.max(np.abs(U_n - U)); U, Ia, Ib = U_n, Ia_n, Ib_n
        if err < tol: break
    U1 = (U[:, 0] + A * U[:, 1] + A ** 2 * U[:, 2]) / 3
    U2 = (U[:, 0] + A ** 2 * U[:, 1] + A * U[:, 2]) / 3
    return U2 / U1

theta_s = np.arctan(10.0)
out = []
for Ssc in (500.0, 750.0, 1500.0):
    for Sa, Sb in [(8 + 0.5j, 0), (8 + 0.5j, 2 + 0.5j), (-6 + 1j, 0), (30 + 3j, 0),
                   (25 + 12j, 5 + 2j), (0, 10 + 2j), (6 - 3j, 0)]:
        ex = solve_complex([Sa], [Sb], Ssc)[0]
        ap = np.exp(1j * theta_s) * np.conj(Sa - Sb) / Ssc
        out.append(dict(Ssc=Ssc, S_alpha=str(Sa), S_beta=str(Sb),
                        exact_mag_pct=abs(ex) * 100, approx_mag_pct=abs(ap) * 100,
                        exact_arg_deg=float(np.degrees(np.angle(ex))),
                        approx_arg_deg=float(np.degrees(np.angle(ap))),
                        mag_ratio=abs(ex) / abs(ap),
                        arg_diff_deg=float(np.degrees(np.angle(ex / ap)))))
for r in out:
    print(f"Ssc={r['Ssc']:6.0f} Sa={r['S_alpha']:>12s} Sb={r['S_beta']:>10s} "
          f"|U2| ex/ap = {r['exact_mag_pct']:.3f}/{r['approx_mag_pct']:.3f} %  "
          f"arg ex/ap = {r['exact_arg_deg']:.1f}/{r['approx_arg_deg']:.1f} deg  dphi={r['arg_diff_deg']:.2f}")
res = dict(theta_s_deg=float(np.degrees(theta_s)), formula="U2/U1 = exp(j*atan(X/R)) * conj(S_alpha - S_beta)/S_sc",
           max_abs_arg_diff_deg=float(max(abs(r["arg_diff_deg"]) for r in out)),
           mag_ratio_range=[min(r["mag_ratio"] for r in out), max(r["mag_ratio"] for r in out)],
           cases=out)
json.dump(res, open("/home/claude/subtasks3/3/scott_phase_check.json", "w"), indent=1)
print("max |arg diff| deg", res["max_abs_arg_diff_deg"], "mag ratio range", res["mag_ratio_range"])
