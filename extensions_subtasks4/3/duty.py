import json, numpy as np, common as cm
from rpc_sizing import rpc as R
C=cm.C_STAR; acc=[];acc1=[]
for k in range(60):
    P,Q=cm.week(k); sx,_=R.compensate(P,Q,C,1.0,750.0); acc.append(np.mean((sx/C)**2)); acc1.append(np.mean(sx/C))
m2=float(np.mean(acc)); print('mean (sx/C)^2 over 60 base weeks',m2,'mean sx/C',np.mean(acc1))
r=json.load(open('res_main1.json'))
out=dict(mean_sxC2=m2)
for cn in ('B10','B5'):
    Pf=r[f'S1_sustained|{cn}']['P_filter_kW']; sxc=r[f'S1_sustained|{cn}']['sx_over_C_max']
    k=Pf/sxc**2   # kW at |sx|=C
    E=k*m2*8766/1e3 # MWh/yr
    out[cn]=dict(Pf_full_kW=Pf, sxC=sxc, kW_at_C=k, MWh_yr=E, kUSD_yr=E*80/1e3)
    print(cn,out[cn])
# ESR of A (assumption tan d =0.002), per full transfer
for cn in ('A','A26'):
    out[cn]=dict(Pesr_full_kW=r[f'S1_sustained|{cn}']['P_esr_kW'], ESR_mOhm=r[f'S1_sustained|{cn}']['ESR_mOhm'],I_Cdc_rms=r[f'S1_sustained|{cn}']['I_Cdc_rms_A'])
    sxc=r[f'S1_sustained|{cn}']['sx_over_C_max']
    E=out[cn]['Pesr_full_kW']/sxc**2*m2*8766/1e3; out[cn]['MWh_yr']=E; out[cn]['kUSD_yr']=E*80/1e3; print(cn,out[cn])
out['B10']['ESR_note']='filter capacitor ESR contained in R_f (Q=30)'
json.dump(out,open('losses_annual.json','w'),indent=1)
