"""Averaged (switching-cycle-averaged) dynamic model of the back-to-back RPC.

States: DC-link energy W = C_dc V_dc^2 / 2, the alpha-leg and beta-leg
active/reactive powers (first-order closed current loops, time constant
tau_i) and the integrator of the DC-energy PI controller.

    dW/dt      = P_beta - P_alpha - P_loss
    P_alpha    -> P_x,ref          (alpha leg injects into feeder alpha)
    P_beta     -> P_x,ref + P_loss,est + PI(W_ref - W)   (beta leg regulates V_dc)
    |S_leg|    <= C U_pu           (rated current at the busbar voltage)

The model neglects switching ripple, the 2f DC-link ripple of single-phase
legs and filter dynamics; it is used to check the DC-link voltage band and
the current limit for the load trajectories of the Monte Carlo study.
"""
import numpy as np
from .params import RPC
from .rpc import busbar_voltage, KAPPA


def simulate(P_L, Q_L, C, eps_u, Ssc, t_step=None, step_MW=0.0,
             dt=2e-4, f_meas=50.0, H_ms=None, ff=True):
    """P_L, Q_L: 1 s samples (MW, Mvar). Returns a dict of time series."""
    H = (RPC["H_dc_ms"] if H_ms is None else H_ms) * 1e-3
    Vref = RPC["Vdc_ref"]
    Cdc = 2.0 * H * C * 1e6 / Vref ** 2 if C > 0 else 1e-3
    Wref = 0.5 * Cdc * Vref ** 2
    w = 2 * np.pi * RPC["f_dc"]
    Kp, Ki = 2 * 0.7 * w, w ** 2
    tau = RPC["tau_i"]
    k0, k1, k2 = RPC["k0"], RPC["k1"], RPC["k2"]
    T = len(P_L) - 1
    n = int(T / dt)
    t = np.arange(n) * dt
    PL = np.interp(t, np.arange(len(P_L)), P_L)
    QL = np.interp(t, np.arange(len(Q_L)), Q_L)
    if t_step is not None:
        PL = PL + np.where(t >= t_step, step_MW, 0.0)
    # measurement filter (one-cycle averaging approximated by first order)
    a_m = dt / (dt + 1.0 / (2 * np.pi * f_meas))
    W = Wref
    pm, qm = PL[0], QL[0]
    # initial steady state
    S0 = np.hypot(pm, qm)
    sx0 = min(max(0.0, S0 - eps_u / 100.0 * Ssc) / 2.0, KAPPA * C)
    Pa = sx0 * pm / S0 if S0 > 0 else 0.0
    Qa = sx0 * qm / S0 if S0 > 0 else 0.0
    ploss0 = 2 * (k0 * C + k1 * sx0 + k2 * sx0 ** 2 / max(C, 1e-6))
    Pb, Qb = Pa + ploss0, Qa
    integ = 0.0 if ff else Pa + ploss0
    out = {k: np.empty(n) for k in ("Vdc", "Pa", "Qa", "Pb", "Qb", "Ia", "Ib",
                                     "PL", "QL", "sx_ref")}
    for i in range(n):
        pm += a_m * (PL[i] - pm)
        qm += a_m * (QL[i] - qm)
        S = np.hypot(pm, qm)
        req = max(0.0, S - eps_u / 100.0 * Ssc) / 2.0
        U = busbar_voltage(PL[i] - Pa, QL[i] - Qa, Ssc)
        lim = C * min(U, 1.0)
        sx = min(req, KAPPA * lim)
        if S > 1e-9:
            Pref, Qref = sx * pm / S, sx * qm / S
        else:
            Pref = Qref = 0.0
        ploss = 2 * (k0 * C + k1 * np.hypot(Pa, Qa) + k2 * (Pa ** 2 + Qa ** 2) / max(C, 1e-6))
        e = (Wref - W) / 1e6                  # MJ
        integ += Ki * e * dt
        Pb_ref = (Pref + ploss if ff else 0.0) + Kp * e + integ
        Qb_ref = Qref
        # current limit of the beta leg: active power has priority
        Pb_ref = float(np.clip(Pb_ref, -lim, lim))
        qmax = np.sqrt(max(lim ** 2 - Pb_ref ** 2, 0.0))
        Qb_ref = float(np.clip(Qb_ref, -qmax, qmax))
        if abs(integ) > lim:                  # anti-windup
            integ = np.sign(integ) * lim
        Pa += dt / tau * (Pref - Pa)
        Qa += dt / tau * (Qref - Qa)
        Pb += dt / tau * (Pb_ref - Pb)
        Qb += dt / tau * (Qb_ref - Qb)
        W += (Pb - Pa - ploss) * 1e6 * dt
        Vdc = np.sqrt(max(2 * W / Cdc, 0.0))
        Ub = 1.0  # beta busbar lightly loaded
        out["Vdc"][i] = Vdc
        out["Pa"][i], out["Qa"][i], out["Pb"][i], out["Qb"][i] = Pa, Qa, Pb, Qb
        out["Ia"][i] = np.hypot(Pa, Qa) / max(U, 1e-3) / max(C, 1e-6)
        out["Ib"][i] = np.hypot(Pb, Qb) / Ub / max(C, 1e-6)
        out["PL"][i], out["QL"][i], out["sx_ref"][i] = PL[i], QL[i], sx
    out["t"] = t
    out["Cdc_mF"] = Cdc * 1e3
    return out
