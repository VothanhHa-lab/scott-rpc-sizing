"""Run the switching-model cases.  Usage: python run_sw.py <batch>
batches: val  (C = 11.27 MVA, C_dc = 48.2 mF: averaged-switch digital model and switching model vs emt.py results)
         main (final design C = 11.5 MVA, H_dc = 26.2 ms -> 49.2 mF: switching Nb=2/fc=1 kHz (base), Nb=1, averaged)
         dt   (dt = 1 us vs 2 us, base configuration)
         h8   (H_dc = 8 ms, switching base: does the band violation of the averaged study reappear?)"""
import sys, json, time
import numpy as np
import sw_rpc as M, sw_post as P
import scen_local as scen
cm = scen

S = scen.scenarios()
PRE = 0.6
ORDER = ['S1_sustained', 'S1b_sustained_w22', 'S2_lowU', 'S3a_rev1s', 'S3b_rev5s', 'S3c_regen_plateau',
         'S4a_step+10_seg', 'S4b_step-10_seg', 'S4c_step+10_15MW', 'S4d_step-10_25MW', 'S5_lowpf', 'S7_up1s',
         'S2b_lowU_sag5', 'S2c_lowU_weak500', 'S2d_overV', 'S6_step+20_pf90']
STRESS = {'S2b_lowU_sag5', 'S2c_lowU_weak500', 'S2d_overV', 'S6_step+20_pf90'}


def case_kw(sc, extra):
    s = S[sc]
    kw = dict(P=s['P'], Q=s['Q'])
    for k in ('g', 'leg_MVA', 'Ssc_thev'):
        if k in s: kw[k] = s[k]
    if 'step' in s:
        kw.update(dP_MW=s['step'], dQ_Mvar=s.get('stepQ', s['step'] * cm.TANPHI), t_ev=s['t_ev'], ramp=2e-3)
    elif s.get('t_ev') is not None:
        kw.update(t_ev=s['t_ev'])            # reversal instant (no step): only used to evaluate the event window
    kw.update(extra)
    return kw


def run_one(sc, extra, sim_kw, save_trace=None):
    kw = case_kw(sc, extra)
    t0 = time.time()
    o = M.simulate(kw, T=PRE + S[sc]['T'], T_pre=PRE, **sim_kw)
    tev = S[sc].get('t_ev')
    r = P.analyse(o, t_event=(tev + PRE) if tev is not None else None)
    r.update(scenario=sc, stress=sc in STRESS, cpu_s=time.time() - t0, sim=dict(sim_kw), C_MVA=o['par']['C'] / 1e6,
             Cdc_mF=o['par']['Cdc'] * 1e3, Kp=o['Kp'], Kr=o['Kr'])
    if save_trace is not None:
        k = max(1, int(round(20e-6 / (o['t'][1] - o['t'][0]))))
        save_trace.update({f'{sc}__{n}': np.asarray(o[n][::k], np.float32) for n in ('t', 'V', 'I', 'vbus', 'd', 'sx', 'PL', 'iref')})
    return r


batch = sys.argv[1]
res = {}; tr = {}
if batch == 'val':
    # results of the averaged-switch model emt.py of the paper (H_dc = 26.2 ms at C = 11.27 MVA, 48.2 mF, dt = 50 us)
    emt = json.load(open('emt_A26_reference.json'))
    for sc in ORDER:
        for mode, sk in (('avg', dict(avg_mode=True)), ('sw', dict(Nb=2, fc=1000.0))):
            r = run_one(sc, dict(C=11.270562, Cdc_mF=48.2), sk)
            res[f'{sc}|{mode}'] = r
            print(f"{sc:20s} {mode:3s} V {r['Vmin_V']:.0f}/{r['Vmax_V']:.0f}  emt {emt[sc]['Vmin_V']:.0f}/{emt[sc]['Vmax_V']:.0f}  "
                  f"I1 {r['I1_pu_max'][0]:.3f}/{r['I1_pu_max'][1]:.3f} emt {emt[sc]['I_pu_max'][0]:.3f}/{emt[sc]['I_pu_max'][1]:.3f}", flush=True)
    res['_emt'] = emt
elif batch == 'main':
    cfgs = {'sw_Nb2_fc1k': dict(Nb=2, fc=1000.0, dt=1e-6), 'sw_Nb1_fc1k': dict(Nb=1, fc=1000.0, dt=1e-6), 'avg': dict(avg_mode=True, dt=1e-6)}
    for name, sk in cfgs.items():
        for sc in ORDER:
            r = run_one(sc, dict(C=11.5, H_ms=26.2), sk, save_trace=tr if name == 'sw_Nb2_fc1k' else None)
            res[f'{sc}|{name}'] = r
            print(f"{name:12s} {sc:20s} V {r['Vmin_V']:.0f}/{r['Vmax_V']:.0f} I1 {r['I1_pu_max'][0]:.3f}/{r['I1_pu_max'][1]:.3f} "
                  f"Ibr_pk {r['Ibr_peak_pu_max']:.3f} Ibr_rms {r['Ibr_rms_pu_max']:.3f} THD {r['Ileg_THD_pct'][0]:.1f}/{r['Ileg_THD_pct'][1]:.1f} "
                  f"d {r['d_max']:.3f} clip {r['nclip']}", flush=True)
elif batch == 'dt':
    for sc in ('S1_sustained', 'S4a_step+10_seg', 'S6_step+20_pf90'):
        for dt in (2e-6, 1e-6, 0.5e-6):
            r = run_one(sc, dict(C=11.5, H_ms=26.2), dict(Nb=2, fc=1000.0, dt=dt))
            res[f'{sc}|dt{dt * 1e6:g}'] = r
            print(sc, dt, round(r['Vmin_V'],1), round(r['Vmax_V'],1), [round(x,4) for x in r['I1_pu_max']], round(r['Ibr_peak_pu_max'],4), round(r['Ibr_rms_pu_max'],4), [round(x,2) for x in r['Ileg_TDD_pct_of_rated']], flush=True)
elif batch == 'h8':
    for sc in ORDER:
        r = run_one(sc, dict(C=11.5, H_ms=8.0), dict(Nb=2, fc=1000.0, dt=1e-6))
        res[f'{sc}|H8'] = r
        print(sc, round(r['Vmin_V']), round(r['Vmax_V']), r['band_ok'], flush=True)
json.dump(res, open(f'res_{batch}.json', 'w'), indent=1, default=float)
if tr:
    np.savez_compressed(f'tr_{batch}.npz', **tr)
