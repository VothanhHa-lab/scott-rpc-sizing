"""Redraws fig9_rpc.pdf (Fig. 10 of the manuscript, label f10): co-phase traction supply with a Scott transformer
and a back-to-back power conditioner, (a) RPC and (b) hybrid RPC (series LC branch in the alpha leg).
Round-3 version: adds the single-phase coupling transformers (27.5/2.0 kV) between the feeder busbars and the
converter legs, the DC-link data (C_dc, V_dc = 3.5 kV) and the optional 100 Hz (2f) resonant filter.
Liberation Sans lettering; figure width 136 mm (0.85 x 160 mm as included in the manuscript).
Usage: python3 fig9_rpc.py [out.pdf]"""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from matplotlib.patches import Rectangle, Circle
setup(8)
out = sys.argv[1] if len(sys.argv) > 1 else 'fig9_rpc.pdf'
W, H = 824, 476
FW = 136*MM
fig = plt.figure(figsize=(FW, FW*H/W))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
FS = 8; FSC = 9.5
TINT = '#DCEEFA'          # light tint of Okabe-Ito sky blue for transformers and train boxes
LW, LWB, LWT, LWP = 1.0, 1.0, 2.0, 1.6    # wires, boxes, buses, capacitor plates (pt)
DASH = (0, (3.0, 2.0))

def line(xs, ys, lw=LW, ls='-', **k):
    ax.plot(xs, ys, color='k', lw=lw, ls=ls, solid_capstyle='butt', solid_joinstyle='miter',
            dash_capstyle='butt', **k)
def box(x0, y0, x1, y1, fc='white', lw=LWB, **k):
    ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc=fc, ec='k', lw=lw, joinstyle='miter', **k))
def dot(x, y, r=3.3):
    ax.add_patch(Circle((x, y), r, fc='k', ec='none'))
def txt(x, y, s, ha='left', va='center', fs=FS, **k):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, **k)
def xfmr(x, yc, r=8.0, sep=9.6):
    """single-phase two-winding transformer symbol on a vertical wire; returns (y_top, y_bottom)."""
    y1, y2 = yc-sep/2, yc+sep/2
    for y in (y1, y2):
        ax.add_patch(Circle((x, y), r, fc='none', ec='k', lw=LWB))
    return y1-r, y2+r
def coil_h(x0, x1, y, n=3, ls='-'):
    """horizontal inductor (n bumps upwards) between x0 and x1."""
    r = (x1-x0)/(2*n); t = np.linspace(0, np.pi, 25); px, py = [], []
    for i in range(n):
        px += list(x0 + 2*r*i + r*(1-np.cos(t))); py += list(y - r*np.sin(t))
    line(px, py, ls=ls)
def coil_v(x, y0, y1, n=3):
    r = (y1-y0)/(2*n); t = np.linspace(0, np.pi, 25); px, py = [], []
    for i in range(n):
        px += list(x + r*np.sin(t)); py += list(y0 + 2*r*i + r*(1-np.cos(t)))
    line(px, py)

def panel(ox, hybrid, caption, rpc_label):
    X = lambda x: ox + x
    xl, xr = X(4), X(408)
    # three-phase 110 kV grid
    txt(X(4), 12, '110 kV three-phase grid')
    ys = [26.5, 33.5, 40.4]
    for y in ys: line([xl, xr], [y, y])
    # Scott transformer
    tx0, tx1, ty0, ty1 = X(16), X(128), 75.2, 123.9
    for xd, y in zip([X(38), X(70), X(102)], ys): line([xd, xd], [y, ty0])
    box(tx0, ty0, tx1, ty1, fc=TINT)
    txt((tx0+tx1)/2, (ty0+ty1)/2, 'Scott\ntransformer', ha='center', linespacing=1.15)
    # geometry of the converter column
    xc = X(266)
    bty0 = 152.0; bty1 = bty0+38.3            # beta leg
    aty0 = bty1+72.0; aty1 = aty0+38.3        # alpha leg
    t2_top, t2_bot = aty1+12.6, aty1+12.6+25.6    # alpha-side coupling transformer extent (r=8, sep=9.6)
    lc_y0 = t2_bot+10.0                       # LC branch (hybrid) between transformer and catenary
    cat_y = lc_y0+45.0                        # same height in both panels
    rail_y = cat_y+41.8
    # feeder alpha to the catenary
    xa = X(38)
    line([xa, xa], [ty1, cat_y])
    txt(xa-9, (ty1+cat_y)/2, 'feeder α', ha='center', rotation=90)
    # catenary, rail, train
    line([xl, xr], [cat_y, cat_y], lw=LWT)
    line([xl, xr], [rail_y, rail_y], lw=LWT)
    dot(xa, cat_y)
    txt(X(46), cat_y-27, 'Catenary (feeder α),\n25 kV', linespacing=1.15)
    bx0, bx1, by0, by1 = X(90), X(142), cat_y+15.3, cat_y+33.4
    box(bx0, by0, bx1, by1, fc=TINT)
    txt((bx0+bx1)/2, (by0+by1)/2, 'Train', ha='center')
    xp = (bx0+bx1)/2
    line([xp, xp, xp+10], [by0, cat_y+8.4, cat_y])
    txt(X(4), rail_y+13, 'Rail')
    # RPC enclosure
    cx0, cx1 = xc-34, xc+34
    ax.add_patch(Rectangle((X(208), 82.2), X(408)-X(208), cat_y+17.4-82.2, fc='none', ec='k', lw=0.8,
                           ls=(0, (4.5, 2.2)), joinstyle='miter'))
    txt((X(208)+X(408))/2, 70.5, rpc_label, ha='center', fs=FS+0.5)
    # feeder beta -> coupling transformer T_beta -> beta leg
    t1_top = 116.0; yc1 = t1_top+8+4.8
    line([tx1, xc, xc], [99.5, 99.5, t1_top])
    txt(tx1+6, 90.0, 'feeder β')
    a, b = xfmr(xc, yc1); line([xc, xc], [b, bty0])
    txt(xc+15, yc1, '27.5/2.0 kV')
    # converter boxes with diagonals and labels
    box(cx0, bty0, cx1, bty1); line([cx0, cx1], [bty1, bty0], lw=0.8)
    box(cx0, aty0, cx1, aty1); line([cx0, cx1], [aty1, aty0], lw=0.8)
    txt(cx0+4, bty0+8.5, 'AC'); txt(cx1-3, bty1-8.5, 'DC', ha='right')
    txt(cx0+4, aty0+8.5, 'DC'); txt(cx1-3, aty1-8.5, 'AC', ha='right')
    txt(cx1+6, (bty0+bty1)/2, 'β leg'); txt(cx1+6, (aty0+aty1)/2, 'α leg')
    # DC link: rails, C_dc, optional 2f filter
    xl1, xr1 = xc-30, xc+30
    line([xl1, xl1], [bty1, aty0]); line([xr1, xr1], [bty1, aty0])
    yc_ = bty1+15.0; yf = bty1+55.0
    xm = xc
    line([xl1, xm-2.6], [yc_, yc_]); line([xm+2.6, xr1], [yc_, yc_])
    line([xm-2.6, xm-2.6], [yc_-5.6, yc_+5.6], lw=LWP); line([xm+2.6, xm+2.6], [yc_-5.6, yc_+5.6], lw=LWP)
    txt(cx1+6, yc_-8, r'$C_\mathrm{dc}$'); txt(cx1+6, yc_+8, r'$V_\mathrm{dc}$ = 3.5 kV')
    # optional filter: series L-C tuned to 100 Hz, dashed
    xs0, xs1 = xl1+5, xr1-4
    line([xl1, xs0], [yf, yf], ls=DASH)
    coil_h(xs0, xs0+24, yf, 3)
    line([xs0+24, xr1-9.0], [yf, yf], ls=DASH)
    line([xr1-9.0, xr1-9.0], [yf-5.6, yf+5.6], lw=LWP); line([xr1-4.0, xr1-4.0], [yf-5.6, yf+5.6], lw=LWP)
    line([xr1-4.0, xr1], [yf, yf], ls=DASH)
    txt(cx1+6, yf-8, 'optional'); txt(cx1+6, yf+8, '2f filter')
    dot(xl1, yf, 2.6); dot(xr1, yf, 2.6); dot(xl1, yc_, 2.6); dot(xr1, yc_, 2.6)
    # alpha leg -> coupling transformer T_alpha -> (LC) -> catenary
    line([xc, xc], [aty1, t2_top])
    a2, b2 = xfmr(xc, (t2_top+t2_bot)/2)
    txt(xc+15, (t2_top+t2_bot)/2, '27.5/2.0 kV')
    if not hybrid:
        line([xc, xc], [t2_bot, cat_y])
    else:
        y_c0 = lc_y0 + 0.0
        line([xc, xc], [t2_bot, y_c0])
        line([xc-6.6, xc+6.6], [y_c0, y_c0], lw=LWP); line([xc-6.6, xc+6.6], [y_c0+4.2, y_c0+4.2], lw=LWP)
        line([xc, xc], [y_c0+4.2, y_c0+6.6])
        coil_v(xc, y_c0+6.6, y_c0+6.6+25.0, 3)
        line([xc, xc], [y_c0+6.6+25.0, cat_y])
        txt(xc+11, y_c0+15.0, 'LC')
    dot(xc, cat_y)
    txt((xl+xr)/2, rail_y+25, caption, ha='center', fs=FSC)
    return cat_y, rail_y

panel(0,   False, '(a) RPC', 'RPC')
panel(414, True,  '(b) hybrid RPC', 'Hybrid RPC')
fig.savefig(out)
