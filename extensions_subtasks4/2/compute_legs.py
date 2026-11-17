"""Step 2 of WORKFLOW: per-second Scott-leg and RPC-leg powers, voltages and currents
for the 60 high-speed design weeks at C = 11.27 MVA/leg, eps_u = 1.0 %, Ssc = 750 MVA,
exact phasor model (same equations as rpc_sizing/network.py, fixed-point, 12 iterations).
Only nonzero-load seconds are solved; zero-load seconds are stored as 0.
usage: python compute_legs.py [week ...]   (default: all 60)
"""
import sys, os, time
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing.network import solve, M, E, A, _z
from rpc_sizing.params import GRID, RPC

C = 11.27; EPS = 1.0; SSC = 750.0; S_B = 100.0
UKV = 27.5                      # kV, secondary base (1 pu)
SR40, SR20 = 40.0, 20.0         # Scott leg ratings considered, MVA
NITER = 12
OUT = "/home/claude/subtasks4/2/data"
BASE = "/home/claude/code/results/base_w%03d.npz"


def solve_full(Sa, Sb, Ssc=SSC, n_iter=NITER, S_b=S_B):
    """Same equations as network.solve; returns converged feeder voltages and
    currents (pu, base S_b / 27.5 kV) and the final fixed-point residual."""
    Zs = _z(S_b / Ssc, 10.0)
    zT = _z(GRID["uk"] * S_b / GRID["trafo_leg_MVA"], 30.0)
    sa = np.asarray(Sa, complex) / S_b
    sb = np.asarray(Sb, complex) / S_b
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
        U = E[None, :] - Zs * Iph
        Ia, Ib = Ia_new, Ib_new
    # consistent final evaluation
    u = U @ M.T
    ua = u[:, 0] - zT * Ia
    ub = u[:, 1] - zT * Ib
    res = np.maximum(np.abs(np.conj(sa / ua) - Ia), np.abs(np.conj(sb / ub) - Ib))
    U1 = (U[:, 0] + A * U[:, 1] + A ** 2 * U[:, 2]) / 3
    U2 = (U[:, 0] + A ** 2 * U[:, 1] + A * U[:, 2]) / 3
    vuf = np.abs(U2) / np.abs(U1) * 100.0
    return ua, ub, Ia, Ib, vuf, res


def week(k, n_iter=NITER, losses_in_network=False):
    d = np.load(BASE % k)
    P = d["P"].astype(float); Q = d["Q"].astype(float)
    N = len(P)
    S = P + 1j * Q
    mag = np.abs(S)
    sx, _ = rpc.compensate(P, Q, C, EPS, SSC)
    sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0)
    nz = mag > 0
    # converter loss model of rpc.py, per leg (MW); both legs' losses are drawn through leg beta
    ploss_leg = RPC["k0"] * C + RPC["k1"] * sx + RPC["k2"] * sx ** 2 / C
    ploss_tot = 2 * ploss_leg
    Sa = S - sxv
    Sb = sxv + (ploss_tot if losses_in_network else 0.0)
    out = {k: np.zeros(N, np.float32) for k in
           ["P_L", "Q_L", "P_alpha", "Q_alpha", "P_beta", "Q_beta", "U_alpha", "U_beta", "vuf",
            "S_alpha", "S_beta", "I_alpha_A", "I_beta_A",
            "I_alpha_pu40", "I_beta_pu40", "I_alpha_pu20", "I_beta_pu20",
            "sx_abs", "ploss_tot_MW", "I_rpc_alpha_A", "I_rpc_beta_A", "I_rpc_alpha_pu", "I_rpc_beta_pu",
            "I_rpc_beta_pu_ownloss", "S_conv_beta"]}
    ua, ub, Ia, Ib, vuf, res = solve_full(Sa[nz], Sb[nz], n_iter=n_iter)
    Ua, Ub = np.abs(ua), np.abs(ub)
    # Scott legs: S at the feeder terminals (drawn from the leg), I = |S|/(U 27.5 kV)
    Smag_a = np.abs(Sa[nz]); Smag_b = np.abs(Sb[nz])
    I_a = Smag_a / Ua / UKV * 1e3          # A  (MVA/kV = kA -> *1e3)
    I_b = Smag_b / Ub / UKV * 1e3
    # RPC: alpha converter current = |s_x|/U_alpha ; beta converter apparent power includes losses
    Sconv_b = sxv[nz] + ploss_tot[nz]
    Sconv_b_own = sxv[nz] + ploss_leg[nz]
    Ira = np.abs(sxv[nz]) / Ua
    Irb = np.abs(Sconv_b) / Ub
    Irb_own = np.abs(Sconv_b_own) / Ub
    f = lambda a: a.astype(np.float32)
    o = out
    o["P_L"][nz] = f(P[nz]); o["Q_L"][nz] = f(Q[nz])
    o["P_alpha"][nz] = f(Sa[nz].real); o["Q_alpha"][nz] = f(Sa[nz].imag)
    o["P_beta"][nz] = f(Sb[nz].real); o["Q_beta"][nz] = f(Sb[nz].imag)
    o["U_alpha"][nz] = f(Ua); o["U_beta"][nz] = f(Ub); o["vuf"][nz] = f(vuf)
    o["S_alpha"][nz] = f(Smag_a); o["S_beta"][nz] = f(Smag_b)
    o["I_alpha_A"][nz] = f(I_a); o["I_beta_A"][nz] = f(I_b)
    o["I_alpha_pu40"][nz] = f(I_a / (SR40 / UKV * 1e3)); o["I_beta_pu40"][nz] = f(I_b / (SR40 / UKV * 1e3))
    o["I_alpha_pu20"][nz] = f(I_a / (SR20 / UKV * 1e3)); o["I_beta_pu20"][nz] = f(I_b / (SR20 / UKV * 1e3))
    o["sx_abs"][nz] = f(sx[nz]); o["ploss_tot_MW"][nz] = f(ploss_tot[nz])
    # current in A of the RPC legs at 27.5 kV (rated current C/27.5 kV)
    o["I_rpc_alpha_A"][nz] = f(np.abs(sxv[nz]) / Ua / UKV * 1e3)
    o["I_rpc_beta_A"][nz] = f(np.abs(Sconv_b) / Ub / UKV * 1e3)
    o["I_rpc_alpha_pu"][nz] = f(Ira / C); o["I_rpc_beta_pu"][nz] = f(Irb / C)
    o["I_rpc_beta_pu_ownloss"][nz] = f(Irb_own / C)
    o["S_conv_beta"][nz] = f(np.abs(Sconv_b))
    return out, float(res.max()), int(nz.sum())


if __name__ == "__main__":
    ks = [int(a) for a in sys.argv[1:]] or list(range(60))
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    for k in ks:
        out, rmax, nnz = week(k)
        np.savez_compressed(f"{OUT}/legs_w{k:03d}.npz", **out)
        print(f"w{k:03d} nz={nnz} res_max={rmax:.2e} maxSa={out['S_alpha'].max():.2f} "
              f"maxIpu40={out['I_alpha_pu40'].max():.3f} t={time.time()-t0:.0f}s", flush=True)
