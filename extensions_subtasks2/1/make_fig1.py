import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import *

# canvas = original (670.7 x 298.4 pt) widened on the right for the wider Arial-metric lettering
CW, CH = 690.0, 298.4
fig, ax, sc = new_fig(174.0, CW, CH)
cmap = {(0.7529, 0.2235, 0.1686): VERM}     # red dashed substation boxes -> Okabe-Ito vermilion
draw_geometry(ax, "fig1_structure", sc, cmap)

FS = 9.0   # pt at final size (174 mm)
# three-phase bus labels and nominal data
text(ax, 69.8, 16.2, "110 kV/220 kV, 50 Hz", FS)
text(ax, 47.1, 27.5, "A", FS); text(ax, 47.4, 51.5, "B", FS); text(ax, 47.4, 75.7, "C", FS)
# substations
text(ax, 192.2, 132.8, "Traction substation 1", FS)
text(ax, 526.3, 132.8, "Traction substation 2", FS)
# feeder terminals
text(ax, 70.4, 180.2, r"$\alpha_{\mathrm{1}}$", FS + 0.5)
text(ax, 213.9, 180.2, r"$\beta_{\mathrm{1}}$", FS + 0.5)
text(ax, 404.5, 180.2, r"$\alpha_{\mathrm{2}}$", FS + 0.5)
text(ax, 548.1, 180.2, r"$\beta_{\mathrm{2}}$", FS + 0.5)
# catenary voltage
text(ax, 15.6, 222.2, "25 kV", FS); text(ax, 15.6, 233.8, "50 Hz", FS)
# neutral sections
text(ax, 158.6, 221.7, "NS1", FS); text(ax, 339.9, 221.7, "NS2", FS); text(ax, 492.1, 221.7, "NS3", FS)
# conductors
text(ax, 631.0, 247.7, "Catenary", FS); text(ax, 631.0, 284.0, "Rail", FS)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "fig1_structure.pdf"
    fig.savefig(out, transparent=False, facecolor="white")
    fig.savefig(out.replace(".pdf", ".png"), dpi=200)
