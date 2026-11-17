import sys; sys.path.insert(0,'/home/claude/subtasks4/2'); sys.path.insert(0,'/home/claude/code')
import numpy as np
import compute_legs as cl
from rpc_sizing.network import solve
from rpc_sizing import rpc
k=15
d=np.load(cl.BASE%k); P=d['P'].astype(float);Q=d['Q'].astype(float)
S=P+1j*Q; mag=abs(S); sx,_=rpc.compensate(P,Q,cl.C,cl.EPS,cl.SSC); sxv=np.where(mag>0,sx*S/np.maximum(mag,1e-9),0)
nz=mag>0
# worst 200k samples subset + whole
Sa=(S-sxv)[nz]; Sb=sxv[nz]
r={}
for n in (10,12,20,60):
    ua,ub,Ia,Ib,v,res=cl.solve_full(Sa,Sb,n_iter=n)
    r[n]=(np.abs(ua),np.abs(ub),v,res.max())
    print(n,'res max',res.max(),'Ua min',np.abs(ua).min(),'vuf max',v.max())
for n in (10,12,20):
    print(n,'max|dUa| vs 60:',np.abs(r[n][0]-r[60][0]).max(),'max dVUF',np.abs(r[n][2]-r[60][2]).max(),' Imax rel',)
v_ref,_=solve(Sa,Sb,cl.SSC,n_iter=10,tol=1e-6)
print('vuf vs network.solve(10 it) max diff',np.abs(v_ref-r[10][2]).max())
v_ref12,_=solve(Sa,Sb,cl.SSC,n_iter=12,tol=1e-7)
print('vuf vs network.solve(12 it) max diff',np.abs(v_ref12-r[12][2]).max())
# current err at the highest-current samples
I12=np.abs(Sa)/r[12][0]/40; I60=np.abs(Sa)/r[60][0]/40
print('max rel err of alpha current pu @12 it vs 60:',np.max(np.abs(I12-I60)/I60),' max abs',np.abs(I12-I60).max())
