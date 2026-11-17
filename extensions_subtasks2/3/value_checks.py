"""Cross-check numbers recovered from the figures against values stated in the manuscript / Online Resource 2 text.
Vector data (Fig. 4 bars, Fig. 3b curves, threshold line) are exact; the dense waveforms of Figs 3a, 5, 6 exist only as
300-dpi bitmaps in the original, so for those the curve extremes are read from the bitmap (accuracy ~ half a line width + 1 pixel)."""
import json, os, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'data')
L = []
def say(s): print(s); L.append(s)

# ---- Fig 4: THD from bar heights (exact vector data) vs titles / Table A-4 (22.52, 20.92, 6.68 %)
d = json.load(open(f'{D}/fig4_spectra.json'))
for k, (a, ref) in enumerate(zip(d['axes'], [22.52, 20.92, 6.68])):
    tops = np.array([b['top'] for b in a['bars']]); h = np.rint([(b['x0']+b['x1'])/2 for b in a['bars']]).astype(int)
    thd = float(np.sqrt((tops**2).sum()))
    say(f'Fig4({"abc"[k]}): THD from {len(tops)} bars (orders {h[0]}-{h[-1]}) = {thd:.2f} % ; manuscript Table: {ref} %  | h3={tops[h==3][0]:.2f} %, h5={tops[h==5][0]:.2f} %')
a = d['axes'][2]; tops = np.array([b['top'] for b in a['bars']]); h = np.rint([(b['x0']+b['x1'])/2 for b in a['bars']]).astype(int)
say(f'Fig4(c): largest bars at orders {h[np.argsort(tops)[-4:]].tolist()} (text: "harmonics concentrated around order 40")')

# ---- Fig 3b: vector curves
d = json.load(open(f'{D}/fig3_primary_currents.json'))['axes'][1]
A, B, C = d['lines']
say(f'Fig3(b): phase A: max|i| = {max(abs(np.array(A["y"]))):.1e} A (text: phase A carries no current, IUF = 100 %); phase B/C peak = {max(B["y"]):.2f}/{max(C["y"]):.2f} A, B = -C: {np.allclose(B["y"], -np.array(C["y"]), atol=1e-6)}')
say(f'Fig3(b): number of curve vertices = {len(B["x"])}; x from {B["x"][0]:.4f} to {B["x"][-1]:.5f} s')

def px_series(png, extent):
    im = np.asarray(Image.open(os.path.join(D, png)).convert('RGBA')); H, W = im.shape[:2]
    x0, x1, yb, yt = extent
    return im, (lambda c: x0 + (c+0.5)/W*(x1-x0)), (lambda r: yt - (r+0.5)/H*(yt-yb)), W, H

# ---- Fig 5(b): current extremes from the bitmap
d5 = json.load(open(f'{D}/fig5_train.json'))['axes'][1]
im, X, Y, W, H = px_series(d5['images'][0]['file'], d5['images'][0]['extent'])
cols = np.arange(W); t = X(cols)
alpha = im[..., 3] > 128
def ext(tmin, tmax):
    sel = (t >= tmin) & (t <= tmax); rows = np.nonzero(alpha[:, sel].any(axis=1))[0]
    return Y(rows.min()), Y(rows.max())
hi = ext(4.4, 4.95); lo = ext(1.9, 2.3); inr = ext(3.0, 3.04); lowp = ext(1.0, 1.4)
pt_per_A = (d5['box_pt'][3]-d5['box_pt'][1])/(d5['ylim'][1]-d5['ylim'][0])
say(f'Fig5(b) bitmap: high-load peak envelope t in 4.4-4.95 s: +{hi[0]:.0f} / {hi[1]:.0f} A (edge of stroke; text: 532 A);  reclosing spike t in 3.00-3.04 s: +{inr[0]:.0f} / {inr[1]:.0f} A (text: 350 A);  low-load steady peak t 1.0-1.4 s: {lowp[0]:.0f} A -> 350/{lowp[0]:.0f} = {350/lowp[0]:.2f} (text: 1.42)')
say(f'   one stroke half-width plus anti-alias = about {0.5*0.8/pt_per_A + 1/ (H/(d5["images"][0]["extent"][3]-d5["images"][0]["extent"][2])):.1f} A to be subtracted from the quoted bitmap edges')

# ---- Fig 6: DC-link extremes from the bitmaps
d6 = json.load(open(f'{D}/fig6_dclink.json'))['axes']
im, X, Y, W, H = px_series(d6[0]['images'][0]['file'], d6[0]['images'][0]['extent'])
pal = {'green': np.array([44, 160, 44]), 'blue': np.array([31, 119, 180])}
rgb = im[..., :3].astype(int); a_ = im[..., 3] > 128
cls = {k: a_ & (np.abs(rgb - v).sum(axis=2) < 90) for k, v in pal.items()}
t = X(np.arange(W))
def top_bot(mask, tmin, tmax):
    sel = (t >= tmin) & (t <= tmax); rows = np.nonzero(mask[:, sel].any(axis=1))[0]; return Y(rows.min()), Y(rows.max())
hw = 0.5*1.4*(d6[0]['ylim'][1]-d6[0]['ylim'][0])/(d6[0]['box_pt'][3]-d6[0]['box_pt'][1])   # half line width in pu
g_start = top_bot(cls['green'], 0.0, 1.0)[0]; g_re = top_bot(cls['green'], 3.0, 3.4)[0]; b_min = top_bot(cls['blue'], 2.9, 3.1)[1]
say(f'Fig6(a) bitmap: diode start-up peak edge = {g_start:.3f} pu -> centre ~ {g_start-hw:.3f} (text: 1.43 pu);  diode peak after reclosing edge = {g_re:.3f} -> ~{g_re-hw:.3f} (text: 1.31 pu);  4QC minimum edge = {b_min:.3f} -> ~{b_min+hw:.3f} (text: 0.44 pu)')
im2, X2, Y2, W2, H2 = px_series(d6[1]['images'][0]['file'], d6[1]['images'][0]['extent'])
rgb2 = im2[..., :3].astype(int); a2 = im2[..., 3] > 128
blue2 = a2 & (np.abs(rgb2 - pal['blue']).sum(axis=2) < 90); t2 = X2(np.arange(W2))
sel = (t2 >= 2.95) & (t2 <= 3.05); rows = np.nonzero(blue2[:, sel].any(axis=1))[0]
hw2 = 0.5*2.0*(d6[1]['ylim'][1]-d6[1]['ylim'][0])/(d6[1]['box_pt'][3]-d6[1]['box_pt'][1])
say(f'Fig6(b) bitmap: 4QC minimum edge = {Y2(rows.max()):.3f} pu -> ~{Y2(rows.max())+hw2:.3f} (one pixel = {(d6[1]["images"][0]["extent"][3]-d6[1]["images"][0]["extent"][2])/H2:.4f} pu; text: 0.44 pu)')
thr = json.load(open(f'{D}/fig6_dclink.json'))['axes'][1]['lines'][0]
say(f'Fig6(b): protection-threshold line (vector) at U_dc = {thr["y"][0]:.4f} pu (0.7 pu)')
open(os.path.join(HERE, '..', 'value_checks.txt'), 'w').write('\n'.join(L))
