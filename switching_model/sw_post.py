"""Metrics of a switching run (same definitions as post.py of the averaged model where they exist)."""
import math
import numpy as np
from scipy.ndimage import maximum_filter1d, minimum_filter1d
import sw_rpc as M

W0 = M.W0


def ma(x, n):
    c = np.cumsum(np.insert(x, 0, 0, axis=0), axis=0)
    N = x.shape[0]
    idx = np.arange(N)
    lo = np.maximum(idx - n // 2, 0); hi = np.minimum(idx + n - n // 2, N)
    cnt = (hi - lo).reshape((-1,) + (1,) * (x.ndim - 1))
    return (c[hi] - c[lo]) / cnt


def phasor(x, t, n):
    z = x * np.exp(-1j * W0 * t).reshape((-1,) + (1,) * (x.ndim - 1))
    return 2 * ma(z, n)


def harmonics(x, dtl, f_max=10e3):
    """amplitude spectrum over an integer number of cycles (len(x)*dtl = k*20 ms); returns f, |X| (peak)."""
    X = np.fft.rfft(x) / len(x) * 2
    f = np.fft.rfftfreq(len(x), dtl)
    m = f <= f_max
    return f[m], np.abs(X[m])


def analyse(o, t_event=None):
    p = o['par']
    t = o['t']; dtl = t[1] - t[0]
    n20 = int(round(0.02 / dtl)); n10 = int(round(0.01 / dtl))
    sel = np.where(t >= p['T_pre'] - 1e-12)[0]
    sl = slice(sel[0] + n20, sel[-1] - n20)
    C = p['C']; Nb = p['Nb']
    Imax = math.sqrt(2) * C / M.VS0          # leg rated peak current (2 kV side)
    Irms_b = C / Nb / M.VS0                  # bridge rated rms current
    V = o['V'].astype(float)
    r = {}
    Vs = V[sl]
    r['Vmin_V'] = float(Vs.min()); r['Vmax_V'] = float(Vs.max())
    r['band_ok'] = bool(Vs.min() >= 3150 and Vs.max() <= 3850)
    r['margin_low_V'] = float(Vs.min() - 3150); r['margin_high_V'] = float(3850 - Vs.max())
    hp = 0.5 * (maximum_filter1d(V, n10) - minimum_filter1d(V, n10))
    r['ripple_halfpp_max_V'] = float(hp[sl].max()); r['ripple_pct'] = 100 * r['ripple_halfpp_max_V'] / 3500
    # switching ripple of V_dc: deviation from a 0.5-ms moving average
    nsw = max(1, int(round(0.5e-3 / dtl)))
    r['Vdc_sw_ripple_pp_V'] = float(np.ptp((V - ma(V, nsw))[sl]))
    I = o['I'].astype(float)                 # (n, 2, Nb)
    Ileg = I.sum(axis=2)
    Il = phasor(Ileg, t, n20)
    r['I1_pu_max'] = [float((np.abs(Il[sl, b]) / Imax).max()) for b in range(2)]          # fundamental, as in post.py
    r['Ileg_inst_pu_max'] = [float((np.abs(Ileg[sl, b]) / Imax).max()) for b in range(2)]
    # bridge (device) currents: instantaneous peak and rms incl. switching ripple, relative to the bridge rating
    r['Ibr_peak_pu_max'] = float((np.abs(I[sl]) / (Imax / Nb)).max())
    Irms = np.sqrt(ma(I ** 2, n20))
    r['Ibr_rms_pu_max'] = float((Irms[sl] / Irms_b).max())
    # ripple of the bridge current: deviation from the leg-average/Nb fundamental-band signal (0.5-ms moving average)
    Ib_ma = ma(I, nsw)
    r['Ibr_ripple_pp_pu_max'] = float(np.ptp((I - Ib_ma)[sl], axis=0).max() / (Imax / Nb))
    # circulating current between the Nb bridges of a leg (difference to the mean)
    r['Icirc_pu_max'] = float((np.abs(I - Ileg[:, :, None] / Nb)[sl] / (Imax / Nb)).max()) if Nb > 1 else 0.0
    # spectra over the last 20 ms*k of the run (steady state)
    ncyc = 5
    m = slice(len(t) - ncyc * n20, len(t))
    thd = []; tdd = []; vthd = []; dom = []
    for b in range(2):
        f, X = harmonics(Ileg[m, b], dtl)
        k1 = np.argmin(abs(f - 50))
        h = (f > 75)
        thd.append(float(np.sqrt(np.sum(X[h] ** 2)) / X[k1] * 100))
        tdd.append(float(np.sqrt(np.sum(X[h] ** 2)) / Imax * 100))
        j = np.argmax(X * h); dom.append([float(f[j]), float(X[j] / Imax * 100)])
        fv, XV = harmonics(o['vbus'][m, b].astype(float), dtl)
        vthd.append(float(np.sqrt(np.sum(XV[fv > 75] ** 2)) / XV[np.argmin(abs(fv - 50))] * 100))
    r['Ileg_THD_pct'] = thd; r['Ileg_TDD_pct_of_rated'] = tdd; r['Ileg_dominant_harm_Hz_pct'] = dom
    r['Vbus_THD_pct'] = vthd
    # DC-link capacitor current from C dV/dt (steady window), total rms, 100 Hz part and part above 1 kHz
    iC = p['Cdc'] * np.gradient(V[m], dtl)
    fC, XC = harmonics(iC, dtl, f_max=40e3)
    r['ICdc_rms_A'] = float(np.sqrt(np.mean(iC ** 2)))
    r['ICdc_100Hz_rms_A'] = float(XC[np.argmin(abs(fC - 100))] / math.sqrt(2))
    r['ICdc_above1k_rms_A'] = float(np.sqrt(np.sum(XC[fC > 1000] ** 2) / 2))
    r['d_max'] = float(np.abs(o['d'][sl]).max())
    r['nclip'] = int(o['nclip'])
    vb = o['vbus'].astype(float)
    Vb = phasor(vb, t, n20)
    r['U_pu_min'] = [float((np.abs(Vb[sl, b]) / (math.sqrt(2) * M.VBUS_N)).min()) for b in range(2)]
    # transferred power (cycle average) vs law (15) with measured U, alpha leg
    S_a = 0.5 * Vb[:, 0] * np.conj(Il[:, 0] / M.N_TR)
    sx = o['sx'].astype(float)
    r['xfer_err_alpha_p95_MVA'] = float(np.percentile(np.abs(np.abs(S_a[sl]) - sx[sl]) / 1e6, 95))
    if t_event is not None:
        Vavg = np.sqrt(ma(V ** 2, n20))
        after = (t >= t_event) & (t <= t_event + 0.5)
        r['Vavg_dev_after_event_pct'] = [float(100 * (Vavg[after].min() / 3500 - 1)), float(100 * (Vavg[after].max() / 3500 - 1))]
    return r
