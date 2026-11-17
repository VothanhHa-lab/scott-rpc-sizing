"""Assumed leg interface: single-phase coupling transformer 27.5 kV / 2.0 kV (rating = C, u_k = 10 %) + single-phase
full-bridge / NPC with V_dc = 3.5 kV.  Checks the DC voltage needed for linear modulation.
Usage: python3 interface_check.py [outdir]"""
import sys, json, numpy as np
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
C = 11.27e6; Vp = 27.5e3; Vs = 2.0e3; uk = 0.10; f = 50.0; Vdc = 3500.0
M_MAX = 0.95            # assumed upper limit of the linear modulation index (dead time, control margin)
res = dict(n=Vp/Vs, I_sec_rated_A=C/Vs, I_sec_peak_A=np.sqrt(2)*C/Vs, I_pri_rated_A=C/Vp,
           Xt_sec_mOhm=uk*Vs**2/C*1e3, Lt_sec_uH=uk*Vs**2/C/(2*np.pi*f)*1e6)
print({k: round(v, 4) for k, v in res.items()})

def Vc_worst(U, x=uk, i=1.0):
    """converter terminal voltage rms, Vc = Vs + j x I (alpha injects) / Vs - j x I (beta absorbs, unity-pf angle
    swept); worst case over the current angle at |I| = i * rated: |Vc| = U Vs sqrt(1+...) max = Vs (U + x i)."""
    ang = np.linspace(0, 2*np.pi, 3601)
    Vs_ph = U*Vs
    Vc = np.abs(Vs_ph + 1j*x*Vs*i*np.exp(1j*ang))      # rated current, drop x*Vs (pu on C and 2.0 kV base)
    return Vc.max(), Vc.min(), Vs_ph*np.sqrt(1+(x*i)**2)   # worst, best, unity-pf-in-quadrature value
tab = {}
print("\nU(pu)  Vs(kV)  Vc,max(kV rms)  peak(kV)  m @3.5 kV  m @3.27  m @3.15 kV | unity-pf Vc peak")
for U in (0.8, 0.9, 1.0, 1.055):
    vmax, vmin, vup = Vc_worst(U); pk = np.sqrt(2)*vmax
    row = dict(Vs_kV=U*Vs/1e3, Vc_max_kV=vmax/1e3, Vc_peak_kV=pk/1e3,
               m_3500=pk/Vdc, m_3270=pk/3270, m_3150=pk/3150, Vdc_min_req_kV=pk/M_MAX/1e3)
    tab[f"U={U}"] = row
    print(f"{U:5.3f} {U*Vs/1e3:7.3f} {vmax/1e3:15.3f} {pk/1e3:9.3f} {pk/Vdc:10.3f} {pk/3270:8.3f} {pk/3150:9.3f}  | {np.sqrt(2)*vup/1e3:.3f}")
res['modulation'] = tab
# no-load and min margins
res['m_noload_3500'] = np.sqrt(2)*Vs/Vdc
res['m_noload_3150'] = np.sqrt(2)*Vs/3150
print(f"\nno-load m = sqrt2*2.0/3.5 = {res['m_noload_3500']:.3f}; at V_dc = 3.15 kV: {res['m_noload_3150']:.3f}")
# DC-link voltage reached by the 100 Hz ripple (from ripple_results.json), m for each
try:
    R = json.load(open(f"{OUT}/ripple_results.json"))
    pk = np.sqrt(2)*Vc_worst(1.0)[0]
    chk = {}
    for name, vmin in (("no filter, 2C transfer (exact -22.4 %)", R['ripple_H8ms']['2C (equal legs at rating C)']['Vmin']),
                       ("filter Cf=10 mF (-1.0 %)", R['filter']['Cf10_Q30_det1.0']['Vmin'])):
        chk[name] = dict(Vdc_min=vmin, m_peak=pk/vmin)
        print(f"V_dc,min {vmin:7.0f} V ({name}): m = {pk/vmin:.3f} at U=1, rated current, worst current angle")
    res['m_with_ripple'] = chk
except Exception as e:
    print('ripple_results.json not found:', e)
# alternatives of the secondary voltage
alt = {}
print("\nalternative secondary voltages (U = 1, rated current, worst angle): m at V_dc,min = 3.15 kV and V_dc = 3.5 kV")
for vs in (1.8e3, 1.9e3, 2.0e3, 2.1e3):
    pk = np.sqrt(2)*vs*(1+uk)
    alt[f"{vs/1e3:.1f}kV"] = dict(n=Vp/vs, I_sec_kA=C/vs/1e3, m_3150=pk/3150, m_3500=pk/Vdc)
    print(f"Vs={vs/1e3:.1f} kV n={Vp/vs:6.2f} I_sec={C/vs/1e3:5.2f} kA  m(3.15)={pk/3150:.3f}  m(3.5)={pk/Vdc:.3f}")
res['alternatives'] = alt
json.dump(res, open(f"{OUT}/interface_results.json", 'w'), indent=1, default=float)
