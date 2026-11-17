"""Instantaneous-value (EMT-type), switching-averaged Python model of ONE Scott substation with two RPC legs.

NOT PSCAD / Simulink.  Averaged-switch model: each single-phase converter is a controlled voltage source
v_c = d * V_dc (d = modulation function, |d| <= m_lim) on the AC side and a current source d*i on the DC side.
All 50 Hz quantities are instantaneous sinusoids; the 100 Hz pulsation of the common DC link emerges from
v_c*i of the two single-phase legs (no separate injection).  Switching ripple is not modelled.

Circuit (per leg k = alpha, beta; both busbars are independent single-phase circuits, as in the sizing model):
   e_k(t) = sqrt2*27.5 kV*g*cos(w t + theta_k),  theta_alpha = 0, theta_beta = +90 deg   (beta leads alpha)
   source impedance (Thevenin of feeder: grid Ssc/2 per feeder, X/R=10, + Scott leg uk/MVA, X/R=30) R_th + L_th
   busbar k (27.5 kV): train load i_L (alpha only; constant-power, sinusoidal current at schedule P_L,Q_L) and
   single-phase coupling transformer 27.5/2.0 kV (rating C, uk, X/R=30: R_t, L_t on the 2.0 kV side)
   converter (averaged full bridge) on the common DC link: C_dc (+ optional series R_f-L_f-C_f 100 Hz branch).
Algebraic node equation solved in closed form (state: i_s only; i_src = i_L + i_s/n):
   v_bus (1 + L_th/(n^2 L_t)) = e - R_th i_src - L_th di_L/dt + L_th/(n L_t) (R_t i_s + v_c)
Control (discrete, sample time = time step, one-step computational delay + ZOH duty):
   SOGI-QSG on bus voltage (-> amplitude U, orthogonal signal), SOGI (or ideal 50 Hz LPF) load power measurement,
   law (15) s_x = min(max(0,|S_L|-eps_u Ssc)/2, kappa C min(U,1)) S_L/|S_L|, alpha leg injects s_x, beta leg absorbs
   s_x (+ loss estimate, + DC-energy PI 15 Hz zeta 0.7 on a 100 Hz-notched energy measurement), alpha-power
   feed-forward optional, current limit at rated current with P priority, instantaneous power -> current reference,
   PR current controller (resonant at 50 Hz) with grid-voltage feed-forward, duty = v_c*/V_dc (instantaneous V_dc)
   limited to +-m_lim with back-calculation anti-windup.
Vectorised over independent cases (batch dimension N) with numpy; plant integrated by RK4 (inputs held over a step).
"""
import math
import numpy as np

F0 = 50.0
W0 = 2 * math.pi * F0
VBUS_N = 27.5e3
N_TR = 27.5 / 2.0           # transformer ratio 27.5/2.0 kV
VS0 = 2000.0                # rated secondary voltage (V rms)
K0, K1, K2 = 0.003, 0.006, 0.006   # sizing loss model per leg (pu of rating) = params.RPC
KAPPA = 0.96
VREF = 3500.0
ZBASE_1MVA = VBUS_N ** 2 / 1e6      # ohm of 1 pu on 1 MVA at 27.5 kV (V^2 / S_b)


def thevenin(Ssc, leg_MVA=40.0, uk=0.105, xr_grid=10.0, xr_t=30.0):
    """Thevenin impedance of a feeder busbar, ohm at 27.5 kV (same construction as rpc_sizing.params.feeder_rx,
    pu on 1 MVA times 27.5^2 ohm): grid Ssc/2 per feeder + Scott leg uk/leg_MVA."""
    zg = 1.0 / (Ssc / 2.0)
    rg, xg = zg / math.sqrt(1 + xr_grid ** 2), zg * xr_grid / math.sqrt(1 + xr_grid ** 2)
    zt = uk / leg_MVA
    rt, xt = zt / math.sqrt(1 + xr_t ** 2), zt * xr_t / math.sqrt(1 + xr_t ** 2)
    return (rg + rt) * ZBASE_1MVA, (xg + xt) * ZBASE_1MVA


def simulate(cases, T, dt=25e-6, log_every=4, T_pre=0.6, T_ramp=0.4, verbose=False, eps_u_default=1.0):
    """cases: list of dicts (see defaults below).  T: total time incl. pre-roll T_pre (the schedule starts at T_pre).
    Returns dict of logs, arrays (nlog, ...) with batch index last, and 'vmin','vmax' (instantaneous, every step)."""
    N = len(cases)
    g = lambda k, d: np.array([c.get(k, d) for c in cases], float)
    C = g('C', 11.270562) * 1e6
    Ssc = g('Ssc', 750.0)
    legM = g('leg_MVA', 40.0)
    Hdc = g('H_ms', 8.0) * 1e-3
    Cdc = np.where(g('Cdc_mF', 0.0) > 0, g('Cdc_mF', 0.0) * 1e-3, 2 * Hdc * C / VREF ** 2)
    Cf_in = g('Cf_mF', 0.0) * 1e-3
    hf = (Cf_in > 0).astype(float)
    Cf = np.where(Cf_in > 0, Cf_in, 1.0)
    Qf = g('Qf', 30.0)
    Lf = np.where(Cf_in > 0, 1.0 / ((2 * W0) ** 2 * Cf), 1.0)
    Rf = np.where(Cf_in > 0, (1.0 / (2 * W0 * Cf)) / Qf, 0.0)
    gv = g('g', 1.0)
    ff = g('ff', 1.0)
    uk_t = g('uk_t', 0.10)
    xr_t = g('xr_t', 30.0)
    eps_u = g('eps_u', eps_u_default)
    mlim = g('m_lim', 0.95)
    tau_ref = g('tau_ref', 0.0)
    # load-power measurement: 0 = first-order 50 Hz low-pass of the load power (as in rpc_sizing/dynamics.py; default),
    # 1 = SOGI-based instantaneous power (implemented, but its discrete phase bias gives a ~0.5 Mvar error in Q; not used)
    meas_sogi = g('meas_sogi', 0.0)
    fbw = g('f_bw', 600.0)              # current-loop bandwidth (Hz)
    tau_r = g('tau_r', 1.5e-3)          # envelope time constant of the resonant part
    kff = g('kff', 1.0)
    # network
    Rth = np.empty(N); Lth = np.empty(N)
    for i, c in enumerate(cases):
        r, x = thevenin(c.get('Ssc_thev', c.get('Ssc', 750.0)), c.get('leg_MVA', 40.0))
        Rth[i], Lth[i] = r, x / W0
    Xt = uk_t * VS0 ** 2 / C
    Lt = Xt / W0
    Rt = Xt / xr_t
    rt_pu = uk_t / xr_t
    kc = Lth / (N_TR * Lt)
    kd = Lth / (N_TR ** 2 * Lt)
    inv1kd = 1.0 / (1.0 + kd)
    Em = math.sqrt(2) * VBUS_N * gv
    Imax = math.sqrt(2) * C / VS0       # rated secondary current, peak
    # controller gains
    Leq = Lt + Lth / N_TR ** 2
    Kp = 2 * math.pi * fbw * Leq
    Kr = 2.0 * Kp / tau_r
    wn = 2 * math.pi * 15.0
    Kpw, Kiw = 2 * 0.7 * wn, wn ** 2
    Kb = Kiw / Kpw
    Wref = 0.5 * Cdc * VREF ** 2
    cth, sth = math.cos(W0 * dt), math.sin(W0 * dt)
    kS = math.sqrt(2.0)
    kI = 2.0
    a50 = dt / (dt + 1.0 / (2 * math.pi * 50.0))
    a_m = dt / (dt + 1.0e-3)
    aref = np.where(tau_ref > 0, dt / (dt + np.maximum(tau_ref, 1e-12)), 1.0)
    # notch at 100 Hz (Q=1), bilinear transform with prewarping
    w2 = 2 * W0
    Qn = 1.0
    Kbl = w2 / math.tan(w2 * dt / 2)
    a0 = Kbl * Kbl + Kbl * w2 / Qn + w2 * w2
    nb0 = (Kbl * Kbl + w2 * w2) / a0
    nb1 = 2 * (w2 * w2 - Kbl * Kbl) / a0
    na1 = nb1
    na2 = (Kbl * Kbl - Kbl * w2 / Qn + w2 * w2) / a0
    # schedule
    K = max(len(c['P']) for c in cases)
    Pk = np.zeros((N, K + 1)); Qk = np.zeros((N, K + 1))
    for i, c in enumerate(cases):
        p = np.asarray(c['P'], float) * 1e6; q = np.asarray(c['Q'], float) * 1e6
        Pk[i, :len(p)] = p; Pk[i, len(p):] = p[-1]
        Qk[i, :len(q)] = q; Qk[i, len(q):] = q[-1]
    t_ev = g('t_ev', 1e9) + T_pre
    dPs = g('dP_MW', 0.0) * 1e6
    dQs = g('dQ_Mvar', 0.0) * 1e6
    Tr = g('ramp', 2e-3)
    # constants
    sgn = np.array([[-1.0], [1.0]])
    u0 = np.array([[1.0], [0.0]]); u1 = np.array([[0.0], [-1.0]])
    zero2 = np.zeros((2, N))
    row0 = np.array([[1.0], [0.0]])
    # ---------------- initial state
    P0 = np.zeros(N); Q0 = np.zeros(N)       # soft start: the load ramps from 0 to the first schedule value in T_ramp
    S0 = np.hypot(P0, Q0)
    sx0 = np.minimum(np.maximum(0.0, S0 - eps_u / 100 * Ssc * 1e6) / 2, KAPPA * C)
    cs0 = np.where(S0 > 1e3, P0 / np.maximum(S0, 1e-9), 1.0)
    sn0 = np.where(S0 > 1e3, Q0 / np.maximum(S0, 1e-9), 0.0)
    Px0, qx0 = sx0 * cs0, sx0 * sn0
    vq = np.vstack([np.zeros(N), Em * 1.0]); vf = np.vstack([Em, np.zeros(N)])
    vqs = vq.copy(); vfs = vf.copy()
    nq = int(round(0.005 / dt))               # T/4 = 5 ms
    th_h = -W0 * dt * np.arange(nq, 0, -1)     # analytic past of the initial voltages (oldest first)
    qbuf = np.zeros((nq, 2, N))
    for ii, ph in enumerate(th_h):
        qbuf[ii, 0] = Em * math.cos(ph); qbuf[ii, 1] = -Em * math.sin(ph)
    qptr = 0
    Vm2 = vf ** 2 + vq ** 2
    Pl0 = np.vstack([sgn[0, 0] * Px0, sgn[1, 0] * Px0]); Ql0 = np.vstack([sgn[0, 0] * qx0, sgn[1, 0] * qx0])
    is_ = (2 * N_TR / Vm2) * (Pl0 * vf + Ql0 * vq)
    V = np.full(N, VREF); if_ = np.zeros(N); vcf = np.full(N, VREF)
    ilf = (2 / Vm2[0]) * (P0 * vf[0] + Q0 * vq[0]); ilq = (2 / Vm2[0]) * (P0 * vq[0] - Q0 * vf[0])
    Pm = P0.copy(); Qm = Q0.copy()
    sh0 = sx0 / C
    ploss0 = 2 * C * (K0 + K1 * sh0 + K2 * sh0 ** 2)
    integ = (1 - ff) * (Px0 + ploss0)
    nt1 = (nb0 - na2) * Wref; nt2 = nt1.copy()
    Pf = Pl0.copy(); Qf = Ql0.copy()
    Pf[1] = ff * (Px0 + ploss0) + integ
    ra = np.zeros((2, N)); rb = np.zeros((2, N))
    d = np.zeros((2, N))
    awc = np.zeros(N)
    iL0 = zero2.copy(); diL = zero2.copy()
    psink = 2 * C * (K0 + K1 * sh0 + (K2 - rt_pu) * sh0 ** 2)
    # logs
    nsteps = int(round(T / dt))
    nlog = nsteps // log_every
    names2 = ['is', 'vbus', 'dcmd', 'vf', 'vq']
    L = {k: np.zeros((nlog, 2, N), np.float32) for k in names2}
    L1 = {k: np.zeros((nlog, N), np.float32) for k in ['V', 'if', 'vcf', 'iL', 'Pm', 'Qm', 'sx', 'U', 'Ppi', 'PL', 'QL', 'psink']}
    tl = np.zeros(nlog)
    vmin = np.full(N, 1e9); vmax = np.full(N, -1e9)
    nclip = np.zeros(N)
    ncl_leg = np.zeros((2, N))
    em = Em
    sqrt2 = math.sqrt(2.0)
    Vsafe_min = 100.0

    def vbus_f(e, i_s, vc, iLs, diLs):
        i_src = iLs + i_s / N_TR
        return (e - Rth * i_src - Lth * diLs + kc * (Rt * i_s + vc)) * inv1kd

    def efun(t):
        return em * (math.cos(W0 * t) * u0 + math.sin(W0 * t) * u1)

    h = dt
    lg = 0
    for k in range(nsteps):
        t = k * dt
        # ---------- schedule at t
        tau = t - T_pre
        if tau <= 0:
            idx, fr = 0, 0.0
            dPk = 0.0
            Pt = Pk[:, 0]; Qt = Qk[:, 0]; dPt = 0.0; dQt = 0.0
        else:
            idx = int(tau)
            if idx >= K - 1:
                idx = K - 1; fr = 0.0
                Pt = Pk[:, idx]; Qt = Qk[:, idx]; dPt = 0.0; dQt = 0.0
            else:
                fr = tau - idx
                dPt = Pk[:, idx + 1] - Pk[:, idx]; dQt = Qk[:, idx + 1] - Qk[:, idx]
                Pt = Pk[:, idx] + fr * dPt; Qt = Qk[:, idx] + fr * dQt
        if t < T_ramp:                       # soft start of the load (avoids artificial start-up transients)
            lam = t / T_ramp
            dPt = dPt * lam + Pt / T_ramp; dQt = dQt * lam + Qt / T_ramp
            Pt = Pt * lam; Qt = Qt * lam
        rp = (t - t_ev) / Tr
        rr = np.minimum(np.maximum(rp, 0.0), 1.0)
        Pt = Pt + dPs * rr; Qt = Qt + dQs * rr
        inr = ((rp > 0) & (rp < 1)).astype(float)
        dPt = dPt + dPs / Tr * inr; dQt = dQt + dQs / Tr * inr
        # ---------- measured bus voltage at t (previous duty, extrapolated load current)
        iLn = iL0 + h * diL
        vc_old = d * V
        vbus = vbus_f(efun(t), is_, vc_old, iLn, diL)
        # ---------- SOGI on bus voltage
        vf = vfs                              # state before the update is in phase with v(t_k) (forward-Euler SOGI)
        vfs = vfs + h * W0 * (kS * (vbus - vfs) - vqs)
        vqs = vqs + h * W0 * vfs
        vq = qbuf[qptr].copy()               # orthogonal signal by a T/4 delay of the SOGI in-phase output
        qbuf[qptr] = vf; qptr = (qptr + 1) % nq
        Vm2 = vf * vf + vq * vq
        Vm = np.sqrt(Vm2)
        Ua = Vm[0] / (sqrt2 * VBUS_N)
        # ---------- load power measurement (alpha bus)
        iL_a = iLn[0]
        ilf = ilf + h * W0 * (kI * (iL_a - ilf) - ilq)
        ilq = ilq + h * W0 * ilf
        Ps = 0.5 * (vf[0] * ilf + vq[0] * ilq)
        Qs = 0.5 * (vq[0] * ilf - vf[0] * ilq)
        Pm = Pm + (meas_sogi * a_m + (1 - meas_sogi) * a50) * (meas_sogi * Ps + (1 - meas_sogi) * Pt - Pm)
        Qm = Qm + (meas_sogi * a_m + (1 - meas_sogi) * a50) * (meas_sogi * Qs + (1 - meas_sogi) * Qt - Qm)
        # ---------- law (15)
        S = np.hypot(Pm, Qm)
        req = np.maximum(0.0, S - eps_u / 100 * Ssc * 1e6) / 2
        lim = C * np.minimum(Ua, 1.0)
        sx = np.minimum(req, KAPPA * lim)
        Sg = np.maximum(S, 1e3)
        Px = sx * Pm / Sg; qx = sx * Qm / Sg
        sh = sx / C
        ploss = 2 * C * (K0 + K1 * sh + K2 * sh * sh)
        psink = 2 * C * (K0 + K1 * sh + (K2 - rt_pu) * sh * sh)
        # ---------- DC-energy PI on notched energy
        W = 0.5 * Cdc * V * V
        y = nb0 * W + nt1
        nt1 = nb1 * W - na1 * y + nt2
        nt2 = nb0 * W - na2 * y
        eW = Wref - y
        Ppi = Kpw * eW + integ
        Pmax = Vm * (Imax / (2 * N_TR))
        integ = integ + h * (Kiw * eW + Kb * awc)
        integ = np.minimum(np.maximum(integ, -Pmax[1]), Pmax[1])
        # ---------- references (power absorbed from the bus)
        P0r = sgn * Px
        Q0r = sgn * qx
        P0r[1] = ff * (Px + ploss) + Ppi
        Pf = Pf + aref * (P0r - Pf)
        Qf = Qf + aref * (Q0r - Qf)
        Pc = np.minimum(np.maximum(Pf, -Pmax), Pmax)
        awc = Pc[1] - Pf[1]                  # back-calculation signal of the DC-energy PI (beta leg at its current limit)
        Qmx = np.sqrt(np.maximum(Pmax * Pmax - Pc * Pc, 0.0))
        Qc = np.minimum(np.maximum(Qf, -Qmx), Qmx)
        iref = (2 * N_TR / np.maximum(Vm2, 1.0)) * (Pc * vf + Qc * vq)
        # ---------- PR current control + modulation
        e = iref - is_
        u = Kp * e + Kr * ra
        vcs = kff * vf / N_TR - u
        Vs = np.maximum(V, Vsafe_min)
        dcmd = vcs / Vs
        d = np.minimum(np.maximum(dcmd, -mlim), mlim)
        dv = (dcmd - d) * Vs
        sat = (dv != 0.0)
        nclip += sat.any(axis=0)
        ncl_leg += sat
        ere = e + dv / Kp
        ra, rb = cth * ra - sth * rb + ere * (sth / W0), sth * ra + cth * rb + ere * ((1 - cth) / W0)
        # ---------- load current for the plant (constant power, sinusoidal)
        iL0 = row0 * ((2.0 / Vm2[0]) * (Pt * vf[0] + Qt * vq[0]))
        diL = row0 * ((2.0 * W0 / Vm2[0]) * (-Pt * vq[0] + Qt * vf[0]) + (2.0 / Vm2[0]) * (dPt * vf[0] + dQt * vq[0]))
        # ---------- log
        if k % log_every == 0 and lg < nlog:
            tl[lg] = t
            L['is'][lg] = is_; L['vbus'][lg] = vbus; L['dcmd'][lg] = dcmd; L['vf'][lg] = vf; L['vq'][lg] = vq
            L1['V'][lg] = V; L1['if'][lg] = if_; L1['vcf'][lg] = vcf; L1['iL'][lg] = iL0[0]
            L1['Pm'][lg] = Pm; L1['Qm'][lg] = Qm; L1['sx'][lg] = sx; L1['U'][lg] = Ua; L1['Ppi'][lg] = Ppi
            L1['PL'][lg] = Pt; L1['QL'][lg] = Qt; L1['psink'][lg] = psink
            lg += 1
        # ---------- plant: RK4 over one step with held d, psink, iL0, diL
        def f(tt, i_s, V_, i_f, vc_f):
            tl_ = tt - t
            iLs = iL0 + tl_ * diL
            vc = d * V_
            vb = vbus_f(efun(tt), i_s, vc, iLs, diL)
            di = (vb / N_TR - Rt * i_s - vc) / Lt
            dV = ((d * i_s).sum(axis=0) - psink / np.maximum(V_, Vsafe_min) - i_f) / Cdc
            dif = hf * (V_ - vc_f - Rf * i_f) / Lf
            dvc = hf * i_f / Cf
            return di, dV, dif, dvc
        k1i, k1V, k1f, k1c = f(t, is_, V, if_, vcf)
        k2i, k2V, k2f, k2c = f(t + h / 2, is_ + h / 2 * k1i, V + h / 2 * k1V, if_ + h / 2 * k1f, vcf + h / 2 * k1c)
        k3i, k3V, k3f, k3c = f(t + h / 2, is_ + h / 2 * k2i, V + h / 2 * k2V, if_ + h / 2 * k2f, vcf + h / 2 * k2c)
        k4i, k4V, k4f, k4c = f(t + h, is_ + h * k3i, V + h * k3V, if_ + h * k3f, vcf + h * k3c)
        is_ = is_ + h / 6 * (k1i + 2 * k2i + 2 * k3i + k4i)
        V = V + h / 6 * (k1V + 2 * k2V + 2 * k3V + k4V)
        if_ = if_ + h / 6 * (k1f + 2 * k2f + 2 * k3f + k4f)
        vcf = vcf + h / 6 * (k1c + 2 * k2c + 2 * k3c + k4c)
        np.minimum(vmin, V, out=vmin); np.maximum(vmax, V, out=vmax)
        if verbose and k % 20000 == 0:
            print(f"  t={t:.3f}s V={V[:3]}", flush=True)
    out = dict(t=tl[:lg], vmin=vmin, vmax=vmax, nclip=nclip, nclip_leg=ncl_leg, dt=dt, log_every=log_every,
               T_pre=T_pre, nsteps=nsteps)
    for k_, v_ in L.items(): out[k_] = v_[:lg]
    for k_, v_ in L1.items(): out[k_] = v_[:lg]
    out['par'] = dict(C=C, Cdc=Cdc, Cf=np.where(hf > 0, Cf, 0.0), Lf=Lf, Rf=Rf, Rt=Rt, Lt=Lt, Xt=Xt, Rth=Rth, Lth=Lth,
                      Kp=Kp, Kr=Kr, mlim=mlim, Imax=Imax, hf=hf, Ssc=Ssc, gv=gv, ff=ff)
    return out
