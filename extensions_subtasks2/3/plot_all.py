"""Re-plot Figs A1-A4 (fig3_primary_currents, fig4_spectra, fig5_train, fig6_dclink) with Liberation Sans lettering.
All plotted numbers come from ../data/*.json, which extract_all.py recovered from the original PDFs
(vector paths mapped to data coordinates through the axis tick positions; the 300-dpi raster layers
holding the dense waveforms are re-embedded unchanged, pixel for pixel, at their original data-space extent).
Usage: python plot_all.py [outdir]"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, '..', 'data')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'new')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Liberation Sans'],
    'font.size': 9, 'axes.labelsize': 9, 'axes.titlesize': 9, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
    'legend.fontsize': 7,
    'pdf.fonttype': 42, 'ps.fonttype': 42,
    'mathtext.fontset': 'custom', 'mathtext.rm': 'Liberation Sans', 'mathtext.it': 'Liberation Sans:italic',
    'mathtext.bf': 'Liberation Sans:bold', 'mathtext.cal': 'Liberation Sans:italic', 'mathtext.sf': 'Liberation Sans', 'mathtext.tt': 'Liberation Sans', 'mathtext.default': 'it',
    'path.simplify': False,           # keep every extracted vertex
    'savefig.dpi': 300,
})
from matplotlib import font_manager as fm
assert 'LiberationSans' in fm.findfont('Liberation Sans'), fm.findfont('Liberation Sans')

SNAP = False
def R(v):
    # Limits as recovered (1e-7 pt fit noise).  Only the log-axis bar figure (Fig. 4) is snapped to 1e-5 so that the
    # top limit is exactly 30 (a minor tick sits there); raster-layer figures keep the recovered values so that the
    # embedded bitmaps land on exactly the same sub-pixel position as in the original.
    return [round(float(t), 5) for t in v] if SNAP else [float(t) for t in v]

def load(name): return json.load(open(os.path.join(DATA, name + '.json')))

def make_axes(fig, W, H, a, **kw):
    x0, y0, x1, y1 = a['box_pt']
    ax = fig.add_axes([x0/W, y0/H, (x1-x0)/W, (y1-y0)/H], **kw)
    if a['ylog']: ax.set_yscale('log')
    ax.set_xlim(R(a['xlim'])); ax.set_ylim(R(a['ylim']))
    ax.set_xticks(a['xticks']); ax.set_yticks(a['yticks'])
    ax.grid(True, alpha=0.35)
    return ax

def add_images(ax, a):
    for im in a['images']:
        arr = np.asarray(Image.open(os.path.join(DATA, im['file'])).convert('RGBA'))
        x0, x1, yb, yt = im['extent']
        ax.imshow(arr, extent=[x0, x1, yb, yt], origin='upper', aspect='auto', interpolation='none', zorder=2)
    ax.set_xlim(R(a['xlim'])); ax.set_ylim(R(a['ylim']))

def dash_to_ls(l):
    d, off = l['dash']
    if not d: return '-'
    return (0, tuple(v / l['lw'] for v in d))   # matplotlib rescales by linewidth

def add_lines(ax, a):
    for l in a['lines']:
        ax.plot(l['x'], l['y'], color=l['color'], lw=l['lw'], ls=dash_to_ls(l), zorder=2)

C_BLUE, C_GREEN, C_RED = '#1f77b4', '#2ca02c', '#d62728'   # exactly the colours of the original
LS_DASH = '--'; LS_DOT = ':'; LS_DASHDOT = '-.'

# ----------------------------------------------------------------------------- Fig 3
def fig3():
    d = load('fig3_primary_currents'); W, H = d['page']
    fig = plt.figure(figsize=(W/72, H/72))
    a0, a1 = d['axes']
    ax = make_axes(fig, W, H, a0); add_images(ax, a0)
    ax.set_title('(a)'); ax.set_xlabel('Time (s)'); ax.set_ylabel('Current (A)')
    ax.legend(handles=[Line2D([], [], color=C_BLUE, lw=1.0, ls='-', label='Phase A'),
                       Line2D([], [], color=C_GREEN, lw=1.0, ls=LS_DASH, label='Phase B'),
                       Line2D([], [], color=C_RED, lw=1.0, ls=LS_DOT, label='Phase C')], loc='upper right')
    ax = make_axes(fig, W, H, a1)
    # vector curves, drawn in the original order A, B, C
    for l, lab in zip(a1['lines'], ['Phase A', 'Phase B', 'Phase C']):
        ax.plot(l['x'], l['y'], color=l['color'], lw=l['lw'], ls=dash_to_ls(l), label=lab, zorder=2)
    ax.set_title('(b)'); ax.set_xlabel('Time (s)'); ax.set_ylabel('Current (A)')
    ax.legend(loc='upper right')
    ax.set_xlim(R(a1['xlim'])); ax.set_ylim(R(a1['ylim']))
    fig.savefig(os.path.join(OUT, 'fig3_primary_currents.pdf'), format='pdf'); plt.close(fig)

# ----------------------------------------------------------------------------- Fig 4
def fig4():
    global SNAP; SNAP = True
    d = load('fig4_spectra'); W, H = d['page']
    fig = plt.figure(figsize=(W/72, H/72))
    titles = ['(a) diode, low load – THD = 22.5%', '(b) diode, high load – THD = 20.9%', '(c) 4QC, high load – THD = 6.7%']
    for k, (a, t) in enumerate(zip(d['axes'], titles)):
        ax = make_axes(fig, W, H, a)
        xc = np.array([(b['x0'] + b['x1'])/2 for b in a['bars']])
        harm = np.rint(xc).astype(int); assert np.allclose(xc, harm, atol=1e-5)
        wid = np.array([b['x1'] - b['x0'] for b in a['bars']]); assert np.allclose(wid, 0.7, atol=1e-5)
        top = np.array([b['top'] for b in a['bars']])
        ax.bar(harm, top, width=0.7, color=a['bars'][0]['color'])
        ax.set_title(t, fontsize=8.5); ax.set_xlabel('Harmonic order')
        if k == 0: ax.set_ylabel('Magnitude (% of fundamental), phase B')
        else: ax.tick_params(labelleft=False)
        ax.set_xlim(R(a['xlim'])); ax.set_ylim(R(a['ylim']))
    fig.savefig(os.path.join(OUT, 'fig4_spectra.pdf'), format='pdf'); plt.close(fig); SNAP = False

# ----------------------------------------------------------------------------- Fig 5
def fig5():
    d = load('fig5_train'); W, H = d['page']
    fig = plt.figure(figsize=(W/72, H/72))
    for a, t, yl in zip(d['axes'], ['(a) pantograph voltage', '(b) train input current'], ['Voltage (kV)', 'Current (A)']):
        ax = make_axes(fig, W, H, a); add_images(ax, a)
        for l in a['lines']:        # breaker-open / reclose markers at 2.5 s and 3.0 s (annotation lines)
            ax.axvline(round(l['x'][0], 4), color='k', lw=l['lw'], ls=':', zorder=2)
        ax.set_title(t); ax.set_xlabel('Time (s)'); ax.set_ylabel(yl)
        ax.set_xlim(R(a['xlim'])); ax.set_ylim(R(a['ylim']))
    fig.savefig(os.path.join(OUT, 'fig5_train.pdf'), format='pdf'); plt.close(fig)

# ----------------------------------------------------------------------------- Fig 6
def fig6():
    d = load('fig6_dclink'); W, H = d['page']
    fig = plt.figure(figsize=(W/72, H/72))
    a0, a1 = d['axes']
    ax = make_axes(fig, W, H, a0); add_images(ax, a0)
    ax.set_title('(a) whole run (scenario A)'); ax.set_xlabel('Time (s)'); ax.set_ylabel(r'U$_{dc}$ (pu)')
    ax.legend(handles=[Line2D([], [], color=C_GREEN, lw=1.4, ls='-', label='Diode, no pre-charge'),
                       Line2D([], [], color=C_BLUE, lw=1.4, ls=LS_DASHDOT, label='4QC, with pre-charge')], loc='lower right')
    ax = make_axes(fig, W, H, a1); add_images(ax, a1)
    thr = a1['lines'][0]; assert abs(thr['y'][0] - 0.7) < 1e-6
    ax.axhline(0.7, color='k', lw=thr['lw'], ls=':', zorder=2)
    ax.text(THR_X, 0.7 + THR_DY, 'protection threshold', fontsize=7, ha='left', va='baseline')
    ax.set_title('(b) zoom around the neutral section'); ax.set_xlabel('Time (s)'); ax.set_ylabel(r'U$_{dc}$ (pu)')
    ax.legend(handles=[Line2D([], [], color=C_GREEN, lw=2.0, ls='-', label='Diode, no pre-charge'),
                       Line2D([], [], color=C_GREEN, lw=2.0, ls=(0, (6, 2)), label='Diode, with pre-charge'),
                       Line2D([], [], color=C_BLUE, lw=2.0, ls=LS_DASHDOT, label='4QC, no pre-charge'),
                       Line2D([], [], color=C_BLUE, lw=2.0, ls=LS_DOT, label='4QC, with pre-charge')], loc='lower right', ncol=2)
    ax.set_xlim(R(a1['xlim'])); ax.set_ylim(R(a1['ylim']))
    fig.savefig(os.path.join(OUT, 'fig6_dclink.pdf'), format='pdf'); plt.close(fig)

# ----------------------------------------------------------------------------- optional: Fig 4 laid out for 1.0\textwidth
def fig4_final():
    """Same bars/limits/ticks/strings as fig4(), but drawn at the final printed width (455.24 pt = \\textwidth of OR2) with
    8 pt lettering, so that \\includegraphics[width=\\textwidth] gives 8 pt text (Springer minimum).  Only the page
    geometry differs (taller, 3.0 in); no number or label is changed."""
    global SNAP; SNAP = True
    d = load('fig4_spectra')
    Wf, Hf = 455.244, 216.0
    plt.rcParams.update({'font.size': 8, 'axes.labelsize': 8, 'axes.titlesize': 8, 'xtick.labelsize': 8, 'ytick.labelsize': 8})
    fig = plt.figure(figsize=(Wf/72, Hf/72))
    titles = ['(a) diode, low load \u2013 THD = 22.5%', '(b) diode, high load \u2013 THD = 20.9%', '(c) 4QC, high load \u2013 THD = 6.7%']
    left, gap, pw = 44.0, 9.0, (Wf - 44.0 - 6.0 - 2*9.0)/3
    for k, (a, t) in enumerate(zip(d['axes'], titles)):
        x0 = left + k*(pw + gap)
        ax = fig.add_axes([x0/Wf, 36.0/Hf, pw/Wf, (Hf-36.0-22.0)/Hf]); ax.set_yscale('log')
        ax.set_xticks(a['xticks']); ax.set_yticks(a['yticks']); ax.grid(True, alpha=0.35)
        xc = np.array([(b['x0'] + b['x1'])/2 for b in a['bars']]); harm = np.rint(xc).astype(int)
        ax.bar(harm, [b['top'] for b in a['bars']], width=0.7, color=a['bars'][0]['color'])
        ax.set_title(t, fontsize=8); ax.set_xlabel('Harmonic order')
        if k == 0: ax.set_ylabel('Magnitude (% of fundamental), phase B')
        else: ax.tick_params(labelleft=False)
        ax.set_xlim(R(a['xlim'])); ax.set_ylim(R(a['ylim']))
    os.makedirs(os.path.join(OUT, '..', 'optional_final_size'), exist_ok=True)
    fig.savefig(os.path.join(OUT, '..', 'optional_final_size', 'fig4_spectra.pdf'), format='pdf'); plt.close(fig); SNAP = False

THR_X, THR_DY = 3.42, 0.03   # text origin read from the original (x=3.4200, baseline y=0.7300)
if __name__ == '__main__':
    fig3(); fig4(); fig5(); fig6(); fig4_final()
    print('written to', OUT)
