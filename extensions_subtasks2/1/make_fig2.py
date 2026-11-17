"""Fig. 2 (label f2): structure of the simulation model.  Redrawn with Liberation Sans lettering.
Geometry of the small symbols (trains, diodes, inductor, ...) is taken from the original drawing
(fig2_model_geometry.json, item numbers = order in the original); boxes, wires and the
layout are re-drawn so that the wider Arial-metric lettering fits."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import *

CW, CH = 730.0, 504.0
fig, ax, sc = new_fig(174.0, CW, CH)
W = lambda w: w * sc                    # original line width (pt) -> final pt
SKYFILL, TRAINFILL, VAFILL = "#FFFFFF", "#FFFFFF", "#FFFFFF"
cmap = {(0.8627, 0.9137, 0.9686): SKYFILL, (0.9176, 0.9451, 0.9843): TRAINFILL,
        (1.0, 0.9568, 0.8392): VAFILL, (0.4784, 0.3608, 0.0): ORANGE}
G = lambda idx, dx=0.0, dy=0.0: draw_geometry(ax, "fig2_model", sc, cmap, only=set(idx), dx=dx, dy=dy)

B, BT = 8.3, 9.0                       # body / bold-title font size [pt, final]
XC = 365.0

# ------------------------------------------------------------------ public grid
ax.add_patch(Ellipse((XC, 40), 360, 68, facecolor="white", edgecolor="black", linewidth=W(1.298), zorder=3))
text(ax, XC, 33.5, "Public power grid, 110 kV, 50 Hz", BT, ha="center", weight="bold")
text(ax, XC, 55.5, r"$S_{\mathrm{sc}}$ = 1500 MVA (varied 500–4000 MVA), $X/R$ = 10", B, ha="center")

PH = (XC - 32.1, XC, XC + 32.2)                 # phase conductors A, B, C
Y_PCC, BOX_T, BOX_B = 133.0, 164.0, 222.0
for x, lab in zip(PH, "ABC"):
    line(ax, [(x, 74), (x, BOX_T)], W(1.198))
    rect(ax, x - 4.8, 96.2, x + 4.8, 114.4, W(1.099), fc="white", z=3)        # source impedance
    text(ax, x - 8.0, 84.5, lab, B, ha="center")
    dot(ax, x, Y_PCC, 2.2, W(1.0))
text(ax, PH[2] + 11.0, 107.5, r"$Z_{s}$ (source impedance)", B)
# PCC and measuring instrument
VA_X = PH[2] + 50.0
text(ax, PH[0] - 24.5, Y_PCC + 3.4, "PCC", B, ha="right", weight="bold")
line(ax, [(PH[0] - 21.5, Y_PCC), (VA_X - 12.0, Y_PCC)], W(0.899), color=ORANGE, dash=[3.995, 2.0])
ax.add_patch(Circle((VA_X, Y_PCC), 12.0, facecolor=VAFILL, edgecolor="black", linewidth=W(1.099), zorder=3))
text(ax, VA_X, Y_PCC + 3.0, "VA", 8.0, ha="center")
text(ax, VA_X + 16.0, Y_PCC - 7.0, r"measured $i_{abc}$, $u_{abc}$", B)
text(ax, VA_X + 16.0, Y_PCC + 6.8, "(IUF, VUF, THD)", B)

# ------------------------------------------------------------------ Scott transformer
rect(ax, XC - 160, BOX_T, XC + 160, BOX_B, W(1.298), fc=SKYFILL, z=3)
text(ax, XC, BOX_T + 21.8, "Scott traction transformer, 40 MVA, 110/25 kV", BT, ha="center", weight="bold")
text(ax, XC, BOX_T + 43.0, r"(three-phase to two-phase:  $i_{abc} = T\;[i_{\alpha},\ i_{\beta}]^{\mathrm{T}}$)", B, ha="center")

# ------------------------------------------------------------------ feeders, catenary, neutral section, rail
Y_CAT, XF1, XF2 = 286.3, XC - 118.0, XC + 118.0
for xf in (XF1, XF2):
    line(ax, [(xf, BOX_B), (xf, Y_CAT)], W(1.198))
    dot(ax, xf, Y_CAT, 2.4, W(1.0))
text(ax, XF1 - 4.5, BOX_B + 15.3, r"$\alpha$", B + 2.0, ha="right")
text(ax, XF2 + 5.0, BOX_B + 15.3, r"$\beta$", B + 2.0, ha="left")
text(ax, XF1 + 5.6, 256.0, r"feeder $\alpha$", B)
text(ax, XF2 - 5.6, 256.0, r"feeder $\beta$", B, ha="right")
NSL, NSR = XC - 26.75, XC + 26.75
line(ax, [(23.3, Y_CAT), (NSL, Y_CAT)], W(1.798))
line(ax, [(NSR, Y_CAT), (700.0, Y_CAT)], W(1.798))
line(ax, [(NSL, Y_CAT), (NSR, Y_CAT)], W(0.999), dash=[2.996, 1.997])
for x in (NSL, NSR):
    rect(ax, x - 2.65, Y_CAT - 4.85, x + 2.65, Y_CAT + 4.85, W(0.999), fc="white", z=3)
text(ax, XC, Y_CAT - 7.0, "neutral section", B, ha="center")
text(ax, XC, Y_CAT + 21.2, "breaker open", B, ha="center")
text(ax, XC, Y_CAT + 34.6, r"$t$ = 2.5–3.0 s", B, ha="center")
text(ax, 34.0, Y_CAT - 6.5, r"25 kV catenary, section $\alpha$", B)
text(ax, 694.0, Y_CAT - 6.5, r"25 kV catenary, section $\beta$", B, ha="right")
Y_RAIL = 345.2
line(ax, [(23.3, Y_RAIL), (700.0, Y_RAIL)], W(2.397))
text(ax, 704.0, Y_RAIL + 2.9, "rail", B)

# trains (original symbols, translated)
TDX, TDX2, TDY = 48.0, 78.0, 21.8       # x shifts of train 1 / train 2, common y shift
G([61] + list(range(68, 79)) + [32, 33], TDX, TDY)
G([62] + list(range(79, 90)) + [34, 35], TDX2, TDY)
text(ax, 198.0, 312.6, r"train, $t$ = 0–2.5 s", B, ha="right")
text(ax, 592.0, 312.6, r"same train, $t$ = 3–5 s", B, ha="right")
# speed arrow (original arrow head, longer shaft)
line(ax, [(202.1 + TDX, 312.7 + TDY), (315.0, 312.7 + TDY)], W(1.099))
G([6], TDX + (315.0 - (250.4 + TDX)), TDY)
text(ax, 204.1 + TDX + 1.0, 308.4 + TDY, r"$v$ = 300 km/h", B)

# ------------------------------------------------------------------ on-board power circuit
BX0, BX1, BY0, BY1 = 28.6, 712.0, 376.0, 496.0
rect(ax, BX0, BY0, BX1, BY1, W(0.999), dash=[4.994, 2.996])
line(ax, [(BX0, BY0), (60.8 + TDX, 328.2 + TDY)], W(0.599), color="#666666", dash=[2.0, 2.0])
line(ax, [(189.3 + TDX, 328.2 + TDY), (BX1, BY0)], W(0.599), color="#666666", dash=[2.0, 2.0])
text(ax, 39.4, BY0 + 14.0, "On-board power circuit of the train (model of section 3.1)", BT, weight="bold")

DYC, DXA, DXB = 40.0, 25.0, 45.0
YU, YL, YM = 398.4 + DYC, 419.8 + DYC, 409.1 + DYC     # upper / lower DC rail, motor wire
G([8, 9, 10, 11, 12, 13, 14] + list(range(38, 50)) + [95, 96, 97], DXA, DYC)       # pantograph ... diode bridge
G([15, 16, 17, 18, 19, 20, 53, 54, 55, 56, 57, 98, 99], DXB, DYC)                  # inductor, DC link, inverter, motor
line(ax, [(242.9 + DXA, YU), (256.3 + DXB, YU)], W(1.198))
line(ax, [(290.6 + DXB, YU), (339.3 + DXB, YU)], W(1.198))
line(ax, [(242.9 + DXA, YL), (339.3 + DXB, YL)], W(1.198))
line(ax, [(382.2 + DXB, YM), (403.6 + DXB, YM)], W(1.198))

text(ax, 50.1 + DXA, 424.0 + DYC, "pantograph", B, ha="center")
text(ax, 93.0 + DXA, 421.8, "main circuit", B, ha="center")
text(ax, 93.0 + DXA, 435.0, "breaker", B, ha="center")
text(ax, 152.1 + DXA, 468.3, "on-board", B, ha="center")
text(ax, 152.1 + DXA, 481.5, "transformer", B, ha="center")
text(ax, 213.7 + DXA, 412.4, "diode bridge + commutation", B, ha="center")
text(ax, 213.7 + DXA, 425.6, "(or 4QC with PWM)", B, ha="center")
text(ax, 256.3 + DXB, 390.2 + DYC, r"$L_{d}$ (diode train)", B)
text(ax, 307.2 + DXB + 11.0, 413.6 + DYC, r"$C_{\mathrm{dc}}$", B)
text(ax, 307.2 + DXB, 431.6 + DYC, "DC link", B, ha="center")
text(ax, 348.4 + DXB, 399.4 + DYC, "=", B, ha="center", va="center")
text(ax, 374.1 + DXB, 417.5 + DYC, "~", B + 3.0, ha="center", va="center")
text(ax, 417.0 + DXB, 409.4 + DYC, "M", B + 2.0, ha="center", va="center")
text(ax, 452.0, 475.2, "inverter + motor: constant-", B, ha="center")
text(ax, 452.0, 488.4, r"power load $P$ (3 / 8 MW)", B, ha="center")
NX = 505.0
for k, s in enumerate(["Breaker opens at current zero",
                       r"Under-voltage trip at 0.7 $U_{\mathrm{dc0}}$",
                       r"Pre-charge resistor $R_{\mathrm{pc}}$ on reclosing",
                       "Catenary impedance neglected",
                       "Time step 10 µs (explicit Euler)"]):
    text(ax, NX, 405.8 + 13.4 * k, s, B)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "fig2_model.pdf"
    fig.savefig(out, transparent=False, facecolor="white")
    fig.savefig(out.replace(".pdf", ".png"), dpi=200)
