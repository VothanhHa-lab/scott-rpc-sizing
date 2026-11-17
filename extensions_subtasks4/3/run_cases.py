"""Run the EMT test cases for the hardware configurations.  Usage: python3 run_cases.py <batch> [dt_us]
batches: search (H_dc search for A), main1 (sustained, low-U, reversal 1 s, regen plateau, low pf), main2 (+-10 MW steps), main3 (5-s reversal)"""
import sys, json, os, time
import numpy as np
import common as cm
import emt, post, scen

batch = sys.argv[1]
DT = (float(sys.argv[2]) if len(sys.argv) > 2 else 50.0) * 1e-6
LOGE = int(round(200e-6 / DT))
S = scen.scenarios()
HA = json.load(open('H_A.json'))['H_A_ms'] if os.path.exists('H_A.json') else None
PRE = 0.6


def case_kw(sc, cfg):
    s = S[sc]
    kw = dict(P=s['P'], Q=s['Q'])
    for k in ('g', 'leg_MVA', 'Ssc_thev'):
        if k in s: kw[k] = s[k]
    if 'step' in s:
        kw.update(dP_MW=s['step'], dQ_Mvar=s.get('stepQ', s['step'] * cm.TANPHI), t_ev=s['t_ev'], ramp=2e-3)
    kw.update(cfg)
    return kw


def run(runs, T_sched, tag):
    cases = [case_kw(sc, cfg) for (_, sc, cfg) in runs]
    t0 = time.time()
    o = emt.simulate(cases, T=PRE + T_sched, dt=DT, log_every=LOGE, T_pre=PRE)
    print(f'[{tag}] simulated {len(cases)} cases in {time.time() - t0:.0f} s', flush=True)
    res = {}; tr_save = {}
    for i, (name, sc, cfg) in enumerate(runs):
        tev = S[sc].get('t_ev')
        r, tr = post.analyse(o, i, cases[i], t_event=(tev + PRE) if tev is not None else None)
        r.update(name=name, scenario=sc, group=S[sc]['group'], cfg=cfg, dt_us=DT * 1e6, nclip_startup_excluded=None)
        res[name] = r
        for k in ('V', 'Vavg', 'Vreq'):
            tr_save[f'{name}__{k}'] = np.asarray(tr[k], np.float32)
        tr_save[f'{name}__Ipu'] = np.asarray(tr['Ipu'], np.float32)
        tr_save[f'{name}__d'] = np.asarray(tr['d'], np.float32)
        tr_save[f'{name}__sx_law'] = np.abs(tr['sx_law']).astype(np.float32)
        tr_save[f'{name}__sx_a'] = np.abs(tr['Sleg'][:, 0]).astype(np.float32)
        tr_save[f'{name}__PL'] = o['PL'][:, i]
        tr_save[f'{name}__U'] = o['U'][:, i]
        tr_save['t'] = np.asarray(tr['t'], np.float32)
    json.dump(res, open(f'res_{tag}.json', 'w'), indent=1, default=float)
    np.savez_compressed(f'tr_{tag}.npz', **tr_save)
    return res


if batch == 'search':
    # ripple-critical scenarios at a grid of H_dc (no filter): sustained traction plateau, regeneration plateau, low pf
    Hs = [float(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [14, 16, 17, 18, 19, 20, 22, 25]
    runs = [(f'{sc}|H{H:g}', sc, dict(H_ms=H)) for sc in ('S1_sustained', 'S3c_regen_plateau', 'S5_lowpf') for H in Hs]
    for sc in ('S1_sustained', 'S3c_regen_plateau', 'S5_lowpf'):
        S[sc]['T'] = 1.0
    run(runs, 1.0, 'search' + (sys.argv[4] if len(sys.argv) > 4 else ''))
elif batch == 'main1':
    cfgs = {'ref8': scen.CONFIGS['ref8'], 'A': scen.config_A(HA), 'A26': scen.config_A(26.2), 'B10': scen.CONFIGS['B10'], 'B5': scen.CONFIGS['B5']}
    scs = ['S1_sustained', 'S2_lowU', 'S2b_lowU_sag5', 'S2c_lowU_weak500', 'S2d_overV', 'S3a_rev1s', 'S3c_regen_plateau', 'S5_lowpf']
    runs = [(f'{sc}|{cn}', sc, cfg) for sc in scs for cn, cfg in cfgs.items()]
    run(runs, 3.0, 'main1')
elif batch == 'main2':
    cfgs = {'ref8': scen.CONFIGS['ref8'], 'A': scen.config_A(HA), 'A26': scen.config_A(26.2), 'B10': scen.CONFIGS['B10'], 'B5': scen.CONFIGS['B5']}
    scs = ['S4a_step+10_seg', 'S4b_step-10_seg', 'S4c_step+10_15MW', 'S4d_step-10_25MW', 'S6_step+20_pf90']
    runs = [(f'{sc}|{cn}', sc, cfg) for sc in scs for cn, cfg in cfgs.items()]
    runs += [(f'{sc}|A_noFF', sc, dict(scen.config_A(HA), ff=0)) for sc in scs]
    runs += [(f'{sc}|B10_noFF', sc, dict(scen.CONFIGS['B10'], ff=0)) for sc in scs]
    run(runs, 2.0, 'main2')
elif batch == 'main3':
    cfgs = {'ref8': scen.CONFIGS['ref8'], 'A': scen.config_A(HA), 'A26': scen.config_A(26.2), 'B10': scen.CONFIGS['B10'], 'B5': scen.CONFIGS['B5']}
    runs = [(f'S3b_rev5s|{cn}', 'S3b_rev5s', cfg) for cn, cfg in cfgs.items()]
    run(runs, 4.0, 'main3')
elif batch == 'main4':
    cfgs = {'ref8': scen.CONFIGS['ref8'], 'A': scen.config_A(HA), 'A26': scen.config_A(26.2), 'B10': scen.CONFIGS['B10'], 'B5': scen.CONFIGS['B5']}
    runs = [(f'{sc}|{cn}', sc, cfg) for sc in ('S1b_sustained_w22', 'S7_up1s') for cn, cfg in cfgs.items()]
    run(runs, 3.0, 'main4')
