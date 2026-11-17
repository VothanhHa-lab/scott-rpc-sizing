"""Summary JSON/CSV/LaTeX tables from res_main*.json (literal numbers)."""
import json, csv
import numpy as np
res = {}
for tag in ('main1', 'main2', 'main3', 'main4'):
    try: res.update(json.load(open(f'res_{tag}.json')))
    except Exception as e: print('missing', tag)
HA = json.load(open('H_A.json'))['H_A_ms']
C = 11.270562
cdc = lambda H: 2 * H * 1e-3 * C * 1e6 / 3500 ** 2 * 1e3
CFG = ['ref8', 'A', 'A26', 'B10', 'B5']
NAME = {'A26': 'A: $H_\\mathrm{dc}=26.2$ ms', 'ref8': 'Reference, $H_\\mathrm{dc}=8$ ms, no filter', 'A': f'A: larger $C_\\mathrm{{dc}}$ ($H_\\mathrm{{dc}}={HA:g}$ ms)',
        'B10': 'B: 8 ms + filter $C_f=10$ mF', 'B5': 'B: 8 ms + filter $C_f=5$ mF'}
DESIGN = ['S1_sustained', 'S1b_sustained_w22', 'S2_lowU', 'S3a_rev1s', 'S3b_rev5s', 'S3c_regen_plateau', 'S4a_step+10_seg', 'S4b_step-10_seg',
          'S4c_step+10_15MW', 'S4d_step-10_25MW', 'S5_lowpf', 'S7_up1s']
STRESS = ['S2b_lowU_sag5', 'S2c_lowU_weak500', 'S2d_overV', 'S6_step+20_pf90']
get = lambda sc, cn: res.get(f'{sc}|{cn}')
summ = {}
for cn in CFG:
    rows = [get(s, cn) for s in DESIGN if get(s, cn)]
    rs = [get(s, cn) for s in STRESS if get(s, cn)]
    def agg(R, k, f, idx=None):
        v = [r[k] if idx is None else r[k][idx] for r in R if r.get(k) is not None]
        return f(v) if v else None
    d = dict(n_design=len(rows),
             Vmin=agg(rows, 'Vmin_V', min), Vmax=agg(rows, 'Vmax_V', max), ripple_pct=agg(rows, 'ripple_pct', max),
             Ia=agg(rows, 'I_pu_max', max, 0), Ib=agg(rows, 'I_pu_max', max, 1), m_inst=agg(rows, 'm_inst_max', max),
             Vreq=agg(rows, 'Vdc_req_max_V', max), clip=agg(rows, 'clip_frac_pct', max),
             xfer_err_p95=agg(rows, 'xfer_err_alpha_p95_MVA', max), xfer_err_max=agg(rows, 'xfer_err_alpha_max_MVA', max),
             Vavg_dev_max_pct=max(abs(r['Vavg_min_pct']) for r in rows) if rows else None,
             Vavg_dev_max_pct_hi=max(abs(r['Vavg_max_pct']) for r in rows) if rows else None,
             t_rec_max=agg(rows, 't_recover_2pct_ms', max),
             Pf_full=(get('S1_sustained', cn) or {}).get('P_filter_kW'), Pesr_full=(get('S1_sustained', cn) or {}).get('P_esr_kW'),
             stress=dict(Vmin=agg(rs, 'Vmin_V', min), Vmax=agg(rs, 'Vmax_V', max), Ia=agg(rs, 'I_pu_max', max, 0), Ib=agg(rs, 'I_pu_max', max, 1),
                         m_inst=agg(rs, 'm_inst_max', max), clip=agg(rs, 'clip_frac_pct', max)))
    d['margin_Vmin_V'] = d['Vmin'] - max(3150.0, d['Vreq'])
    d['band_ok'] = bool(d['Vmin'] >= 3150 and d['Vmax'] <= 3850)
    d['mod_ok'] = bool(d['m_inst'] <= 0.95)   # pointwise criterion (Vmin vs the maximum requirement is conservative, the two do not coincide in time)
    d['current_ok'] = bool(d['Ia'] <= 1.0 and d['Ib'] <= 1.0)
    summ[cn] = d
json.dump(summ, open('summary.json', 'w'), indent=1, default=float)
# csv of all runs
keys = ['name', 'scenario', 'group', 'Vmin_V', 'Vmax_V', 'Vavg_min_pct', 'Vavg_max_pct', 'ripple_pct', 'band_ok', 't_outside_band_ms', 'I_pu_max', 'I_inst_pu_max', 'U_pu_min',
        'Vdc_req_max_V', 'Vmin_minus_req_V', 'm_inst_max', 'm_fund_max', 'clip_frac_pct', 'xfer_err_alpha_max_MVA', 'xfer_err_alpha_p95_MVA', 'dVUF_max_pp',
        'P_cu_kW', 'P_conv_model_kW', 'P_filter_kW', 'P_esr_kW', 'I_Cdc_rms_A', 'I_filter_rms_A', 't_recover_2pct_ms', 't_recover_1pct_ms']
with open('all_runs.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(keys)
    for k, r in res.items():
        w.writerow([json.dumps(r.get(q)) if isinstance(r.get(q), list) else r.get(q) for q in keys])

def f0(x): return f'{x:.0f}'
def f1(x): return f'{x:.1f}'
def f2(x): return f'{x:.2f}'
def f3(x): return f'{x:.3f}'
L = []
# ---- Table A: summary per configuration (design scenarios)
L.append('% ---- Table EMT-1: summary per hardware configuration (worst case over the 12 design test cases)')
L.append('\\begin{table}[htbp]\n\\centering\n\\caption{\\label{tEMT1}Python averaged-switch EMT-type model, final design ($C^*=11.27$~MVA, $\\varepsilon_u^*=1\\%$, $S_\\mathrm{sc}=750$~MVA): worst case over the twelve test cases of Table~\\ref{tEMT2} for the five DC-link configurations (reference, A at two values of $H_\\mathrm{dc}$, B at two values of $C_f$). $m$: instantaneous modulation function; $V_\\mathrm{dc,req}$: DC voltage required for $m\\le0.95$ at the operating point (peak over the test cases); 100~Hz ripple: half the peak-to-peak variation at sustained transfer; band / $m$ / $I$: all test cases keep $v_\\mathrm{dc}$ in 3.15--3.85~kV, $|d|\\le0.95$ and both leg currents $\\le1$~pu; margin: $\\min v_\\mathrm{dc}-\\max(3150\\,\\mathrm{V},V_\\mathrm{dc,req})$; stress: min $v_\\mathrm{dc}$ (kV) / max $|d|$ over the four stress cases of Table~\\ref{tEMT3}.}')
L.append('\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}{lccccccccccc}\n\\hline')
L.append('Configuration & $C_\\mathrm{dc}$ (mF) & $v_\\mathrm{dc}$ min / max (kV) & 100~Hz ripple $\\pm$ (\\%) & $I_\\alpha$ / $I_\\beta$ (pu) & max $|d|$ & $V_\\mathrm{dc,req}$ (kV) & margin (V) & band / $m$ / $I$ & stress\\\\\n\\hline')
cdcs = {'ref8': cdc(8), 'A': cdc(HA), 'A26': cdc(26.2), 'B10': cdc(8), 'B5': cdc(8)}
for cn in CFG:
    d = summ[cn]
    L.append(f"{NAME[cn]} & {f1(cdcs[cn])} & {f2(d['Vmin']/1e3)} / {f2(d['Vmax']/1e3)} & {f1(get('S1_sustained', cn)['ripple_pct'])} & {f3(d['Ia'])} / {f3(d['Ib'])} & {f3(d['m_inst'])} & {f2(d['Vreq']/1e3)} & {f0(d['margin_Vmin_V'])} & {'yes' if d['band_ok'] else 'no'} / {'yes' if d['mod_ok'] else 'no'} / {'yes' if d['current_ok'] else 'no'} & {f2(d['stress']['Vmin']/1e3)} / {f2(d['stress']['m_inst'])}\\\\")
L.append('\\hline\n\\end{tabular}\n\\end{adjustbox}\n\\end{table}\n')
# ---- Table B: per case
CASE = [('S1_sustained', 'sustained transfer (week 19)'), ('S1b_sustained_w22', 'sustained transfer (week 23)'), ('S2_lowU', 'lowest busbar voltage, 68 MW'),
        ('S3a_rev1s', 'reversal, 1 s'), ('S3b_rev5s', 'reversal, 5 s'), ('S3c_regen_plateau', 'regeneration plateau'), ('S4a_step+10_seg', '$+10$ MW step (15 MW)'),
        ('S4b_step-10_seg', '$-10$ MW step (15 MW)'), ('S4c_step+10_15MW', '$+10$ MW step, const. 15 MW'), ('S4d_step-10_25MW', '$-10$ MW step, const. 25 MW'),
        ('S5_lowpf', 'pf 0.90 load, 30 MW'), ('S7_up1s', 'largest 1-s increase')]
L.append('% ---- Table EMT-2: per test case, v_dc min / max (kV) for the five configurations; max |d|; recovery')
L.append('\\begin{table}[htbp]\n\\centering\n\\caption{\\label{tEMT2}Instantaneous DC-link voltage (min / max in kV) per test case and configuration; $I_\\alpha/I_\\beta$: leg currents (pu of rated, rms) and max $|d|$ for configuration B (10~mF); $t_{2\\%}$: recovery of the 20-ms mean $v_\\mathrm{dc}$ to $\\pm2\\%$ after the event (configuration A 18 ms / B 10~mF). Test-case labels follow the zero-based file index of the stored base weeks (file base\\_w018 is called week 19). ``--'': no event.}')
L.append('\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}{lcccccccccc}\n\\hline')
L.append('Test case & ref. & A 18 ms & A 26.2 ms & B 10~mF & B 5~mF & $I_\\alpha/I_\\beta$ & max $|d|$ & $V_\\mathrm{dc,req}$ (kV) & $t_{2\\%}$ (ms)\\\\\n\\hline')
for sc, lab in CASE:
    if not get(sc, 'B10'): continue
    cells = [f"{f2(get(sc,cn)['Vmin_V']/1e3)} / {f2(get(sc,cn)['Vmax_V']/1e3)}" for cn in CFG]
    b = get(sc, 'B10'); a = get(sc, 'A')
    tr = f"{a.get('t_recover_2pct_ms', float('nan')):.0f} / {b.get('t_recover_2pct_ms', float('nan')):.0f}" if 't_recover_2pct_ms' in b else '--'
    L.append(f"{lab} & " + ' & '.join(cells) + f" & {f2(b['I_pu_max'][0])} / {f2(b['I_pu_max'][1])} & {f2(b['m_inst_max'])} & {f2(b['Vdc_req_max_V']/1e3)} & {tr}\\\\")
L.append('\\hline\n\\end{tabular}\n\\end{adjustbox}\n\\end{table}\n')
# ---- Table C: stress and no-FF
SC2 = [('S2b_lowU_sag5', 'feeder source $-5\\%$'), ('S2c_lowU_weak500', 'weak grid, $S_\\mathrm{sc}=500$ MVA'), ('S2d_overV', 'feeder source $+6\\%$'), ('S6_step+20_pf90', '$+20$ MW step, pf 0.90')]
L.append('% ---- Table EMT-3: stress cases and runs without feed-forward')
L.append('\\begin{table}[htbp]\n\\centering\n\\caption{\\label{tEMT3}Stress cases (min / max $v_\\mathrm{dc}$ in kV, max $|d|$, percentage of time with $|d|>0.95$) and the $\\pm10$~MW steps without power feed-forward (min / max of the 20-ms mean $v_\\mathrm{dc}$ in \\%).}')
L.append('\\begin{adjustbox}{max width=\\textwidth}\n\\begin{tabular}{lccccc}\n\\hline')
L.append('Stress case & ref. & A 18 ms & A 26.2 ms & B 10~mF & B 5~mF\\\\\n\\hline')
for sc, lab in SC2:
    if not get(sc, 'A'): continue
    cells = []
    for cn in CFG:
        r = get(sc, cn); cells.append(f"{f2(r['Vmin_V']/1e3)}/{f2(r['Vmax_V']/1e3)}; {f2(r['m_inst_max'])}; {f1(r['clip_frac_pct'])}\\%")
    L.append(f"{lab} & " + ' & '.join(cells) + '\\\\')
L.append('\\hline\n')
L.append('Steps without FF & & A 18 ms & B 10~mF & &\\\\\n\\hline')
for sc, lab in [('S4a_step+10_seg', '$+10$ MW (15 MW)'), ('S4b_step-10_seg', '$-10$ MW (15 MW)'), ('S4c_step+10_15MW', '$+10$ MW (const.)'), ('S4d_step-10_25MW', '$-10$ MW (const. 25 MW)'), ('S6_step+20_pf90', '$+20$ MW, pf 0.90')]:
    a = get(sc, 'A_noFF'); b = get(sc, 'B10_noFF')
    if not a: continue
    L.append(f"{lab} & & {f1(a['Vavg_min_pct'])} / {f1(a['Vavg_max_pct'])} & {f1(b['Vavg_min_pct'])} / {f1(b['Vavg_max_pct'])} & &\\\\")
L.append('\\hline\n\\end{tabular}\n\\end{adjustbox}\n\\end{table}\n')

# ---- Table D: additional losses
LA = json.load(open('losses_annual.json'))
L.append('% ---- Table EMT-4: additional losses of the DC-link solutions')
L.append('\\begin{table}[htbp]\n\\centering\n\\caption{\\label{tEMT4}Additional losses of the DC-link solutions at full transfer ($|s_x|=0.94\\,C$) and annual energy over the 60 base weeks (mean $(s_x/C)^2=%.4f$, price 80~USD/MWh as in the cost model). Filter loss from the series resistance $R_f$ of the 100~Hz branch ($Q=30$); capacitor ESR loss of the DC link under the assumption $\\tan\\delta=0.002$ at 100~Hz (assumption, not a datasheet value).}' % LA['mean_sxC2'])
L.append('\\begin{tabular}{lcccc}\n\\hline')
L.append('Configuration & loss at full transfer (kW) & loss at $|s_x|=C$ (kW) & energy (MWh/yr) & cost (kUSD/yr)\\\\\n\\hline')
for cn, lab in (('A', 'A: $H_\\mathrm{dc}=18$ ms (ESR)'), ('A26', 'A: $H_\\mathrm{dc}=26.2$ ms (ESR)'), ('B10', 'B: 8 ms + $C_f=10$ mF'), ('B5', 'B: 8 ms + $C_f=5$ mF')):
    d = LA[cn]
    if cn in ('A', 'A26'):
        L.append(f"{lab} & {d['Pesr_full_kW']:.1f} & {d['Pesr_full_kW']/0.9412**2:.1f} & {d['MWh_yr']:.1f} & {d['kUSD_yr']:.2f}\\\\")
    else:
        L.append(f"{lab} & {d['Pf_full_kW']:.0f} & {d['kW_at_C']:.0f} & {d['MWh_yr']:.0f} & {d['kUSD_yr']:.1f}\\\\")
L.append('\\hline\n\\end{tabular}\n\\end{table}\n')
open('tables.tex', 'w').write('\n'.join(L))
# markdown summary
md = ['| config | C_dc mF | Vmin kV | Vmax kV | ripple % | I_a | I_b | max d | Vreq kV | margin V | band | m<=0.95 | stress Vmin | stress max d |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for cn in CFG:
    d = summ[cn]
    md.append(f"| {cn} | {cdcs[cn]:.1f} | {d['Vmin']/1e3:.3f} | {d['Vmax']/1e3:.3f} | {d['ripple_pct']:.1f} | {d['Ia']:.3f} | {d['Ib']:.3f} | {d['m_inst']:.3f} | {d['Vreq']/1e3:.3f} | {d['margin_Vmin_V']:.0f} | {d['band_ok']} | {d['mod_ok']} | {d['stress']['Vmin']/1e3:.3f} | {d['stress']['m_inst']:.3f} |")
open('summary.md', 'w').write('\n'.join(md))
print('\n'.join(md))
