import numpy as np, json
from rpc_sizing import dynamics as dy, rpc
d=np.load('results/base_w000.npz'); P=d['P'].astype(float); Q=d['Q'].astype(float)
S=np.hypot(P,Q)
from analyse import load, methods
_m=methods(load('base'),750)['proposed']
C,eps,Ssc=_m['C'],_m['eps'],750.0
print('design',C,eps)
req=np.maximum(0,S-eps/100*Ssc)/2
# segment with the largest 1 s change of the requested transfer
i=int(np.argmax(np.abs(np.diff(req)))); a=max(i-30,0)
seg=slice(a,a+61)
res={}
for ff in [True, False]:
    o=dy.simulate(P[seg],Q[seg],C,eps,Ssc,t_step=40.0,step_MW=-10.0,ff=ff)
    res[str(ff)]=o
    print(ff,'Cdc %.1f mF'%o['Cdc_mF'],'Vdc %.0f..%.0f'%(o['Vdc'].min(),o['Vdc'].max()),'Ia %.3f Ib %.3f'%(o['Ia'].max(),o['Ib'].max()))
np.savez_compressed('results/dyn.npz', a=a, **{f'{k}_{ff}':v[::10] for ff,o in res.items() for k,v in o.items() if isinstance(v,np.ndarray)})
print('segment start', a, 'max dreq', np.abs(np.diff(req)).max())
# H sweep without ff to find min H keeping +/-10 %
for H in [8, 15, 20, 30, 40]:
    o=dy.simulate(P[seg],Q[seg],C,eps,Ssc,t_step=40.0,step_MW=-10.0,ff=False,H_ms=H, dt=4e-4)
    print('H',H,'Vdc %.0f..%.0f'%(o['Vdc'].min(),o['Vdc'].max()))
