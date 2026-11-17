"""Fidelity check. (1) strip all text from original and new PDFs, rasterise at 300 dpi, compare pixel by pixel
(everything that is not lettering: axes, ticks, grids, bars, curves, raster layers, legend lines must coincide;
legend FRAMES are re-fitted to the narrower Liberation Sans text and are masked and reported separately).
(2) compare the text layers (strings; positions)."""
import os, sys, json, subprocess, collections
import numpy as np, pikepdf, pdfplumber
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from pdfprims import parse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
SRC = '/home/claude/urt_v3'; NEW = os.path.join(ROOT, 'new'); WORK = os.path.join(ROOT, 'verify'); os.makedirs(WORK, exist_ok=True)
FIGS = ['fig3_primary_currents', 'fig4_spectra', 'fig5_train', 'fig6_dclink']
DPI = 300

def strip_text(src, dst):
    pdf = pikepdf.open(src); page = pdf.pages[0]
    ops = []; intext = False
    for operands, op in pikepdf.parse_content_stream(page):
        s = str(op)
        if s == 'BT': intext = True; continue
        if s == 'ET': intext = False; continue
        if intext: continue
        ops.append((operands, op))
    page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops)); pdf.save(dst)

def raster(pdf, png):
    base = png[:-4]
    subprocess.run(['nice', '-n', '15', 'pdftoppm', '-r', str(DPI), '-png', '-singlefile', pdf, base], check=True)

def legend_boxes(pdf):
    _, page, prims = parse(pdf); boxes = []
    for p in prims:
        if p['kind'] == 'path' and p['op'] == 'B' and p['CA'] == 0.8:
            pts = [q for sp in p['sub'] for seg in sp for q in seg[1]]
            xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes, float(page.MediaBox[3])

summary = {}
for f in FIGS:
    o_nt, n_nt = f'{WORK}/{f}_orig_notext.pdf', f'{WORK}/{f}_new_notext.pdf'
    strip_text(f'{SRC}/{f}.pdf', o_nt); strip_text(f'{NEW}/{f}.pdf', n_nt)
    raster(o_nt, f'{WORK}/{f}_orig_notext.png'); raster(n_nt, f'{WORK}/{f}_new_notext.png')
    A = np.asarray(Image.open(f'{WORK}/{f}_orig_notext.png').convert('RGB')).astype(int)
    B = np.asarray(Image.open(f'{WORK}/{f}_new_notext.png').convert('RGB')).astype(int)
    assert A.shape == B.shape, (A.shape, B.shape)
    diff = np.abs(A - B).max(axis=2)
    mask = np.zeros(diff.shape, bool); s = DPI/72
    for pdf in (f'{SRC}/{f}.pdf', f'{NEW}/{f}.pdf'):
        bx, H = legend_boxes(pdf)
        for (x0, y0, x1, y1) in bx:
            mask[int((H-y1)*s)-3:int((H-y0)*s)+4, int(x0*s)-3:int(x1*s)+4] = True
    outside = diff.copy(); outside[mask] = 0
    n_out = int((outside > 24).sum()); n_in = int(((diff > 24) & mask).sum())
    tot = diff.size
    # overlay: grey = both ink, red = original only, blue = new only
    inkA = A.sum(axis=2) < 700; inkB = B.sum(axis=2) < 700
    ov = np.full(A.shape, 255, np.uint8)
    ov[inkA & inkB] = (140, 140, 140); ov[inkA & ~inkB] = (230, 30, 30); ov[~inkA & inkB] = (30, 60, 230)
    ov[mask & (diff > 24)] = np.where(ov[mask & (diff > 24)] == 255, 255, ov[mask & (diff > 24)])
    Image.fromarray(ov).save(f'{ROOT}/overlay_{f}.png')
    d8 = np.clip(diff*4, 0, 255).astype(np.uint8)
    Image.fromarray(255 - d8).save(f'{ROOT}/diff_{f}.png')
    summary[f] = dict(pixels=tot, diff_gt24_outside_legend_frames=n_out, diff_gt24_inside_legend_frame_areas=n_in,
                      max_diff_outside=int(outside.max()), n_legends=len(bx))
    print(f, summary[f])
json.dump(summary, open(f'{ROOT}/verify_summary.json', 'w'), indent=1)

# ---- text layer comparison
def words(pdf):
    pg = pdfplumber.open(pdf).pages[0]
    return pg.extract_words(keep_blank_chars=True, extra_attrs=['size', 'upright'])
def norm(t): return t.replace('−', '-').replace('–', '-').replace(' ', '')
lines = []
for f in FIGS:
    wo, wn = words(f'{SRC}/{f}.pdf'), words(f'{NEW}/{f}.pdf')
    def rot(pdf):
        ch = pdfplumber.open(pdf).pages[0].chars; out = []; cur = ''
        for c in ch:
            if not c['upright']: cur += c['text']
            elif cur: out.append(cur); cur = ''
        if cur: out.append(cur)
        return out
    so = collections.Counter(norm(w['text']) for w in wo if w['upright']); sn = collections.Counter(norm(w['text']) for w in wn if w['upright'])
    ro, rn = rot(f'{SRC}/{f}.pdf'), rot(f'{NEW}/{f}.pdf')
    lines.append(f'{f}: horizontal strings identical (minus/en-dash glyph variants and spaces ignored): {so == sn}; '
                 f'rotated strings orig={ro} new={rn} identical: {[norm(x) for x in ro] == [norm(x) for x in rn]}')
    if so != sn:
        lines.append('   only in orig: %s  only in new: %s' % (dict(so - sn), dict(sn - so)))
    # centre-point displacement for horizontal words with same text (greedy nearest)
    d = []
    for w in wo:
        if not w['upright']: continue
        cands = [v for v in wn if v['upright'] and norm(v['text']) == norm(w['text'])]
        if not cands: continue
        cx, cy = (w['x0']+w['x1'])/2, (w['top']+w['bottom'])/2
        v = min(cands, key=lambda v: abs((v['x0']+v['x1'])/2-cx) + abs((v['top']+v['bottom'])/2-cy))
        d.append((abs((v['x0']+v['x1'])/2-cx), abs((v['top']+v['bottom'])/2-cy), w['text']))
    dx = max(d)[0]; dy = max(x[1] for x in d)
    big = [(round(x[0],1), round(x[1],1), x[2]) for x in d if x[0] > 6 or x[1] > 4]
    lines.append(f'   max centre displacement of horizontal text: dx={dx:.2f} pt, dy={dy:.2f} pt over {len(d)} items; items moving more than 6 pt in x or 4 pt in y: {big}')
open(f'{ROOT}/text_check.txt', 'w').write('\n'.join(lines)); print('\n'.join(lines))
