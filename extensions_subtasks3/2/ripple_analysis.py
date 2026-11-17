"""100 Hz DC-link ripple of the two single-phase RPC legs (Scott outputs alpha, beta, 90 deg apart).

Switching-free instantaneous-power check of the analytic result
    p_dc,ac(t) = Re{ (S_a + S_b)^* ... } -> amplitude |s_a + s_b|  (= 2|s_x| for the law (15)),
plus the nonlinear energy balance of the DC link and an optional series-LC 2f filter.
All numbers printed / written to ripple_results.json come from this code.
Usage: nice -n 15 python3 ripple_analysis.py [outdir]
"""
import sys, json, numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
f0 = 50.0; w = 2*np.pi*f0
C_MVA = 11.27          # leg rating of the final design (exact model in the loop), MVA
KAPPA = 0.96
H_DC = 8e-3            # DC-link energy constant (s)
VDC = 3500.0
V_RMS = 27.5e3         # no-load busbar voltage (U = 1 pu), both feeders
res = {}

# ---------------------------------------------------------------- 1. instantaneous powers
dt = 1e-5
t = np.arange(0, 0.1, dt)            # 5 cycles = integer number of 100 Hz cycles

def leg_power(theta, S_abs):
    """Grid-absorbed instantaneous power of a leg: v = sqrt2 V cos(wt+theta), i = sqrt2 I cos(wt+theta-phi),
    S_abs = V I e^{j phi} (complex power absorbed from the busbar)."""
    V = V_RMS; S = abs(S_abs); phi = np.angle(S_abs); I = S / V
    v = np.sqrt(2)*V*np.cos(w*t + theta)
    i = np.sqrt(2)*I*np.cos(w*t + theta - phi)
    return v*i

def fit(p):
    """mean and 100 Hz amplitude/phase by least squares (exact over integer cycles)."""
    A = np.column_stack([np.ones_like(t), np.cos(2*w*t), np.sin(2*w*t)])
    c, *_ = np.linalg.lstsq(A, p, rcond=None)
    resid = p - A@c
    return c[0], np.hypot(c[1], c[2]), np.max(np.abs(resid))

def case(name, S_alpha_abs, S_beta_abs, th_a=0.0, th_b=-np.pi/2):
    """S_*_abs: complex power ABSORBED from the busbar (injection = negative real part)."""
    p_a = leg_power(th_a, S_alpha_abs); p_b = leg_power(th_b, S_beta_abs)
    p_dc = p_a + p_b                      # lossless legs: power into the DC link
    m, amp, r = fit(p_dc)
    pred = abs(np.conj(S_alpha_abs) * np.exp(1j*2*th_a) + np.conj(S_beta_abs) * np.exp(1j*2*th_b))
    d = dict(mean_MW=m/1e6, amp_MVA=amp/1e6, pred_MVA=pred/1e6, resid_MW=r/1e6)
    res.setdefault('waveform_cases', {})[name] = d
    print(f"{name:55s} mean {m/1e6:8.4f} MW  |2w| {amp/1e6:8.4f} (analytic {pred/1e6:8.4f}) MVA  nonsinus.resid {r/1e6:.1e}")
    return amp

C = C_MVA*1e6
print("== 1. instantaneous power of the two legs (Scott: theta_beta = theta_alpha - 90 deg)")
for psi_deg in (0, 30, 60, 90, -45):
    s = C*np.exp(1j*np.deg2rad(psi_deg))
    case(f"law (15), s_x=C e^(j{psi_deg:+d}deg): a injects, b absorbs", -s, s)
s = C*np.exp(1j*np.deg2rad(30))
case("same, beta lags +90 deg instead (theta_b=+90)", -s, s, th_b=+np.pi/2)
case("same, theta_a=theta_b (single-phase pair, same bus) ", -s, s, th_b=0.0)
case("both legs ABSORB s_x (balanced two-phase load, no RPC)", s, s)
lam = 0.015
sa = -(s.real*(1-2*lam) + 1j*s.imag); case("losses 1.5 %/leg: a injects P(1-3%)+jq, b absorbs P+jq", sa, s)
case("unequal: a injects kappa*C, b absorbs C (same angle)", -KAPPA*s, s)
case("reactive of opposite sign (q_b=-q_a), P equal", -s, np.conj(s))
case("b absorbs j*s_x (90 deg rotated), a injects s_x", -s, 1j*s)
case("zero transfer, load only on alpha (no ripple from RPC)", -0*s, 0*s)

# ---------------------------------------------------------------- 2. DC-link ripple (nonlinear energy balance)
print("\n== 2. DC-link voltage ripple, energy balance W = C_dc V^2/2, H = C_dc V^2/(2C)")
def ripple_unfiltered(amp_MVA, H):
    """exact: W = W0 + (amp/(2w)) sin(2wt) -> V = sqrt(2W/C_dc)."""
    eps = amp_MVA*1e6/(2*w) / (H*C)       # relative energy swing amplitude (W0 = H*C)
    Vmax = VDC*np.sqrt(1+eps); Vmin = VDC*np.sqrt(max(1-eps, 0))
    lin = amp_MVA*1e6/(2*w*(2*H*C/VDC**2)*VDC)    # DeltaV = p/(2w C_dc Vdc)
    return dict(eps=eps, dV_lin_V=lin, dV_lin_pct=100*lin/VDC, Vmax=Vmax, Vmin=Vmin,
                up_pct=100*(Vmax/VDC-1), dn_pct=100*(Vmin/VDC-1))
Cdc = 2*H_DC*C/VDC**2
res['Cdc_mF'] = Cdc*1e3
print(f"C_dc = 2 H C / V^2 = {Cdc*1e3:.3f} mF   (W0 = H C = {H_DC*C/1e3:.2f} kJ)")
tab = {}
for lab, amp in (("2C (equal legs at rating C)", 2*C_MVA), ("2*kappa*C (law (15) saturated)", 2*KAPPA*C_MVA),
                 ("(1+kappa)*C (alpha at kappa C, beta at C)", (1+KAPPA)*C_MVA)):
    r = ripple_unfiltered(amp, H_DC); tab[lab] = dict(amp_MVA=amp, **r)
    print(f"{lab:45s} amp {amp:6.2f} MVA  dV_lin {r['dV_lin_V']:6.1f} V ({r['dV_lin_pct']:5.2f} %)  exact V {r['Vmin']:.0f}..{r['Vmax']:.0f} V ({r['dn_pct']:+.1f} / {r['up_pct']:+.1f} %)")
res['ripple_H8ms'] = tab
print("\nvs. transfer level |s_x|/C and H_dc (exact +/-%, up/down)")
sweep = {}
for H in (8e-3, 15e-3, 20e-3, 30e-3, 40e-3):
    row = {}
    for frac in (0.25, 0.5, 0.75, KAPPA, 1.0):
        r = ripple_unfiltered(2*frac*C_MVA, H); row[f"{frac:.2f}"] = (round(r['dn_pct'],2), round(r['up_pct'],2))
    sweep[f"{H*1e3:.0f}ms"] = row
    print(f"H={H*1e3:4.0f} ms  C_dc={2*H*C/VDC**2*1e3:6.2f} mF ", {k: v for k, v in row.items()})
res['ripple_sweep'] = sweep
# required H so that ripple alone stays within +/-d (exact, lower side binding), at 2|s|=2C and 2kappa C
req = {}
for d in (0.10, 0.075, 0.05, 0.03):
    eps_max = min(1-(1-d)**2, (1+d)**2-1)     # lower side binds
    for lab, a in (("C", C_MVA), ("kC", KAPPA*C_MVA)):
        H = (a*1e6/w)/(C) / eps_max          # eps = amp/(2w) / (H C) with amp = 2a
        req[f"+-{d*100:g}%_{lab}"] = dict(H_ms=H*1e3, Cdc_mF=2*H*C/VDC**2*1e3)
    print(f"ripple alone within +/-{d*100:g} %: H_dc >= {req[f'+-{d*100:g}%_C']['H_ms']:.1f} ms (C_dc >= {req[f'+-{d*100:g}%_C']['Cdc_mF']:.1f} mF) for |s|=C; "
          f"{req[f'+-{d*100:g}%_kC']['H_ms']:.1f} ms for |s|=kappa C")
res['required_H'] = req

# ---------------------------------------------------------------- 3. optional series-LC 2f filter across the DC link
print("\n== 3. optional 2f series R-L-C filter (tuned to 100 Hz) across C_dc, current-source model i_in = p/V")
w2 = 2*w
def sim_filter(Cf, Q, amp_MVA, Cdc_F, detune=1.0, T=1.5, h=2e-5, ctrl=True):
    """states: V (DC link), i (filter current), vc (filter capacitor voltage), Wm (50 Hz-filtered DC-link energy),
    integ (PI of the DC-energy loop, 15 Hz, zeta 0.7, as in the averaged model).
    C_dc dV/dt = (p(t) + P_ctrl)/V - i ;  Lf di/dt = V - vc - Rf i ;  Cf dvc/dt = i.
    Cf = 0 removes the filter branch."""
    A = amp_MVA*1e6
    if Cf > 0:
        Lf = 1.0/(w2**2*Cf); Rf = (1/(w2*Cf))/Q
    else:
        Lf = Rf = 1.0
    Cf_a = Cf*detune if Cf > 0 else 1.0       # actual capacitance (tolerance / ageing), L fixed
    wn = 2*np.pi*15.0; Kp, Ki = 2*0.7*wn, wn**2
    Wref = 0.5*Cdc_F*VDC**2
    def f(tt, x):
        V, i, vc, Wm, ig = x
        p = -A*np.cos(w2*tt)                  # ac part of the net DC-link power (sign irrelevant to amplitude)
        e = (Wref - Wm)/1e6
        Pc = 1e6*(Kp*e + ig) if ctrl else 0.0
        di = (V - vc - Rf*i)/Lf if Cf > 0 else 0.0
        dv = i/Cf_a if Cf > 0 else 0.0
        return np.array([((p + Pc)/V - (i if Cf > 0 else 0.0))/Cdc_F, di, dv,
                         2*np.pi*50*(0.5*Cdc_F*V**2 - Wm), Ki*e if ctrl else 0.0])
    x = np.array([VDC, 0.0, VDC, Wref, 0.0]); n = int(T/h); keep = int(0.1/h)
    Vh = np.empty(n); ih = np.empty(n); vh = np.empty(n)
    for k in range(n):
        tt = k*h
        k1 = f(tt, x); k2 = f(tt+h/2, x+h/2*k1); k3 = f(tt+h/2, x+h/2*k2); k4 = f(tt+h, x+h*k3)
        x = x + h/6*(k1+2*k2+2*k3+k4); Vh[k], ih[k], vh[k] = x[:3]
    Vl, il, vl = Vh[-keep:], ih[-keep:], vh[-keep:]
    return dict(Vmax=Vl.max(), Vmin=Vl.min(), Vmean=Vl.mean(), up_pct=100*(Vl.max()/VDC-1), dn_pct=100*(Vl.min()/VDC-1),
                If_rms_kA=np.sqrt(np.mean(il**2))/1e3, Vcf_ac_pk=(vl.max()-vl.min())/2, Rf=Rf, Lf=Lf,
                Ploss_kW=Rf*np.mean(il**2)/1e3)
amp = 2*C_MVA
filt = {}
print(f"{'Cf mF':>6} {'Q':>3} {'detune':>6} {'Vdc min..max V':>16} {'dn/up %':>13} {'If_rms kA':>9} {'Vcf_ac pk V':>11} {'Lf mH':>6} {'Rf mOhm':>7} {'Ploss kW':>8}")
# cross-check of the ODE without filter (PI loop in place) against the closed-form energy balance
r0 = sim_filter(0, 30, amp, Cdc, 1.0)
print(f"{0:6.1f} {'-':>3} {'-':>6} {r0['Vmin']:8.0f}..{r0['Vmax']:<8.0f} {r0['dn_pct']:+6.1f}/{r0['up_pct']:+5.1f}   (no filter, ODE with PI loop; closed form -22.4/+18.2)")
filt['no_filter_ode'] = r0
for Cf_mF, Q, det in ((2, 30, 1.0), (5, 30, 1.0), (10, 30, 1.0), (15, 30, 1.0), (20, 30, 1.0), (10, 30, 0.95), (10, 30, 1.05), (10, 15, 1.0), (15, 30, 0.95), (15, 30, 1.05)):
    r = sim_filter(Cf_mF*1e-3, Q, amp, Cdc, det)
    filt[f"Cf{Cf_mF}_Q{Q}_det{det}"] = r
    print(f"{Cf_mF:6.1f} {Q:3d} {det:6.2f} {r['Vmin']:8.0f}..{r['Vmax']:<8.0f} {r['dn_pct']:+6.1f}/{r['up_pct']:+5.1f} {r['If_rms_kA']:9.2f} {r['Vcf_ac_pk']:11.0f} {r['Lf']*1e3:6.3f} {r['Rf']*1e3:7.2f} {r['Ploss_kW']:8.1f}")
res['filter'] = filt

with open(f"{OUT}/ripple_results.json", 'w') as fh:
    json.dump(res, fh, indent=1, default=float)
