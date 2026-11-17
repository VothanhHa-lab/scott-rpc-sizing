"""Helper used by the figure script: build a case from scen.py and simulate it."""
import sw_rpc as M
import scen_local as scen
cm = scen
S = scen.scenarios()
PRE = 0.6
def sim(sc, extra, sim_kw):
    s = S[sc]
    kw = dict(P=s['P'], Q=s['Q'])
    for k in ('g', 'leg_MVA', 'Ssc_thev'):
        if k in s: kw[k] = s[k]
    if 'step' in s:
        kw.update(dP_MW=s['step'], dQ_Mvar=s.get('stepQ', s['step'] * cm.TANPHI), t_ev=s['t_ev'], ramp=2e-3)
    kw.update(extra)
    return M.simulate(kw, T=PRE + s['T'], T_pre=PRE, **sim_kw)
