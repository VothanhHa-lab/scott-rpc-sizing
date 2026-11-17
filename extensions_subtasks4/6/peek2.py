import sys; sys.path.insert(0,'/home/claude/subtasks4/6/scripts')
from lib6 import *
from scipy.interpolate import PchipInterpolator
S = exact_set()
hw = Hw("none", trafo=False)
def curve(eps):
    cs = sorted([c for c in S if abs(c.eps-eps)<1e-9 and ok(c)], key=lambda c: c.C)
    C = np.array([c.C for c in cs]); lE = np.log(np.maximum([c.Ev*W for c in cs],1e-3)); CL=np.array([hw.CL(c) for c in cs])
    return C, lE, CL
for cap in (44.86, 30.64):
    print("cap", cap)
    for eps in (0,0.25,0.5,0.75,1.0,1.25,1.5,1.75,1.9):
        C,lE,CL = curve(eps)
        if len(C)<3: continue
        # find C where Eviol = cap by linear interpolation of log E in C
        f = PchipInterpolator(C, lE); g = PchipInterpolator(C, CL)
        xs = np.linspace(C.min(), C.max(), 5000); e = f(xs)
        idx = np.where(e <= np.log(cap))[0]
        if len(idx)==0: print(eps,"none"); continue
        x = xs[idx[0]]; print(f" eps={eps:4.2f} Cmin={x:6.2f} caploss={float(g(x)):6.1f}")
