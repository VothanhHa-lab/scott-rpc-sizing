"""Operating points / scenarios for the EMT runs (all from the stored base weeks, law (15), C = 11.27 MVA, eps_u = 1 %, Ssc = 750 MVA)."""
import json, os
import numpy as np
import common as cm

def knots(k, a, n):
    P, Q = cm.week(k); return P[a:a + n + 1].copy(), Q[a:a + n + 1].copy()

def zero_cross(P):
    for j in range(len(P) - 1):
        if P[j] > 0 >= P[j + 1]:
            return j + P[j] / (P[j] - P[j + 1])
    return None

def scenarios():
    S = {}
    # 1 sustained high |s_x|/C (week 19 = idx 18, 10-s mean of |s_x|/C = 0.948, i.e. kappa C U)
    P, Q = knots(18, 33092, 3); S['S1_sustained'] = dict(group='sustained', P=P, Q=Q, T=3.0, src='base week 19, samples 33092-33095')
    # 1b sustained transfer from the independent search of the load-flow sub-task (/home/claude/subtasks4/2/emt_points.json, A rank 1)
    P, Q = knots(22, 410862, 3); S['S1b_sustained_w22'] = dict(group='sustained', P=P, Q=Q, T=3.0, src='base_w022, samples 410862-410865 (643 s run with |s_x|/C >= 0.90, U_alpha 0.96)')
    # 1c largest 1-s increase of the transfer (point D_step_up_1s rank 1 of emt_points.json; week 16 = idx 15)
    P, Q = knots(15, 372158, 3); S['S7_up1s'] = dict(group='steps', P=P, Q=Q, T=3.0, t_ev=0.5, src='base week 16, samples 372158-372161 (largest 1-s increase, 11.5 to 21.9 MW)')
    # 2 low busbar voltage near saturation: the sample with the lowest alpha-busbar voltage (U=0.961, S_L=68.3 MVA, week 13 = idx 12)
    P, Q = knots(12, 581225, 3)
    S['S2_lowU'] = dict(group='lowU', P=P, Q=Q, T=3.0, src='base week 13, samples 581225-581228 (lowest U of the 60 weeks)')
    S['S2b_lowU_sag5'] = dict(group='lowU', P=P, Q=Q, T=3.0, g=0.95, src='same, feeder source voltage 0.95 pu (grid sag) - synthetic stress')
    S['S2c_lowU_weak500'] = dict(group='lowU', P=P, Q=Q, T=3.0, Ssc_thev=500.0, src='same, actual short-circuit power 500 MVA in the feeder impedance (law threshold still for 750 MVA)')
    S['S2d_overV'] = dict(group='lowU', P=P, Q=Q, T=3.0, g=1.06, src='same, feeder source voltage 1.06 pu - synthetic stress (saturation beyond m_max)')
    # 3 traction -> regeneration
    P, Q = knots(33, 545385, 3); S['S3a_rev1s'] = dict(group='reversal', P=P, Q=Q, T=3.0, t_ev=zero_cross(P), src='base week 34, samples 545385-545388 (fastest 1-s fall through zero)')
    P, Q = knots(11, 27645, 4); S['S3b_rev5s'] = dict(group='reversal', P=P, Q=Q, T=4.0, t_ev=zero_cross(P), src='base week 12, samples 27645-27649 (33.6 to -8.8 MW in 5 s)')
    P, Q = knots(48, 585624, 3); S['S3c_regen_plateau'] = dict(group='reversal', P=P, Q=Q, T=3.0, src='base week 49, samples 585624-585627 (sustained regeneration, |s_x| = kappa C)')
    # 4 +-10 MW steps (as in the previous dynamic check), step at 0.5 s after the start of the schedule, 2 ms ramp
    a0 = 462083 + 38
    P, Q = knots(0, a0, 2)
    for nm, (PP, QQ), st in (('S4a_step+10_seg', (P, Q), +10.0), ('S4b_step-10_seg', (P, Q), -10.0), ('S4c_step+10_15MW', cm.const(15.0, 2), +10.0), ('S4d_step-10_25MW', cm.const(25.0, 2), -10.0)):
        S[nm] = dict(group='steps', P=PP, Q=QQ, T=2.0, t_ev=0.5, step=st, src='week 1 segment (15.1 MW) / constant baseline, step %+d MW at 0.5 s' % st)
    P, Q = cm.const(10.0, 2)
    S['S6_step+20_pf90'] = dict(group='steps', P=P, Q=Q, T=2.0, t_ev=0.5, step=+20.0, stepQ=20.0 * np.tan(np.arccos(0.9)), src='10 MW -> 30 MW step at 0.5 s, step power factor 0.90 lagging (stress: beta leg at its limit)')
    # 5 low power factor load (pf 0.90 lagging) on the sustained plateau: adverse reactive operating point for the modulation index
    P, Q = knots(18, 33092, 3)
    S['S5_lowpf'] = dict(group='lowpf', P=np.array([30.0] * 4), Q=np.array([30.0 * np.tan(np.arccos(0.9))] * 4), T=3.0, src='synthetic constant 30 MW at pf 0.90 lagging')
    return S

CONFIGS = {
    'ref8': dict(H_ms=8.0),
    'B10': dict(H_ms=8.0, Cf_mF=10.0, Qf=30.0),
    'B5': dict(H_ms=8.0, Cf_mF=5.0, Qf=30.0),
}
def config_A(H):
    return dict(H_ms=float(H))
