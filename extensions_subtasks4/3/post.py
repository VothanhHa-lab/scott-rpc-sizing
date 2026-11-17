"""Post-processing of emt.simulate outputs: instantaneous V_dc statistics, 100 Hz ripple, per-leg phasors (one-cycle
lock-in), currents in pu, modulation index, DC-voltage minimum required for modulation, power-transfer error, losses,
recovery time."""
import math
import numpy as np
from scipy.ndimage import maximum_filter1d, minimum_filter1d
W0 = 2 * math.pi * 50.0
N_TR = 27.5 / 2.0
KAPPA = 0.96
TAN_DELTA = 0.002          # ASSUMPTION: DC-link capacitor dissipation factor at 100 Hz (film), see NOTES


def ma(x, n):
    """centred moving average over n samples along axis 0 (edges use the available samples)."""
    c = np.cumsum(np.insert(x, 0, 0, axis=0), axis=0)
    out = np.empty_like(x, dtype=float)
    N = x.shape[0]
    idx = np.arange(N)
    lo = np.maximum(idx - n // 2, 0); hi = np.minimum(idx + n - n // 2, N)
    cnt = (hi - lo).reshape((-1,) + (1,) * (x.ndim - 1))
    return (c[hi] - c[lo]) / cnt


def phasor(x, t, nwin):
    """peak phasor (complex) of the 50 Hz component, one-cycle sliding window (nwin samples = 20 ms)."""
    z = x * np.exp(-1j * W0 * t).reshape((-1,) + (1,) * (x.ndim - 1))
    return 2 * ma(z, nwin)


def analyse(o, i, c, m_max=0.95, tau_band=0.02, t_event=None, esr_tand=TAN_DELTA):
    t = o['t']; dtl = o['dt'] * o['log_every']
    par = o['par']
    sel = t >= o['T_pre'] - 1e-9
    n10 = int(round(0.01 / dtl)); n20 = int(round(0.02 / dtl))
    V = o['V'][:, i].astype(float)
    Cdc = par['Cdc'][i]; C = par['C'][i]; Imax = par['Imax'][i]; Xt = par['Xt'][i]; Rt = par['Rt'][i]
    Ssc = par['Ssc'][i]
    res = {}
    s = np.where(sel)[0]
    s0, s1 = s[0] + n20, s[-1] - n20           # exclude the lock-in edges
    sl = slice(s0, s1)
    Vs = V[sl]
    res['Vmin_V'] = float(Vs.min()); res['Vmax_V'] = float(Vs.max())
    res['Vmin_pct'] = 100 * (Vs.min() / 3500 - 1); res['Vmax_pct'] = 100 * (Vs.max() / 3500 - 1)
    Vavg = np.sqrt(ma(V ** 2, n20))     # energy-based average over two ripple periods (20 ms)
    res['Vavg_min_V'] = float(Vavg[sl].min()); res['Vavg_max_V'] = float(Vavg[sl].max())
    res['Vavg_min_pct'] = 100 * (Vavg[sl].min() / 3500 - 1); res['Vavg_max_pct'] = 100 * (Vavg[sl].max() / 3500 - 1)
    # 100 Hz ripple: half peak-to-peak in any 10 ms window
    hp = 0.5 * (maximum_filter1d(V, n10) - minimum_filter1d(V, n10))
    res['ripple_halfpp_max_V'] = float(hp[sl].max()); res['ripple_pct'] = 100 * float(hp[sl].max()) / 3500
    res['band_ok'] = bool(Vs.min() >= 3150 and Vs.max() <= 3850)
    res['t_outside_band_ms'] = float(1e3 * dtl * np.sum((Vs < 3150) | (Vs > 3850)))
    # phasors (peak) of bus voltage (primary) and converter current (secondary) of both legs
    vb = o['vbus'][:, :, i].astype(float); isl = o['is'][:, :, i].astype(float)
    Vb = phasor(vb, t, n20); Is = phasor(isl, t, n20)
    Ipu = np.abs(Is) / Imax
    res['I_pu_max'] = [float(Ipu[sl, k].max()) for k in range(2)]
    res['I_inst_pu_max'] = [float(np.abs(isl[sl, k]).max() / Imax) for k in range(2)]
    res['U_pu_min'] = [float((np.abs(Vb[sl, k]) / (math.sqrt(2) * 27.5e3)).min()) for k in range(2)]
    Sleg = 0.5 * Vb * np.conj(Is / N_TR)                   # absorbed from the bus (VA)
    Vconv = Vb / N_TR - (Rt + 1j * Xt) * Is
    Vc_pk = np.abs(Vconv)
    res['Vconv_pk_max_V'] = [float(Vc_pk[sl, k].max()) for k in range(2)]
    vreq = Vc_pk / m_max
    res['Vdc_req_max_V'] = float(vreq[sl].max())            # minimum DC voltage for modulation at the actual operating point
    res['Vdc_req_max_leg'] = [float(vreq[sl, k].max()) for k in range(2)]
    # margin of the instantaneous minimum, evaluated at the instants of the max requirement and globally
    res['Vmin_minus_req_V'] = float(Vs.min() - vreq[sl].max())
    d = np.abs(o['dcmd'][:, :, i].astype(float))
    res['m_inst_max'] = float(d[sl].max())
    res['clip_frac_pct'] = float(100 * np.mean(d[sl].max(axis=1) > m_max))
    res['m_fund_max'] = float((Vc_pk[sl] / np.maximum(Vavg[sl], 1)[:, None]).max())
    # transfer error: delivered cycle-average transfer vs quasi-static law (15) with the measured alpha-bus voltage
    PL = o['PL'][:, i].astype(float); QL = o['QL'][:, i].astype(float)
    SL = PL + 1j * QL
    Ua = np.abs(Vb[:, 0]) / (math.sqrt(2) * 27.5e3)
    eps = c.get('eps_u', 1.0)
    req = np.maximum(0.0, np.abs(SL) - eps / 100 * Ssc * 1e6) / 2
    sx_law = np.minimum(req, KAPPA * C * np.minimum(Ua, 1.0)) * SL / np.maximum(np.abs(SL), 1e3)
    sx_a = -Sleg[:, 0]; sx_b = Sleg[:, 1]
    # compare with the law of a smoothed load (centred 20 ms mean) to remove the measurement lag partly
    SLm = ma(SL, n20)
    reqm = np.maximum(0.0, np.abs(SLm) - eps / 100 * Ssc * 1e6) / 2
    sx_lawm = np.minimum(reqm, KAPPA * C * np.minimum(Ua, 1.0)) * SLm / np.maximum(np.abs(SLm), 1e3)
    err_a = np.abs(sx_a - sx_lawm) / 1e6; err_b = np.abs(sx_b - sx_lawm) / 1e6
    res['sx_deliv_alpha_max_MVA'] = float(np.abs(sx_a[sl]).max() / 1e6)
    res['sx_law_max_MVA'] = float(np.abs(sx_lawm[sl]).max() / 1e6)
    res['xfer_err_alpha_max_MVA'] = float(err_a[sl].max()); res['xfer_err_beta_max_MVA'] = float(err_b[sl].max())
    res['xfer_err_alpha_max_pctC'] = float(100 * err_a[sl].max() * 1e6 / C)
    # steady-state part (exclude 0.15 s after the event(s) and ramps): use the 95th percentile of the error as robust measure
    res['xfer_err_alpha_p95_MVA'] = float(np.quantile(err_a[sl], 0.95))
    # unbalance (equivalent VUF of (8)) with the delivered legs
    S_al = SL + Sleg[:, 0]; S_be = Sleg[:, 1]
    vuf_emt = np.abs(S_al - S_be) / (Ssc * 1e6) * 100
    vuf_law = np.abs(SLm - 2 * sx_lawm) / (Ssc * 1e6) * 100
    res['dVUF_max_pp'] = float(np.abs(vuf_emt - vuf_law)[sl].max())
    res['VUF_emt_max_pct'] = float(vuf_emt[sl].max()); res['VUF_law_max_pct'] = float(vuf_law[sl].max())
    # saturation (power-transfer shortfall relative to the unsaturated request): requested/delivered when law is capped
    # losses (means over the analysis window)
    isq = isl ** 2
    p_cu = float((Rt * isq[sl].sum(axis=1)).mean())
    p_sink = float(o['psink'][sl, i].mean())
    iC = Cdc * np.gradient(V, dtl)
    esr = esr_tand / (2 * W0 * Cdc)
    p_esr = float(esr * np.mean(iC[sl] ** 2))
    ifl = o['if'][:, i].astype(float)
    p_f = float(par['Rf'][i] * par['hf'][i] * np.mean(ifl[sl] ** 2))
    res.update(P_cu_kW=p_cu / 1e3, P_conv_model_kW=p_sink / 1e3, P_model_total_kW=(p_cu + p_sink) / 1e3, P_filter_kW=p_f / 1e3,
               P_esr_kW=p_esr / 1e3, I_Cdc_rms_A=float(np.sqrt(np.mean(iC[sl] ** 2))), I_filter_rms_A=float(np.sqrt(np.mean(ifl[sl] ** 2))),
               ESR_mOhm=float(esr * 1e3))
    # recovery of the cycle-averaged V_dc into +-2 % after the event
    if t_event is None and 't_ev' in c:
        t_event = c['t_ev'] + o['T_pre']
    if t_event is not None:
        post = np.where((t >= t_event) & (np.arange(len(t)) <= s1))[0]
        out2 = post[np.abs(Vavg[post] / 3500 - 1) > tau_band]
        out1 = post[np.abs(Vavg[post] / 3500 - 1) > 0.01]
        res['t_recover_2pct_ms'] = float(1e3 * (t[out2[-1]] - t_event)) if len(out2) else 0.0
        res['t_recover_1pct_ms'] = float(1e3 * (t[out1[-1]] - t_event)) if len(out1) else 0.0
        res['t_event_s'] = float(t_event - o['T_pre'])
    res['mean_P_load_MW'] = float(PL[sl].mean() / 1e6)
    res['sx_over_C_max'] = float(np.abs(sx_a[sl]).max() / C)
    return res, dict(t=t, V=V, Vavg=Vavg, Ipu=Ipu, Vreq=vreq, Sleg=Sleg, sx_law=sx_lawm, d=d)
