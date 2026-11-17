import sys, numpy as np, emt, post, common as cm, json
P1,Q1=cm.const(30.0,1); P2,Q2=cm.const(25.0,1)
base=[dict(P=P1,Q=Q1,H_ms=8.0), dict(P=P1,Q=Q1,H_ms=8.0,Cf_mF=10.0), dict(P=P2,Q=Q2,dP_MW=-10,dQ_Mvar=-10*cm.TANPHI,t_ev=0.3,ramp=2e-3,H_ms=8.0,Cf_mF=10.0), dict(P=P2,Q=Q2,dP_MW=-10,dQ_Mvar=-10*cm.TANPHI,t_ev=0.3,ramp=2e-3,H_ms=8.0,ff=0)]
res={}
for dt,le in ((25e-6,8),(40e-6,5),(50e-6,4)):
    o=emt.simulate(base,T=1.4,dt=dt,log_every=le)
    rows=[]
    for i,c in enumerate(base):
        r,tr=post.analyse(o,i,c)
        rows.append([round(r['Vmin_V'],1),round(r['Vmax_V'],1),round(r['Vavg_min_V'],1),round(r['Vavg_max_V'],1),round(r['I_pu_max'][0],4),round(r['I_pu_max'][1],4),round(r['m_inst_max'],4)])
    res[dt]=rows; print(dt,rows,flush=True)
