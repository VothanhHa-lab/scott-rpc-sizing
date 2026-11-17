"""Switching (PWM) instantaneous-value model of ONE Scott co-phase substation with two RPC legs on a common DC link.

Purpose: check the DC-link band and the leg currents of the final design (C = 11.5 MVA per leg, eps_u = 1 %,
H_dc = 26.2 ms, C_dc = 49.2 mF, V_dc = 3.5 kV) with the switching of the converters included.

What is modelled (differences from the averaged model emt.py of the paper are marked *):
  * each leg = Nb single-phase full bridges (H-bridges) with ideal switches, unipolar (three-level) sine-triangle PWM,
    carriers of the Nb bridges interleaved by Tc/(2 Nb); each bridge feeds the 27.5 kV busbar through its own
    single-phase coupling transformer 27.5/2.0 kV rated C/Nb, uk = 10 %, X/R = 30 (leakage referred to the 2 kV side);
    the converter voltage is s*V_dc with s in {-1, 0, +1}, the DC current s*i;
  * digital control sampled at the carrier peaks and valleys of bridge 0 (fs = 2 fc) with one-sample computational
    delay; current and voltages are averaged over the sampling period (anti-aliasing); PR current control with
    resonant delay compensation (Yepes et al. 2010); voltage feed-forward advanced by the delay;
  - grid, Scott leg impedances, constant-power train load on the alpha busbar, law (15) with the measured busbar
    voltage, current limit with P priority, DC-energy PI (15 Hz, zeta 0.7, 100 Hz notch) with alpha-power feed-forward,
    loss sink on the DC link: as in emt.py;
  - no dead time, no device voltage drops, no capacitor ESR, no protection, no PLL dynamics (50 Hz fixed),
    sinusoidal train current (train harmonics not included).
Plant integrated with RK4 at dt (default 2 us) with switch states held over a step (carrier compared at step start).
Not PSCAD/EMTDC, not Simulink.
"""
import math
import numpy as np
from numba import njit
from scipy.linalg import expm

F0 = 50.0
W0 = 2 * math.pi * F0
VBUS_N = 27.5e3
N_TR = 27.5 / 2.0
VS0 = 2000.0
K0, K1, K2 = 0.003, 0.006, 0.006
KAPPA = 0.96
VREF = 3500.0
ZBASE_1MVA = VBUS_N ** 2 / 1e6


def thevenin(Ssc, leg_MVA=40.0, uk=0.105, xr_grid=10.0, xr_t=30.0):
    zg = 1.0 / (Ssc / 2.0)
    rg, xg = zg / math.sqrt(1 + xr_grid ** 2), zg * xr_grid / math.sqrt(1 + xr_grid ** 2)
    zt = uk / leg_MVA
    rt, xt = zt / math.sqrt(1 + xr_t ** 2), zt * xr_t / math.sqrt(1 + xr_t ** 2)
    return (rg + rt) * ZBASE_1MVA, (xg + xt) * ZBASE_1MVA


def sogi_discrete(Ts, k=math.sqrt(2.0)):
    """Exact ZOH discretisation of the SOGI x' = A x + B u (x = [v', qv'])."""
    A = W0 * np.array([[-k, -1.0], [1.0, 0.0]])
    B = W0 * np.array([k, 0.0])
    Ad = expm(A * Ts)
    Bd = np.linalg.solve(A, (Ad - np.eye(2)) @ B)
    return Ad, Bd


def sogi_calibration(Ts):
    """Phase and gain of the (period-average -> ZOH SOGI) chain at 50 Hz, referred to the instantaneous
    value at the sampling instant: returns (gain, phase) such that phasor_true(t_k) = phasor_est * exp(j*phase)/gain."""
    Ad, Bd = sogi_discrete(Ts)
    x = np.zeros(2)
    n = int(round(0.4 / Ts))
    est = []
    for m in range(1, n + 1):
        t1 = m * Ts; t0 = t1 - Ts
        u = (math.sin(W0 * t1) - math.sin(W0 * t0)) / (W0 * Ts)       # average of cos over [t0, t1]
        x = Ad @ x + Bd * u
        est.append((x[0] + 1j * x[1]) * np.exp(-1j * W0 * t1))         # true phasor of cos at t1 is 1
    z = np.mean(est[-int(round(0.04 / Ts)):])
    return float(abs(z)), float(-np.angle(z))


@njit(cache=True)
def _sim(T, dt, Ts_n, Nb, fc,
         C, Ssc, eps_u, Cdc, ff, kff, mlim, fbw, tau_r, g, Rth, Lth, Rt, Lt,
         Pk, Qk, T_pre, T_ramp, t_ev, dPs, dQs, Tr,
         Ad, Bd, cal_g, cal_ph, avg_mode, log_every, V0, ploss_scale, kh_gain, v_pred, kh5_gain):
    h = dt
    Ts = Ts_n * dt
    nsteps = int(round(T / dt))
    K = Pk.shape[0]
    Em = math.sqrt(2.0) * VBUS_N * g
    Lj = Nb * Lt; Rj = Nb * Rt
    kd = Nb * Lth / (N_TR * N_TR * Lj)
    kc = Lth / (N_TR * Lj)
    inv1kd = 1.0 / (1.0 + kd)
    Imax = math.sqrt(2.0) * C / VS0
    rt_pu = (Rt * C / VS0 ** 2)
    # controller gains (equivalent leg inductance)
    Leq = Lt + Lth / N_TR ** 2
    Kp = 2 * math.pi * fbw * Leq
    Kr = 2.0 * Kp / tau_r
    phi_d = W0 * 2.0 * Ts                 # delay: averaging centre (t_k - Ts/2) to application centre (t_k + 1.5 Ts)
    NH = 3
    hh = np.array([1.0, 3.0, 5.0])
    krh = np.array([1.0, kh_gain, kh5_gain]) * Kr
    cwT = np.cos(hh * W0 * Ts)
    cphi = np.cos(hh * phi_d); cphi1 = np.cos(hh * phi_d - hh * W0 * Ts)
    wn = 2 * math.pi * 15.0
    Kpw = 2 * 0.7 * wn; Kiw = wn * wn; Kb = Kiw / Kpw
    Wref = 0.5 * Cdc * VREF ** 2
    a50 = Ts / (Ts + 1.0 / (2 * math.pi * 50.0))
    w2 = 2 * W0; Qn = 1.0
    Kbl = w2 / math.tan(w2 * Ts / 2)
    a0 = Kbl * Kbl + Kbl * w2 / Qn + w2 * w2
    nb0 = (Kbl * Kbl + w2 * w2) / a0
    nb1 = 2 * (w2 * w2 - Kbl * Kbl) / a0
    na1 = nb1
    na2 = (Kbl * Kbl - Kbl * w2 / Qn + w2 * w2) / a0
    # ---------------- states
    I = np.zeros((2, Nb))            # bridge currents, 2 kV side, positive from busbar into converter
    V = V0
    # plant-side SOGI for the load-current model (forward Euler at dt, T/4 delay for the orthogonal signal)
    nq = int(round(0.005 / dt))
    qbuf = np.zeros(nq)
    for ii in range(nq):
        ph = -W0 * dt * (nq - ii)
        qbuf[ii] = Em * math.cos(ph)
    qptr = 0
    pvf = Em; pvfs = Em; pvqs = 0.0
    kS = math.sqrt(2.0)
    # controller states
    xs = np.zeros((2, 2))            # control SOGI states per busbar
    xs[0, 0] = Em; xs[0, 1] = 0.0    # alpha at t=0: in-phase cos(0)=1, quadrature sin(0)=0
    xs[1, 0] = 0.0; xs[1, 1] = Em    # beta = cos(wt+90 deg): in-phase 0, quadrature 1
    ry = np.zeros((2, 3, 2))         # resonant controller outputs y[k-1], y[k-2] per harmonic
    re1 = np.zeros(2)                # e[k-1]
    Vm_prev = V0
    Pm = 0.0; Qm = 0.0
    integ = 0.0
    nt1 = (nb0 - na2) * Wref; nt2 = nt1
    d_now = np.zeros(2); d_next = np.zeros(2)
    acc_i = np.zeros(2); acc_v = np.zeros(2); acc_V = 0.0; acc_n = 0
    psink = 0.0
    # logs
    nlog = nsteps // log_every + 1
    Lt_ = np.zeros(nlog); LV = np.zeros(nlog, np.float32); LI = np.zeros((nlog, 2, Nb), np.float32)
    Lvb = np.zeros((nlog, 2), np.float32); LiL = np.zeros(nlog, np.float32); Ld = np.zeros((nlog, 2), np.float32)
    Lsx = np.zeros(nlog, np.float32); LPL = np.zeros(nlog, np.float32); LQL = np.zeros(nlog, np.float32)
    LU = np.zeros(nlog, np.float32); Lir = np.zeros((nlog, 2), np.float32)
    lg = 0
    vmin = 1e9; vmax = -1e9
    ipk = np.zeros((2, Nb))
    dmax = 0.0
    nclip = 0
    iref_hold = np.zeros(2)
    sx_hold = 0.0; U_hold = 1.0
    Tc = 1.0 / fc
    s = np.zeros((2, Nb))
    kI = np.zeros((4, 2, Nb)); kV = np.zeros(4)
    vb0 = Em; vb1 = 0.0
    for k in range(nsteps):
        t = k * dt
        # ---------------- schedule (traction load on the alpha busbar)
        tau = t - T_pre
        if tau <= 0:
            Pt = Pk[0]; Qt = Qk[0]; dPt = 0.0; dQt = 0.0
        else:
            idx = int(tau)
            if idx >= K - 1:
                Pt = Pk[K - 1]; Qt = Qk[K - 1]; dPt = 0.0; dQt = 0.0
            else:
                fr = tau - idx
                dPt = Pk[idx + 1] - Pk[idx]; dQt = Qk[idx + 1] - Qk[idx]
                Pt = Pk[idx] + fr * dPt; Qt = Qk[idx] + fr * dQt
        if t < T_ramp:
            lam = t / T_ramp
            dPt = dPt * lam + Pt / T_ramp; dQt = dQt * lam + Qt / T_ramp
            Pt = Pt * lam; Qt = Qt * lam
        rp = (t - t_ev) / Tr
        rr = min(max(rp, 0.0), 1.0)
        Pt = Pt + dPs * rr; Qt = Qt + dQs * rr
        if rp > 0 and rp < 1:
            dPt += dPs / Tr; dQt += dQs / Tr
        # ---------------- digital controller at the sampling instants (every Ts_n plant steps)
        if k % Ts_n == 0:
            d_now[0] = d_next[0]; d_now[1] = d_next[1]          # apply the duty computed one sample earlier
            if acc_n > 0:
                im0 = acc_i[0] / acc_n; im1 = acc_i[1] / acc_n
                vm0 = acc_v[0] / acc_n; vm1 = acc_v[1] / acc_n
                Vm_dc = acc_V / acc_n
            else:
                im0 = 0.0; im1 = 0.0; vm0 = Em; vm1 = 0.0; Vm_dc = V
            acc_i[0] = 0.0; acc_i[1] = 0.0; acc_v[0] = 0.0; acc_v[1] = 0.0; acc_V = 0.0; acc_n = 0
            # SOGI on period-averaged busbar voltages, calibrated to the instantaneous phasor at t_k
            vfk = np.zeros(2); vqk = np.zeros(2)
            for b in range(2):
                u = vm0 if b == 0 else vm1
                x0 = Ad[0, 0] * xs[b, 0] + Ad[0, 1] * xs[b, 1] + Bd[0] * u
                x1 = Ad[1, 0] * xs[b, 0] + Ad[1, 1] * xs[b, 1] + Bd[1] * u
                xs[b, 0] = x0; xs[b, 1] = x1
                c = math.cos(cal_ph); sn = math.sin(cal_ph)
                vfk[b] = (x0 * c - x1 * sn) / cal_g
                vqk[b] = (x0 * sn + x1 * c) / cal_g
            Vm2a = vfk[0] ** 2 + vqk[0] ** 2
            Vm2b = vfk[1] ** 2 + vqk[1] ** 2
            Vma = math.sqrt(Vm2a); Vmb = math.sqrt(Vm2b)
            Ua = Vma / (math.sqrt(2.0) * VBUS_N)
            # load-power measurement: 50 Hz first-order low-pass of the schedule (as in emt.py, default)
            Pm = Pm + a50 * (Pt - Pm)
            Qm = Qm + a50 * (Qt - Qm)
            S = math.hypot(Pm, Qm)
            req = max(0.0, S - eps_u / 100.0 * Ssc * 1e6) / 2
            lim = C * min(Ua, 1.0)
            sx = min(req, KAPPA * lim)
            Sg = max(S, 1e3)
            Px = sx * Pm / Sg; qx = sx * Qm / Sg
            sh = sx / C
            ploss = 2 * C * (K0 + K1 * sh + K2 * sh * sh)
            psink = ploss_scale * 2 * C * (K0 + K1 * sh + (K2 - rt_pu) * sh * sh)
            # DC-energy PI on the notched energy
            W = 0.5 * Cdc * Vm_dc * Vm_dc
            y = nb0 * W + nt1
            nt1 = nb1 * W - na1 * y + nt2
            nt2 = nb0 * W - na2 * y
            eW = Wref - y
            Ppi = Kpw * eW + integ
            Pmax_a = Vma * (Imax / (2 * N_TR)); Pmax_b = Vmb * (Imax / (2 * N_TR))
            # references: power absorbed from the busbar
            Pr = np.array([-Px, ff * (Px + ploss) + Ppi])
            Qr = np.array([-qx, qx])
            Pmx = np.array([Pmax_a, Pmax_b])
            Pc = np.zeros(2); Qc = np.zeros(2)
            for b in range(2):
                Pc[b] = min(max(Pr[b], -Pmx[b]), Pmx[b])
                qm = math.sqrt(max(Pmx[b] ** 2 - Pc[b] ** 2, 0.0))
                Qc[b] = min(max(Qr[b], -qm), qm)
            awc = Pc[1] - Pr[1]
            integ = integ + Ts * (Kiw * eW + Kb * awc)
            integ = min(max(integ, -Pmax_b), Pmax_b)
            imeas = np.array([im0, im1])
            # DC voltage predicted to the application centre (2 Ts ahead of the averaging centre)
            Vpred = Vm_dc + v_pred * 2.0 * (Vm_dc - Vm_prev)
            Vm_prev = Vm_dc
            Vdc_s = max(Vpred, 100.0)
            for b in range(2):
                vf = vfk[b]; vq = vqk[b]
                Vm2 = vf * vf + vq * vq
                # reference at the averaging centre t_k - Ts/2 (rotate back by w Ts/2), period-average gain
                cb = math.cos(-W0 * Ts / 2); sb = math.sin(-W0 * Ts / 2)
                vfm = vf * cb - vq * sb; vqm = vf * sb + vq * cb
                gav = math.sin(W0 * Ts / 2) / (W0 * Ts / 2)
                iref = gav * (2 * N_TR / max(Vm2, 1.0)) * (Pc[b] * vfm + Qc[b] * vqm)
                iref_hold[b] = iref
                e = iref - imeas[b]
                # resonant controller with delay compensation: y = 2cos(wTs) y1 - y2 + Kr Ts (cos(phi) e - cos(phi-wTs) e1)
                yrs = np.zeros(3)
                ysum = 0.0
                for q in range(NH):
                    yrs[q] = 2 * cwT[q] * ry[b, q, 0] - ry[b, q, 1] + krh[q] * Ts * (cphi[q] * e - cphi1[q] * re1[b])
                    ysum += yrs[q]
                u = Kp * e + ysum
                # feed-forward of the busbar voltage at the application centre t_k + 1.5 Ts
                ca = math.cos(1.5 * W0 * Ts); sa = math.sin(1.5 * W0 * Ts)
                vff = (vf * ca - vq * sa) / N_TR
                vcs = kff * vff - u
                dc = vcs / Vdc_s
                dl = min(max(dc, -mlim), mlim)
                if dl != dc:
                    nclip += 1                                  # conditional integration (anti-windup)
                else:
                    for q in range(NH):
                        ry[b, q, 1] = ry[b, q, 0]; ry[b, q, 0] = yrs[q]
                    re1[b] = e
                d_next[b] = dl
                if abs(dl) > dmax and t >= T_pre:
                    dmax = abs(dl)
            sx_hold = sx; U_hold = Ua
        # ---------------- switching functions (unipolar PWM, interleaved carriers)
        for b in range(2):
            for j in range(Nb):
                if avg_mode:
                    s[b, j] = d_now[b]
                else:
                    ph = (t / Tc + j / (2.0 * Nb)) % 1.0
                    cr = 4.0 * ph - 1.0 if ph < 0.5 else 3.0 - 4.0 * ph      # triangle -1..1, peak at ph=0.5
                    sA = 1.0 if d_now[b] > cr else 0.0
                    sB = 1.0 if -d_now[b] > cr else 0.0
                    s[b, j] = sA - sB
        # ---------------- plant-side load current (constant power, sinusoidal) from the plant SOGI
        Vm2p = pvf * pvf + qbuf[qptr] * qbuf[qptr]
        pvq = qbuf[qptr]
        iL0 = (2.0 / Vm2p) * (Pt * pvf + Qt * pvq)
        diL = (2.0 * W0 / Vm2p) * (-Pt * pvq + Qt * pvf) + (2.0 / Vm2p) * (dPt * pvf + dQt * pvq)
        # ---------------- RK4 over one plant step
        Ist = I.copy(); Vst = V
        for stg in range(4):
            if stg == 0:
                tt = t; Ic = I; Vc = V
            elif stg == 1:
                tt = t + h / 2; Ic = I + h / 2 * kI[0]; Vc = V + h / 2 * kV[0]
            elif stg == 2:
                tt = t + h / 2; Ic = I + h / 2 * kI[1]; Vc = V + h / 2 * kV[1]
            else:
                tt = t + h; Ic = I + h * kI[2]; Vc = V + h * kV[2]
            iLs = iL0 + (tt - t) * diL
            dcI = 0.0
            for b in range(2):
                if b == 0:
                    e_src = Em * math.cos(W0 * tt); iLb = iLs; diLb = diL
                else:
                    e_src = -Em * math.sin(W0 * tt); iLb = 0.0; diLb = 0.0
                sumi = 0.0; sumv = 0.0
                for j in range(Nb):
                    sumi += Ic[b, j]
                    sumv += Rj * Ic[b, j] + s[b, j] * Vc
                i_src = iLb + sumi / N_TR
                vb = (e_src - Rth * i_src - Lth * diLb + kc * sumv) * inv1kd
                for j in range(Nb):
                    kI[stg, b, j] = (vb / N_TR - Rj * Ic[b, j] - s[b, j] * Vc) / Lj
                    dcI += s[b, j] * Ic[b, j]
                if stg == 0:
                    if b == 0:
                        vb0 = vb
                    else:
                        vb1 = vb
            kV[stg] = (dcI - psink / max(Vc, 100.0)) / Cdc
        I = I + h / 6 * (kI[0] + 2 * kI[1] + 2 * kI[2] + kI[3])
        V = V + h / 6 * (kV[0] + 2 * kV[1] + 2 * kV[2] + kV[3])
        # ---------------- plant SOGI update (alpha busbar voltage at t)
        pvf_old = pvfs
        pvfs = pvfs + h * W0 * (kS * (vb0 - pvfs) - pvqs)
        pvqs = pvqs + h * W0 * pvfs
        qbuf[qptr] = pvf_old; qptr = (qptr + 1) % nq
        pvf = pvfs
        # ---------------- measurement accumulation (state after the step ~ trapezoid with the start value)
        for b in range(2):
            si = 0.0; si0 = 0.0
            for j in range(Nb):
                si += I[b, j]; si0 += Ist[b, j]
            acc_i[b] += 0.5 * (si + si0)
        acc_v[0] += vb0; acc_v[1] += vb1
        acc_V += 0.5 * (V + Vst); acc_n += 1
        # ---------------- extremes (after the pre-roll)
        if t >= T_pre:
            if V < vmin: vmin = V
            if V > vmax: vmax = V
            for b in range(2):
                for j in range(Nb):
                    if abs(I[b, j]) > ipk[b, j]: ipk[b, j] = abs(I[b, j])
        if k % log_every == 0 and lg < nlog:
            Lt_[lg] = t; LV[lg] = V
            for b in range(2):
                for j in range(Nb):
                    LI[lg, b, j] = I[b, j]
                Ld[lg, b] = d_now[b]; Lir[lg, b] = iref_hold[b]
            Lvb[lg, 0] = vb0; Lvb[lg, 1] = vb1; LiL[lg] = iL0
            Lsx[lg] = sx_hold; LPL[lg] = Pt; LQL[lg] = Qt; LU[lg] = U_hold
            lg += 1
    return (Lt_[:lg], LV[:lg], LI[:lg], Lvb[:lg], LiL[:lg], Ld[:lg], Lsx[:lg], LPL[:lg], LQL[:lg], LU[:lg], Lir[:lg],
            vmin, vmax, ipk, dmax, nclip, Kp, Kr)


def simulate(case, T, dt=2e-6, fc=1000.0, Nb=2, T_pre=0.6, T_ramp=0.4, f_bw=150.0, tau_r=0.010, avg_mode=False,
             log_dt=10e-6, kh_gain=0.05, v_pred=1.0, kh5_gain=0.0):
    """case: dict with P, Q (MW, Mvar knots at 1 s), optional C (MVA), Cdc_mF or H_ms, eps_u, Ssc, Ssc_thev, g,
    leg_MVA, uk_t, xr_t, ff, kff, m_lim, dP_MW, dQ_Mvar, t_ev, ramp."""
    C = case.get('C', 11.5) * 1e6
    Ssc = case.get('Ssc', 750.0)
    H = case.get('H_ms', 26.2) * 1e-3
    Cdc = case['Cdc_mF'] * 1e-3 if case.get('Cdc_mF', 0) > 0 else 2 * H * C / VREF ** 2
    r, x = thevenin(case.get('Ssc_thev', Ssc), case.get('leg_MVA', 40.0))
    Rth, Lth = r, x / W0
    uk_t = case.get('uk_t', 0.10); xr_t = case.get('xr_t', 30.0)
    Xt = uk_t * VS0 ** 2 / C
    Lt = Xt / W0 + case.get('L_extra_mH', 0.0) * 1e-3
    Rt = Xt / xr_t
    Ts = 1.0 / (2 * fc)
    Ts_n = int(round(Ts / dt))
    assert abs(Ts_n * dt - Ts) < 1e-9 * Ts, 'dt must divide the sampling period'
    Ad, Bd = sogi_discrete(Ts)
    cal_g, cal_ph = sogi_calibration(Ts)
    P = np.asarray(case['P'], float) * 1e6; Q = np.asarray(case['Q'], float) * 1e6
    t_ev = case.get('t_ev', 1e9) + T_pre
    dP = case.get('dP_MW', 0.0) * 1e6; dQ = case.get('dQ_Mvar', 0.0) * 1e6
    le = max(1, int(round(log_dt / dt)))
    out = _sim(T, dt, Ts_n, Nb, fc, C, Ssc, case.get('eps_u', 1.0), Cdc, case.get('ff', 1.0), case.get('kff', 1.0),
               case.get('m_lim', 0.95), f_bw, tau_r, case.get('g', 1.0), Rth, Lth, Rt, Lt,
               P, Q, T_pre, T_ramp, t_ev, dP, dQ, case.get('ramp', 2e-3),
               Ad, Bd, cal_g, cal_ph, avg_mode, le, VREF, case.get('ploss_scale', 1.0), kh_gain, v_pred, kh5_gain)
    keys = ['t', 'V', 'I', 'vbus', 'iL', 'd', 'sx', 'PL', 'QL', 'U', 'iref']
    o = {k: v for k, v in zip(keys, out[:11])}
    o.update(vmin=out[11], vmax=out[12], ipk=out[13], dmax=out[14], nclip=out[15], Kp=out[16], Kr=out[17])
    o['par'] = dict(C=C, Cdc=Cdc, Lt=Lt, Rt=Rt, Xt=Xt, Rth=Rth, Lth=Lth, Ts=Ts, fc=fc, Nb=Nb, dt=dt, T_pre=T_pre,
                    cal_g=cal_g, cal_ph=cal_ph, f_bw=f_bw, tau_r=tau_r, avg_mode=avg_mode)
    return o
