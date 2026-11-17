"""Redraws fig9_rpc.pdf (Fig. 10 of the manuscript, label f10): co-phase traction supply with a
Scott transformer and a back-to-back power conditioner, (a) RPC and (b) hybrid RPC (series LC branch
in the alpha leg). Same content and topology as the previous version; Liberation Sans lettering.
Geometry in 'units' (y downwards); figure width 136 mm = 0.85 x 160 mm (as included in the manuscript); 1 unit = 136 mm / 704."""
import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/',1)[0])
from common import *
from matplotlib.patches import Rectangle, Circle
setup(8)
out = sys.argv[1] if len(sys.argv)>1 else 'fig9_rpc.pdf'
W, H = 704, 336
FW = 136*MM
fig = plt.figure(figsize=(FW, FW*H/W))
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
FS = 8; FSC = 9.5
TINT = '#DCEEFA'          # light tint of Okabe-Ito sky blue for the transformer and train boxes
LW, LWB, LWT, LWP = 1.0, 1.0, 2.0, 1.6    # wires, boxes, buses, capacitor plates (pt)

def line(xs, ys, lw=LW, **k):
    ax.plot(xs, ys, color='k', lw=lw, solid_capstyle='butt', solid_joinstyle='miter', **k)
def box(x0, y0, x1, y1, fc='white', lw=LWB, **k):
    ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc=fc, ec='k', lw=lw, joinstyle='miter', **k))
def dot(x, y, r=3.3):
    ax.add_patch(Circle((x, y), r, fc='k', ec='none'))
def txt(x, y, s, ha='left', va='center', fs=FS, **k):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, **k)

def panel(ox, hybrid, caption, rpc_label):
    X = lambda x: ox + x
    xl, xr = X(4), X(346)
    # three-phase 110 kV grid
    txt(X(4), 12, '110 kV three-phase grid')
    ys = [26.5, 33.5, 40.4]
    for y in ys: line([xl, xr], [y, y])
    # Scott transformer
    tx0, tx1, ty0, ty1 = X(40), X(160), 75.2, 123.9
    for xd, y in zip([X(60), X(100), X(140)], ys): line([xd, xd], [y, ty0])
    box(tx0, ty0, tx1, ty1, fc=TINT)
    txt((tx0+tx1)/2, (ty0+ty1)/2, 'Scott\ntransformer', ha='center', linespacing=1.15)
    # feeder alpha to the catenary
    cat_y, rail_y = 256.0, 297.8
    xa = X(55)
    line([xa, xa], [ty1, cat_y])
    txt(xa-9, 190, 'feeder α', ha='center', rotation=90)
    # catenary, rail, train
    line([xl, xr], [cat_y, cat_y], lw=LWT)
    line([xl, xr], [rail_y, rail_y], lw=LWT)
    dot(xa, cat_y)
    txt(X(63), 248.5, 'Catenary (feeder α), 25 kV')
    bx0, bx1, by0, by1 = X(110), X(162), 271.3, 289.4
    box(bx0, by0, bx1, by1, fc=TINT)
    txt((bx0+bx1)/2, (by0+by1)/2, 'Train', ha='center')
    xp = (bx0+bx1)/2
    line([xp, xp, xp+10], [by0, 264.4, cat_y])
    txt(X(4), 311, 'Rail')
    # RPC
    cx0, cx1 = X(252), X(300); xc = (cx0+cx1)/2
    bty0, bty1 = 130.8, 169.1       # beta leg
    aty0, aty1 = 186.5, 224.7       # alpha leg
    # dashed enclosure
    ax.add_patch(Rectangle((X(243), 82.2), X(344)-X(243), 273.4-82.2, fc='none', ec='k', lw=0.8,
                           ls=(0, (4.5, 2.2)), joinstyle='miter'))
    txt((X(243)+X(344))/2, 70.5, rpc_label, ha='center', fs=FS+0.5)
    # feeder beta
    line([tx1, xc, xc], [99.5, 99.5, bty0])
    txt(tx1+8, 90.0, 'feeder β')
    # converter boxes with diagonals and labels
    box(cx0, bty0, cx1, bty1); line([cx0, cx1], [bty1, bty0], lw=0.8)
    box(cx0, aty0, cx1, aty1); line([cx0, cx1], [aty1, aty0], lw=0.8)
    txt(cx0+4, bty0+8.5, 'AC'); txt(cx1-3, bty1-8.5, 'DC', ha='right')
    txt(cx0+4, aty0+8.5, 'DC'); txt(cx1-3, aty1-8.5, 'AC', ha='right')
    txt(cx1+7, (bty0+bty1)/2, 'β leg'); txt(cx1+7, (aty0+aty1)/2, 'α leg')
    # DC-link capacitor
    xl1, xr1 = xc-12, xc+12; ymid = (bty1+aty0)/2
    line([xl1, xl1], [bty1, aty0]); line([xr1, xr1], [bty1, aty0])
    line([xl1, xc-2.6], [ymid, ymid]); line([xc+2.6, xr1], [ymid, ymid])
    line([xc-2.6, xc-2.6], [ymid-5.6, ymid+5.6], lw=LWP); line([xc+2.6, xc+2.6], [ymid-5.6, ymid+5.6], lw=LWP)
    txt(cx1+7, ymid, r'$C_\mathrm{dc}$')
    # alpha-leg output to the catenary
    line([xc, xc], [bty0-31.3, bty0]) if False else None
    if not hybrid:
        line([xc, xc], [aty1, cat_y])
    else:
        line([xc, xc], [aty1, 231.0])
        line([xc-6.6, xc+6.6], [231.0, 231.0], lw=LWP); line([xc-6.6, xc+6.6], [235.2, 235.2], lw=LWP)
        line([xc, xc], [235.2, 236.6])
        r = (253.3-236.6)/6; t = np.linspace(0, np.pi, 25)
        px, py = [], []
        for i in range(3):
            px += list(xc + r*np.sin(t)); py += list(236.6 + 2*r*i + r*(1-np.cos(t)))
        line(px, py)
        line([xc, xc], [253.3, cat_y])
        txt(xc+11, 238.0, 'LC')
    dot(xc, cat_y)
    txt((xl+xr)/2, 321, caption, ha='center', fs=FSC)

panel(0,   False, '(a) RPC', 'RPC')
panel(354, True,  '(b) hybrid RPC', 'Hybrid RPC')
fig.savefig(out)
