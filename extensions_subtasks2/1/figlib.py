"""Shared helpers: redraw of the original (vector) geometry + Liberation Sans lettering."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

# Okabe-Ito
BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, BLACK = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#000000"

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "mathtext.fontset": "custom",
    "mathtext.rm": "Liberation Sans",
    "mathtext.it": "Liberation Sans:italic",
    "mathtext.bf": "Liberation Sans:bold",
    "mathtext.sf": "Liberation Sans",
    "mathtext.cal": "Liberation Sans:italic",
    "mathtext.tt": "Liberation Sans",
    "mathtext.default": "it",
    "pdf.fonttype": 42,      # embed TrueType (Liberation Sans), no Type 3
    "ps.fonttype": 42,
    "pdf.compression": 6,
})

HERE = os.path.dirname(os.path.abspath(__file__))
CODES = {"M": Path.MOVETO, "L": Path.LINETO, "C": Path.CURVE4, "Z": Path.CLOSEPOLY}

def _col(c, cmap):
    if c is None:
        return None
    key = tuple(c)
    if key in cmap:
        return cmap[key]
    return key

def new_fig(width_mm, canvas_w, canvas_h, x0=0.0, y0=0.0):
    """Axes in 'original point' units (y down).  Figure is width_mm wide."""
    w_in = width_mm / 25.4
    h_in = w_in * canvas_h / canvas_w
    fig = plt.figure(figsize=(w_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x0 + canvas_w)
    ax.set_ylim(y0 + canvas_h, y0)
    ax.axis("off")
    scale = w_in * 72.0 / canvas_w     # final pt per canvas unit
    return fig, ax, scale

def draw_geometry(ax, name, scale, cmap=None, only=None, dx=0.0, dy=0.0, lw_factor=1.0):
    """Draw items of the original vector geometry (index = order in the original drawing;
    item 0 is the white page background and is never drawn).  Optional translation (dx, dy)."""
    cmap = cmap or {}
    items = json.load(open(os.path.join(HERE, name + "_geometry.json")))
    for i, it in enumerate(items):
        if i == 0 or (only is not None and i not in only):
            continue
        verts, codes = [], []
        last = (0, 0)
        for cmd, pts in it["segs"]:
            if cmd == "Z":
                verts.append(last); codes.append(Path.CLOSEPOLY)
                continue
            for k in range(0, len(pts), 2):
                last = (pts[k] + dx, pts[k + 1] + dy)
                verts.append(last)
            codes += [CODES[cmd]] * (len(pts) // 2)
        # drop a trailing lone MOVETO (artefact of the original path dump)
        if codes and codes[-1] == Path.MOVETO and len(codes) > 1:
            codes.pop(); verts.pop()
        path = Path(verts, codes)
        fc = _col(it["fill"], cmap)
        ec = _col(it["stroke"], cmap)
        # line width: original pt * (canvas->final scale) * factor
        lw = it["lw"] * scale * lw_factor
        kw = dict(facecolor=fc if fc else "none", edgecolor=ec if ec else "none",
                  linewidth=lw if ec else 0, zorder=2)
        if it["dash"]:
            kw["linestyle"] = (0, [d / it["lw"] if it["lw"] else d for d in it["dash"]])
        kw["capstyle"] = {"butt": "butt", "round": "round", "square": "projecting"}.get(it["cap"], "butt")
        kw["joinstyle"] = it["join"] or "miter"
        ax.add_patch(PathPatch(path, **kw))

def text(ax, x, y, s, size, ha="left", va="baseline", weight="normal", color="black", z=5, **kw):
    return ax.text(x, y, s, fontsize=size, ha=ha, va=va, fontweight=weight, color=color,
                   zorder=z, fontfamily="Liberation Sans", **kw)

from matplotlib.patches import Ellipse, Rectangle, Circle
def line(ax, pts, lw, color="black", dash=None, cap="butt", join="miter", z=2):
    xs, ys = zip(*pts)
    ls = "-" if dash is None else (0, dash)
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle=cap, solid_joinstyle=join, linestyle=ls,
            zorder=z, dash_capstyle="butt")
def rect(ax, x0, y0, x1, y1, lw, fc="none", ec="black", dash=None, z=2):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=fc, edgecolor=ec, linewidth=lw,
                           linestyle="-" if dash is None else (0, dash), zorder=z, joinstyle="miter"))
def dot(ax, x, y, r, lw, color="black", z=4):
    ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor=color, linewidth=lw, zorder=z))
