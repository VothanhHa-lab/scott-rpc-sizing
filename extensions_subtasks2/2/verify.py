"""Numerical check: vertices of the curves in the OLD vector PDFs (pdftocairo -svg, converted to data
coordinates through the old tick positions) are compared with the analytic formulas used for the NEW
figures. Also checks the NEW PDFs' own curve vertices against the same formulas (same mapping, via
its own ticks is not needed: new curves are generated from the formulas)."""
import sys, numpy as np
sys.path.insert(0,'/home/claude/subtasks2/2/work')
from parse import parse, tpts
def get(svg): return parse(svg)
# ---------- fig7 (indices as listed from the old file) ----------
P=get('/home/claude/subtasks2/2/work/fig7_iuf_vuf.svg')
x0,x1,y0,y100=59.2461,298.154,204.07,26.5
def a_map(X,Y): return (X-x0)/(x1-x0),(y0-Y)/(y0-y100)*100
def iuf(k,d):
    z=k*np.exp(1j*np.radians(d)); return 100*abs(1-z)/abs(1+z)
print('fig7(a) max |old vertex - Eq.(7)| in IUF percentage points')
for i,d in [(26,0),(36,10),(37,20),(47,30)]:
    X,Y=tpts(P[i]); k,y=a_map(X,Y)
    ok=[j for j in range(len(k)) if -0.001<=k[j]<=1.001]
    err=max(abs(y[j]-iuf(np.clip(k[j],0,1),d)) for j in ok); print('  dphi',d,'n',len(ok),'max err %.3f'%err)
bx0,bx1,by0,by6=357.84,596.75,204.07,22.95
print('fig7(b) max |old vertex - 100*dS/Ssc| in VUF percentage points')
for i,s in [(88,1000),(90,2000),(92,4000),(94,8000)]:
    X,Y=tpts(P[i]); x=(X-bx0)/(bx1-bx0)*60; y=(by0-Y)/(by0-by6)*6
    print('  Ssc',s,'max err %.4f'%np.max(abs(y-100*x/s)))
# markers vs analytic
k=np.arange(9)/8
sim0=np.array([100.00,77.42,59.50,44.94,32.87,22.71,14.03,6.54,0.00]); sim20=np.array([100.00,78.81,61.86,48.21,37.24,28.64,22.34,18.52,17.28])
d0=sim0-np.array([iuf(kk,0) for kk in k]); d20=sim20-np.array([iuf(kk,20) for kk in k])
print('IUF sim-analytic dphi=0 :',np.round(d0,2),'max |.|=%.2f'%abs(d0).max())
print('IUF sim-analytic dphi=20:',np.round(d20,2),'max |.|=%.2f'%abs(d20).max())
print('analytic at k=.5,0deg %.2f ; k=1,20deg %.2f ; (Table t5: 33.33 / 17.63)'%(iuf(.5,0),iuf(1,20)))
for s,v in [(1000,.826),(2000,.414),(4000,.207)]: print('VUF sim/analytic Ssc',s,'=%.4f'%(v/(100*8.42/s)))
# ---------- fig8 ----------
P=get('/home/claude/subtasks2/2/work/fig8_neutral.svg')
# panel a: x 100->61.58, 350->292.05 ; y: 1e3->144.96, 1e4->48.16
def amap(X,Y): return 100+(X-61.58)/(292.05-61.58)*250, 10**(3+(144.96-Y)/(144.96-48.16))
print('fig8(a) max relative error of old vertices vs L/(v/3.6)')
for i,L in [(33,30),(34,100),(35,200),(36,400)]:
    X,Y=tpts(P[i]); v,t=amap(X,Y); print('  L',L,'max rel err %.4f'%np.max(abs(t/(L/(v/3.6)*1000)-1)))
def bmap(X,Y): return (X-360.92)/(596.09-360.92)*2.5, 10**(1+(160.73-Y)/(160.73-109.86))
print('fig8(b) max relative error of old vertices vs 2Pt/(V0^2(1-b^2)), V0=3 kV, b=0.7, in mF')
for i,t in [(94,.1),(95,.3),(96,1.0),(97,3.0)]:
    X,Y=tpts(P[i]); Pm,C=bmap(X,Y); ref=2*Pm*1e6*t/(9e6*(1-.49))*1e3; print('  t',t,'max rel err %.4f'%np.max(abs(C/ref-1)))
print('C(1 MW, 30 m @ 350 km/h) = %.1f mF (text: 134 mF)'%(2*1e6*(30/(350/3.6))/(9e6*0.51)*1e3))
print('t_ns(30 m, 350 km/h) = %.1f ms (text: 0.31 s)'%(30/(350/3.6)*1e3))
print('t_ns(200 m, 350 km/h) = %.2f s (text: > 2 s)'%(200/(350/3.6)))
print('C(8 MW, 0.5 s, V0=3 kV) = %.2f F; with V0=2463 V: %.2f F (text 4.6 F, 153x 30 mF)'%(2*8e6*.5/(9e6*.51), 2*8e6*.5/(2463**2*.51)))
