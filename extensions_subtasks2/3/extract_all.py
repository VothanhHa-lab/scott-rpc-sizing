"""Extract vector geometry + raster layers from the four original PDFs and map them to data coordinates.
Usage: python extract_all.py   (reads /home/claude/urt_v3/*.pdf, writes ../data/*.json and ../data/*.png)"""
import json, os, sys
import numpy as np, pikepdf, pdfplumber
from pikepdf import PdfImage
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from pdfprims import parse

SRC = '/home/claude/urt_v3'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data'); os.makedirs(OUT, exist_ok=True)

# tick label values read from the original text layer (checked against pdfplumber words below)
SPEC = {
 'fig3_primary_currents': [dict(xt=[0,1,2,3,4,5], yt=[-100,0,100]),
                           dict(xt=[2.20,2.21,2.22,2.23,2.24,2.25,2.26], yt=[-100,-50,0,50,100])],
 'fig4_spectra': [dict(xt=[0,10,20,30,40,50], yt=[1e-2,1e-1,1,10], ylog=True)]*3,
 'fig5_train':   [dict(xt=[0,1,2,3,4,5], yt=[-40,-20,0,20,40]),
                  dict(xt=[0,1,2,3,4,5], yt=[-400,-200,0,200,400])],
 'fig6_dclink':  [dict(xt=[0,1,2,3,4,5], yt=[0.4,0.6,0.8,1.0,1.2,1.4]),
                  dict(xt=[2.4,2.6,2.8,3.0,3.2,3.4,3.6], yt=[0.4,0.6,0.8,1.0,1.2])],
}

def fit(pt, val):
    A = np.vstack([val, np.ones(len(val))]).T
    (a, b), *_ = np.linalg.lstsq(A, np.array(pt), rcond=None)
    res = np.array(pt) - (a*np.array(val)+b)
    return a, b, float(np.abs(res).max())

def endpoints(p):
    pts = [q for sp in p['sub'] for seg in sp for q in seg[1]]
    return pts

def img_rgba(pdf, page, name):
    xo = page.Resources.XObject[name]
    rgb = PdfImage(xo).as_pil_image().convert('RGB')
    sm = PdfImage(xo.SMask).as_pil_image().convert('L')
    rgba = rgb.copy(); rgba.putalpha(sm)
    return rgba

report = {}
for fig, spec in SPEC.items():
    pdf, page, prims = parse(f'{SRC}/{fig}.pdf')
    W = float(page.MediaBox[2]); H = float(page.MediaBox[3])
    # axes patches: white 'f' rect with CA==0 and 4 pts, not page background
    ax_idx = [i for i,p in enumerate(prims) if p['kind']=='path' and p['op']=='f' and p['CA']==0.0 and p['fill']==(1.0,1.0,1.0)]
    assert len(ax_idx)==len(spec), (fig, ax_idx)
    ax_idx.append(len(prims))
    out = dict(page=[W,H], axes=[])
    for k, sp in enumerate(spec):
        i0, i1 = ax_idx[k], ax_idx[k+1]
        pts = endpoints(prims[i0]); xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
        box = [min(xs), min(ys), max(xs), max(ys)]
        ticks = [p for p in prims[i0:i1] if p['kind']=='path' and p['op']=='B' and len(endpoints(p))==2]
        major = [p for p in ticks if abs(p['lw']-0.8)<1e-6]
        minor = [p for p in ticks if abs(p['lw']-0.6)<1e-6]
        xtk = sorted(endpoints(p)[0][0] for p in major if abs(endpoints(p)[0][1]-box[1])<1e-3 and endpoints(p)[1][1] < box[1])
        ytk = sorted(endpoints(p)[0][1] for p in major if abs(endpoints(p)[0][0]-box[0])<1e-3 and endpoints(p)[1][0] < box[0])
        assert len(xtk)==len(sp['xt']) and len(ytk)==len(sp['yt']), (fig,k,len(xtk),len(ytk))
        ax_, bx_, rx = fit(xtk, sp['xt'])
        yv = np.log10(sp['yt']) if sp.get('ylog') else np.array(sp['yt'], float)
        ay_, by_, ry = fit(ytk, yv)
        def X(px): return (px-bx_)/ax_
        def Y(py):
            v = (py-by_)/ay_
            return 10**v if sp.get('ylog') else v
        xlim = [X(box[0]), X(box[2])]; ylim = [Y(box[1]), Y(box[3])]
        axd = dict(box_pt=box, xlim=xlim, ylim=ylim, xticks=sp['xt'], yticks=sp['yt'], ylog=bool(sp.get('ylog')),
                   fit_resid_pt=[rx, ry], n_minor_ticks=len(minor), lines=[], bars=[], images=[])
        # 'S' lines with clip == box and not grid
        for p in prims[i0:i1]:
            if p['kind']=='image':
                rgba = img_rgba(pdf, page, p['name'])
                fn = f'{fig}_ax{k}_{p["name"].strip("/")}.png'; rgba.save(os.path.join(OUT, fn))
                a,b,c,d,e,f = [float(v) for v in p['ctm']]
                axd['images'].append(dict(file=fn, extent=[X(e), X(e+a), Y(f), Y(f+d)], ctm=[a,b,c,d,e,f], size=rgba.size))
                continue
            if p['clip'] is None or max(abs(np.array(p['clip'])-np.array(box)))>1e-3: continue
            P = endpoints(p)
            if p['op']=='S' and not (len(P)==2 and p['CA']==0.35):
                axd['lines'].append(dict(x=[X(q[0]) for q in P], y=[Y(q[1]) for q in P], lw=p['lw'], dash=p['dash'], color=list(p['stroke']),
                                         cap=p['cap'], pts_pdf=[[q[0],q[1]] for q in P]))
            elif p['op']=='f' and len(P)==4 and p['CA']==0.0:
                xs_=[q[0] for q in P]; ys_=[q[1] for q in P]
                axd['bars'].append(dict(x0=X(min(xs_)), x1=X(max(xs_)), top=Y(max(ys_)), color=list(p['fill']), top_pt=max(ys_)))
        out['axes'].append(axd)
        report[(fig,k)] = (rx, ry)
    json.dump(out, open(os.path.join(OUT, fig+'.json'),'w'), indent=1)
    print(fig, [ (a['xlim'], a['ylim'], a['fit_resid_pt'], len(a['lines']), len(a['bars']), len(a['images'])) for a in out['axes']])

# text layer of the originals (for reference + later comparison)
texts = {}
for fig in SPEC:
    pg = pdfplumber.open(f'{SRC}/{fig}.pdf').pages[0]
    texts[fig] = [dict(text=w['text'], x0=w['x0'], x1=w['x1'], top=w['top'], bottom=w['bottom'], size=w['size'], upright=w['upright'])
                  for w in pg.extract_words(keep_blank_chars=True, extra_attrs=['size','upright'])]
json.dump(texts, open(os.path.join(OUT,'orig_text_layer.json'),'w'), indent=1)
