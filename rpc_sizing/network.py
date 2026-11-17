"""Exact fundamental-frequency phasor model of a Scott substation on a
three-phase source with impedance, used to check the approximation (8).

Per unit: three-phase base S_b, phase-voltage base; three-phase power
S = (1/3) sum_ph U_ph conj(I_ph). The ideal Scott transformer maps the
primary phase voltages U = [U_A, U_B, U_C] to the secondary voltages
    u = M U,  M = [[0, 1/sqrt3, -1/sqrt3], [2/3, -1/3, -1/3]],
so that u_alpha = -j and u_beta = 1 for a balanced source (beta leads alpha
by 90 deg). Power conservation gives the primary currents I_ph = 3 M^T I_s.
Each leg has the leakage impedance z_T (40 MVA, uk = 10.5 %, X/R = 30);
the source has Z_s = S_b/S_sc (X/R = 10). Loads are constant power at the
feeder terminals. The nonlinear equations are solved by fixed-point
iteration, vectorised over time.
"""
import numpy as np
from .params import GRID

A = np.exp(2j * np.pi / 3)
M = np.array([[0.0, 1 / np.sqrt(3), -1 / np.sqrt(3)],
              [2 / 3, -1 / 3, -1 / 3]])
E = np.array([1.0, A ** 2, A])          # balanced source, phase sequence A-B-C


def _z(mag, xr):
    return mag * (1 + 1j * xr) / np.sqrt(1 + xr ** 2)


def solve(S_alpha, S_beta, Ssc, S_b=100.0, n_iter=12, tol=1e-7):
    """S_alpha, S_beta: complex power arrays (MVA) drawn at the feeders.
    Returns the exact VUF (%) at the PCC and the feeder voltages (pu)."""
    Zs = _z(S_b / Ssc, 10.0)
    zT = _z(GRID["uk"] * S_b / GRID["trafo_leg_MVA"], 30.0)
    sa = np.asarray(S_alpha, complex) / S_b
    sb = np.asarray(S_beta, complex) / S_b
    n = sa.size
    U = np.tile(E, (n, 1))                       # primary phase voltages
    Ia = np.zeros(n, complex); Ib = np.zeros(n, complex)
    for _ in range(n_iter):
        u = U @ M.T                              # n x 2 secondary EMFs
        ua = u[:, 0] - zT * Ia
        ub = u[:, 1] - zT * Ib
        Ia_new = np.conj(sa / ua)
        Ib_new = np.conj(sb / ub)
        Iph = 3.0 * np.stack([Ia_new, Ib_new], axis=1) @ M   # n x 3
        U_new = E[None, :] - Zs * Iph
        err = np.max(np.abs(U_new - U))
        U, Ia, Ib = U_new, Ia_new, Ib_new
        if err < tol:
            break
    U1 = (U[:, 0] + A * U[:, 1] + A ** 2 * U[:, 2]) / 3
    U2 = (U[:, 0] + A ** 2 * U[:, 1] + A * U[:, 2]) / 3
    return np.abs(U2) / np.abs(U1) * 100.0, (ua, ub)
