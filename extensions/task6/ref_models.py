"""Python reference computations for the Simulink validation package.

Everything here is computed from /home/claude/code/rpc_sizing (read-only).
Three groups of references:
  * eq. (7)-(8) of the paper (analytic)
  * exact fundamental-frequency phasor model, two load models:
        'CP'  constant power  (rpc_sizing.network.solve, the model of the paper)
        'CZ'  constant impedance at nominal feeder voltage 1 pu = 27.5 kV
              (what a Simulink 'Series RLC Load' does)
  * averaged RPC dynamic model rpc_sizing.dynamics.simulate (case C)
"""
import sys, os, json
import numpy as np

CODE = "/home/claude/code"
if CODE not in sys.path:
    sys.path.insert(0, CODE)
from rpc_sizing import network as _net                      # noqa: E402
from rpc_sizing.network import M, E, A, _z                   # noqa: E402
from rpc_sizing.params import GRID, RPC                      # noqa: E402
from rpc_sizing import rpc as _rpc, dynamics as _dyn         # noqa: E402

S_B = 100.0                    # MVA base used inside network.solve
V_PRIM_KV = 110.0              # line-to-line, PCC
V_SEC_KV = 27.5                # no-load secondary voltage of each leg
XR_SRC = 10.0
XR_LEG = 30.0
F_HZ = 50.0

# ----------------------------------------------------------------------------
# case definitions (single source of truth, exported to JSON for MATLAB)
# ----------------------------------------------------------------------------
P_ALPHA_MW = 8.0               # reproduces Table 5 of the paper: 8 MW / 0.95 -> 8.42 MVA
COSPHI_ALPHA = 0.95
SSC_LIST = (500.0, 1000.0)
K_LIST = (0.0, 0.5, 1.0)
DPHI_LIST = (0.0, 20.0)

SL_B_MVA = 18.5                # case B load
COSPHI_B = 0.89
SSC_B = 500.0
LIM_PCT = 2.0
PAPER_B = dict(vuf_sim_pct=2.04, vuf_analytic_pct=2.00, rating_MVA=4.24)  # Table 6 of the paper


def cases_A():
    out = []
    phia = np.degrees(np.arccos(COSPHI_ALPHA))
    Sa = P_ALPHA_MW / COSPHI_ALPHA
    for ssc in SSC_LIST:
        for dphi in DPHI_LIST:
            for k in K_LIST:
                if k == 0.0 and dphi != 0.0:
                    continue                       # duplicate of (k=0, dphi=0)
                out.append(dict(id=f"A_Ssc{int(ssc)}_k{k:.1f}_dphi{int(dphi)}",
                                Ssc_MVA=ssc, k=k, dphi_deg=dphi,
                                Sa_MVA=Sa, phia_deg=phia,
                                Sb_MVA=k * Sa, phib_deg=phia - dphi))
    return out


def _Sc(mag, ang_deg):
    return mag * np.exp(1j * np.radians(ang_deg))


def case_A_loads(c):
    return _Sc(c["Sa_MVA"], c["phia_deg"]), _Sc(c["Sb_MVA"], c["phib_deg"])


def cases_B():
    """Ideal RPC transfer for one load S_L on feeder alpha, Ssc=500 MVA.
    alpha leg injects s_x into feeder alpha, beta leg draws s_x from feeder beta."""
    SL = _Sc(SL_B_MVA, np.degrees(np.arccos(COSPHI_B)))
    ssc = SSC_B
    c11 = max(0.0, abs(SL) - LIM_PCT / 100 * ssc) / 2.0           # eq. (11)
    sx_list = [
        ("B1_none", "No compensation", 0.0 + 0j),
        ("B2_Ponly", "Active power transfer only (P limited to 2 %)", max(0.0, (SL.real - LIM_PCT / 100 * ssc) / 2.0) + 0j),
        ("B3_eq11", "Compensation along S_L, eq. (11)", c11 / abs(SL) * SL),
        ("B4_full", "Full compensation", SL / 2.0),
    ]
    out = []
    for cid, label, sx in sx_list:
        out.append(dict(id=cid, label=label, Ssc_MVA=ssc,
                        SL_MVA=abs(SL), SL_P_MW=SL.real, SL_Q_Mvar=SL.imag,
                        rating_MVA=abs(sx), sx_P_MW=sx.real, sx_Q_Mvar=sx.imag,
                        Sa_P_MW=(SL - sx).real, Sa_Q_Mvar=(SL - sx).imag,
                        Sb_P_MW=sx.real, Sb_Q_Mvar=sx.imag))
    return out


def case_B_loads(c):
    return complex(c["Sa_P_MW"], c["Sa_Q_Mvar"]), complex(c["Sb_P_MW"], c["Sb_Q_Mvar"])


# ----------------------------------------------------------------------------
# analytic expressions (7), (8)
# ----------------------------------------------------------------------------
def iuf_eq7(Sa, Sb):
    """(7) with complex feeder powers: IUF = |S_a* ... |; k e^{j dphi} = S_b / S_a-type
    ratio of the CURRENTS referred to the feeder voltages.  For constant feeder
    voltage magnitude, I_x = conj(S_x)/U, so k e^{j dphi} = conj(S_b)/conj(S_a)
    with dphi = phi_a - phi_b."""
    r = np.conj(Sb) / np.conj(Sa) if abs(Sa) > 0 else np.inf
    return abs(1 - r) / abs(1 + r) * 100.0


def vuf_eq8(Sa, Sb, Ssc):
    return abs(Sa - Sb) / Ssc * 100.0


# ----------------------------------------------------------------------------
# exact phasor models, returning VUF and IUF
# ----------------------------------------------------------------------------
def _seq(x):
    x = np.asarray(x)
    x1 = (x[..., 0] + A * x[..., 1] + A ** 2 * x[..., 2]) / 3
    x2 = (x[..., 0] + A ** 2 * x[..., 1] + A * x[..., 2]) / 3
    return x1, x2


def exact_cp(Sa, Sb, Ssc, n_iter=200, tol=1e-12):
    """Constant-power loads: the algorithm of rpc_sizing.network.solve (same
    equations, many more iterations) returning also the primary currents.
    Powers in MVA (complex)."""
    Zs = _z(S_B / Ssc, XR_SRC)
    zT = _z(GRID["uk"] * S_B / GRID["trafo_leg_MVA"], XR_LEG)
    sa, sb = Sa / S_B, Sb / S_B
    U = E.copy()
    Ia = Ib = 0j
    for _ in range(n_iter):
        u = M @ U
        ua, ub = u[0] - zT * Ia, u[1] - zT * Ib
        Ia_n = np.conj(sa / ua) if abs(sa) > 0 else 0j
        Ib_n = np.conj(sb / ub) if abs(sb) > 0 else 0j
        Iph = 3.0 * (M.T @ np.array([Ia_n, Ib_n]))
        Un = E - Zs * Iph
        err = np.max(np.abs(Un - U))
        U, Ia, Ib = Un, Ia_n, Ib_n
        if err < tol:
            break
    return _pack(U, Iph, ua, ub, Ia, Ib, S_B)


def exact_cz(Sa, Sb, Ssc, Vn_pu=1.0):
    """Constant-impedance loads: Z_x = Vn^2 / conj(S_x) with Vn = 1 pu (27.5 kV)
    (rated power S_x is drawn at Vn).  Linear network, solved directly."""
    Zs = _z(S_B / Ssc, XR_SRC)
    zT = _z(GRID["uk"] * S_B / GRID["trafo_leg_MVA"], XR_LEG)
    ya = np.conj(Sa / S_B) / Vn_pu ** 2
    yb = np.conj(Sb / S_B) / Vn_pu ** 2
    Yp = np.diag([ya / (1 + ya * zT), yb / (1 + yb * zT)])
    Y3 = 3.0 * M.T @ Yp @ M
    U = np.linalg.solve(np.eye(3) + Zs * Y3, E.astype(complex))
    u = M @ U
    Ia = ya / (1 + ya * zT) * u[0]
    Ib = yb / (1 + yb * zT) * u[1]
    Iph = 3.0 * (M.T @ np.array([Ia, Ib]))
    ua, ub = u[0] - zT * Ia, u[1] - zT * Ib
    return _pack(U, Iph, ua, ub, Ia, Ib, S_B)


def exact_ci(Sa, Sb, Ssc):
    """Constant-current loads (ideal controlled current sources, as the converter model
    of Table 6 of the paper): I_x = conj(S_x / u0_x) with u0 the NO-LOAD feeder voltage
    (-j for alpha, 1 for beta); independent of network impedances."""
    Zs = _z(S_B / Ssc, XR_SRC)
    zT = _z(GRID["uk"] * S_B / GRID["trafo_leg_MVA"], XR_LEG)
    u0 = M @ E
    Ia = np.conj(Sa / S_B / u0[0]) if abs(Sa) > 0 else 0j
    Ib = np.conj(Sb / S_B / u0[1]) if abs(Sb) > 0 else 0j
    Iph = 3.0 * (M.T @ np.array([Ia, Ib]))
    U = E - Zs * Iph
    u = M @ U
    return _pack(U, Iph, u[0] - zT * Ia, u[1] - zT * Ib, Ia, Ib, S_B)


EXACT = dict(CP=exact_cp, CZ=exact_cz, CI=exact_ci)


def _pack(U, Iph, ua, ub, Ia, Ib, S_b):
    U1, U2 = _seq(U)
    I1, I2 = _seq(Iph)
    Sa_act = ua * np.conj(Ia) * S_b
    Sb_act = ub * np.conj(Ib) * S_b
    return dict(VUF_pct=abs(U2) / abs(U1) * 100.0, IUF_pct=abs(I2) / abs(I1) * 100.0,
                Sa_act_MVA=complex(Sa_act), Sb_act_MVA=complex(Sb_act),
                Ua_pu=abs(ua), Ub_pu=abs(ub), U1_pu=abs(U1))


def vuf_network_solve(Sa, Sb, Ssc):
    """The production function of the paper (rpc_sizing.network.solve), 12 iterations."""
    v, _ = _net.solve(np.array([Sa]), np.array([Sb]), Ssc)
    return float(v[0])


# ----------------------------------------------------------------------------
# case C: averaged RPC dynamic step (as in dyn_run.py)
# ----------------------------------------------------------------------------
T_STEP = 40.0
STEP_MW = -10.0
SEG_LEN = 61
VBAND_PCT = 1.0                    # settling band (+-1 % of Vdc_ref)


def design_and_segment():
    """Proposed design and load segment exactly as dyn_run.py."""
    cwd = os.getcwd()
    os.chdir(CODE)
    try:
        sys.path.insert(0, CODE)
        from analyse import load, methods
        m = methods(load("base"), 750)["proposed"]
        d = np.load("results/base_w000.npz")
        P = d["P"].astype(float)
        Q = d["Q"].astype(float)
    finally:
        os.chdir(cwd)
    C, eps, Ssc = float(m["C"]), float(m["eps"]), 750.0
    S = np.hypot(P, Q)
    req = np.maximum(0, S - eps / 100 * Ssc) / 2
    i = int(np.argmax(np.abs(np.diff(req))))
    a = max(i - 30, 0)
    return C, eps, Ssc, a, P[a:a + SEG_LEN].copy(), Q[a:a + SEG_LEN].copy()


def initial_state(P, Q, C, eps, Ssc, ff):
    """Steady-state initial condition used inside dynamics.simulate (copied)."""
    k0, k1, k2 = RPC["k0"], RPC["k1"], RPC["k2"]
    pm, qm = P[0], Q[0]
    S0 = np.hypot(pm, qm)
    sx0 = min(max(0.0, S0 - eps / 100.0 * Ssc) / 2.0, _rpc.KAPPA * C)
    Pa = sx0 * pm / S0 if S0 > 0 else 0.0
    Qa = sx0 * qm / S0 if S0 > 0 else 0.0
    ploss0 = 2 * (k0 * C + k1 * sx0 + k2 * sx0 ** 2 / max(C, 1e-6))
    Pb, Qb = Pa + ploss0, Qa
    integ = 0.0 if ff else Pa + ploss0
    return dict(Pa=Pa, Qa=Qa, Pb=Pb, Qb=Qb, integ=integ, pm=pm, qm=qm)


def dynamic_params(C, eps, Ssc):
    H = RPC["H_dc_ms"] * 1e-3
    Vref = RPC["Vdc_ref"]
    Cdc = 2.0 * H * C * 1e6 / Vref ** 2
    w = 2 * np.pi * RPC["f_dc"]
    from rpc_sizing.params import feeder_rx
    r, x = feeder_rx(Ssc)
    return dict(C=C, eps_pct=eps, Ssc_MVA=Ssc, KAPPA=_rpc.KAPPA, k0=RPC["k0"], k1=RPC["k1"],
                k2=RPC["k2"], Vref=Vref, H_s=H, Cdc_F=Cdc, Wref_MJ=0.5 * Cdc * Vref ** 2 / 1e6,
                Kp=2 * 0.7 * w, Ki=w ** 2, tau_i_s=RPC["tau_i"], tau_m_s=1.0 / (2 * np.pi * 50.0),
                r_pu_per_MVA=r, x_pu_per_MVA=x)


def settling_time(t, Vdc, Vref, t_step=T_STEP, band_pct=VBAND_PCT):
    """Time after the step at which |Vdc-Vref| leaves the band for the last time (0 if never)."""
    t = np.asarray(t); Vdc = np.asarray(Vdc)
    m = t >= t_step
    out = np.abs(Vdc[m] - Vref) > band_pct / 100 * Vref
    if not out.any():
        return 0.0
    return float(t[m][np.where(out)[0][-1]] - t_step)


def metrics_from_series(t, Vdc, Ia, Ib, Vref=None):
    Vref = RPC["Vdc_ref"] if Vref is None else Vref
    return dict(Vdc_min_V=float(np.min(Vdc)), Vdc_max_V=float(np.max(Vdc)),
                Vdc_dev_max_pct=float(np.max(np.abs(np.asarray(Vdc) - Vref)) / Vref * 100),
                Ia_max_pu=float(np.max(Ia)), Ib_max_pu=float(np.max(Ib)),
                settle_s=settling_time(t, Vdc, Vref))


def run_caseC(ff, dt=2e-4, decim=10):
    C, eps, Ssc, a, P, Q = design_and_segment()
    o = _dyn.simulate(P, Q, C, eps, Ssc, t_step=T_STEP, step_MW=STEP_MW, ff=ff, dt=dt)
    m = metrics_from_series(o["t"], o["Vdc"], o["Ia"], o["Ib"])
    return dict(metrics=m, t=o["t"][::decim], Vdc=o["Vdc"][::decim], Ia=o["Ia"][::decim],
                Ib=o["Ib"][::decim], Pa=o["Pa"][::decim], Pb=o["Pb"][::decim], Cdc_mF=o["Cdc_mF"])


# ----------------------------------------------------------------------------
# continuous-time right-hand side of the averaged model (mirrors matlab/rpc_avg_rhs.m)
# state x = [W_MJ, Pa, Qa, Pb, Qb, integ, pm, qm]
# ----------------------------------------------------------------------------
def rhs_cont(x, PL, QL, p, ff):
    W, Pa, Qa, Pb, Qb, integ, pm, qm = x
    C = p["C"]
    S = np.hypot(pm, qm)
    req = max(0.0, S - p["eps_pct"] / 100.0 * p["Ssc_MVA"]) / 2.0
    U = 1.0 - (p["r_pu_per_MVA"] * (PL - Pa) + p["x_pu_per_MVA"] * (QL - Qa))
    lim = C * min(U, 1.0)
    sx = min(req, p["KAPPA"] * lim)
    if S > 1e-9:
        Pref, Qref = sx * pm / S, sx * qm / S
    else:
        Pref = Qref = 0.0
    ploss = 2.0 * (p["k0"] * C + p["k1"] * np.hypot(Pa, Qa)
                   + p["k2"] * (Pa ** 2 + Qa ** 2) / max(C, 1e-6))
    e = p["Wref_MJ"] - W
    dinteg = p["Ki"] * e
    if (integ >= lim and dinteg > 0) or (integ <= -lim and dinteg < 0):
        dinteg = 0.0
    Pb_ref = (Pref + ploss if ff else 0.0) + p["Kp"] * e + integ
    Pb_ref = min(max(Pb_ref, -lim), lim)
    qmax = np.sqrt(max(lim ** 2 - Pb_ref ** 2, 0.0))
    Qb_ref = min(max(Qref, -qmax), qmax)
    tau = p["tau_i_s"]
    return np.array([Pb - Pa - ploss,
                     (Pref - Pa) / tau, (Qref - Qa) / tau,
                     (Pb_ref - Pb) / tau, (Qb_ref - Qb) / tau,
                     dinteg,
                     (PL - pm) / p["tau_m_s"], (QL - qm) / p["tau_m_s"]])


def outputs_cont(x, PL, QL, p):
    W, Pa, Qa, Pb, Qb = x[:5]
    Vdc = np.sqrt(max(2.0 * W * 1e6 / p["Cdc_F"], 0.0))
    U = 1.0 - (p["r_pu_per_MVA"] * (PL - Pa) + p["x_pu_per_MVA"] * (QL - Qa))
    Ia = np.hypot(Pa, Qa) / max(U, 1e-3) / max(p["C"], 1e-6)
    Ib = np.hypot(Pb, Qb) / 1.0 / max(p["C"], 1e-6)
    return Vdc, Ia, Ib


def run_caseC_continuous(ff, rtol=1e-8, atol=1e-9, max_step=2e-3, tgrid_dt=2e-3):
    from scipy.integrate import solve_ivp
    C, eps, Ssc, a, P, Q = design_and_segment()
    p = dynamic_params(C, eps, Ssc)
    ic = initial_state(P, Q, C, eps, Ssc, ff)
    x0 = np.array([p["Wref_MJ"], ic["Pa"], ic["Qa"], ic["Pb"], ic["Qb"], ic["integ"], ic["pm"], ic["qm"]])
    tt = np.arange(len(P), dtype=float)

    def f(t, x):
        PL = np.interp(t, tt, P) + (STEP_MW if t >= T_STEP else 0.0)
        QL = np.interp(t, tt, Q)
        return rhs_cont(x, PL, QL, p, ff)

    T = float(len(P) - 1)
    tev = np.arange(0.0, T, tgrid_dt)
    # integrate in pieces so that the step discontinuity at T_STEP is a break point
    sols = []
    x = x0
    pieces = [(0.0, T_STEP), (T_STEP, T)]
    for (t0, t1) in pieces:
        te = tev[(tev >= t0) & (tev < t1)]
        s = solve_ivp(f, (t0, t1), x, method="RK45", rtol=rtol, atol=atol, max_step=max_step,
                      t_eval=te if t1 < T else np.append(te, t1))
        sols.append(s)
        x = s.y[:, -1]
    t = np.concatenate([s.t for s in sols]); Y = np.concatenate([s.y for s in sols], axis=1)
    PLv = np.interp(t, tt, P) + np.where(t >= T_STEP, STEP_MW, 0.0)
    QLv = np.interp(t, tt, Q)
    out = np.array([outputs_cont(Y[:, i], PLv[i], QLv[i], p) for i in range(len(t))])
    return dict(t=t, Vdc=out[:, 0], Ia=out[:, 1], Ib=out[:, 2], Pa=Y[1], Pb=Y[3], integ=Y[5],
                params=p, x0=x0, P=P, Q=Q)
