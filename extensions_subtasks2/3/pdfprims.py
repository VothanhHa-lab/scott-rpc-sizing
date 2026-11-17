"""Minimal content-stream interpreter for matplotlib-produced PDFs.
Returns drawing primitives (paths, images) in PDF user space (pt, origin bottom-left),
with CTM applied, plus graphics state (colours, line width, dash, caps, alpha, clip)."""
import pikepdf, copy
import numpy as np

def mul(a, b):  # a then b ; matrices as (a,b,c,d,e,f)
    A = np.array([[a[0], a[1], 0], [a[2], a[3], 0], [a[4], a[5], 1]])
    B = np.array([[b[0], b[1], 0], [b[2], b[3], 0], [b[4], b[5], 1]])
    C = A @ B
    return (C[0,0], C[0,1], C[1,0], C[1,1], C[2,0], C[2,1])

def apply(m, x, y):
    return (m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5])

def parse(path):
    pdf = pikepdf.open(path)
    page = pdf.pages[0]
    gs_res = page.Resources.get('/ExtGState', {})
    prims = []
    st = dict(ctm=(1,0,0,1,0,0), lw=1.0, dash=([],0), cap=0, join=0, stroke=(0,0,0), fill=(0,0,0),
              ca=1.0, CA=1.0, clip=None)
    stack = []
    cur = []  # list of subpaths; each list of ('m'|'l'|'c'|'h', pts)
    pending_clip = False
    for operands, op in pikepdf.parse_content_stream(page):
        op = str(op); o = [float(x) if not isinstance(x, (pikepdf.Array, pikepdf.Name, pikepdf.String)) else x for x in operands]
        if op == 'q': stack.append(copy.deepcopy(st))
        elif op == 'Q': st = stack.pop()
        elif op == 'cm': st['ctm'] = mul(tuple(o), st['ctm'])
        elif op == 'w': st['lw'] = o[0]
        elif op == 'J': st['cap'] = int(o[0])
        elif op == 'j': st['join'] = int(o[0])
        elif op == 'd': st['dash'] = ([float(x) for x in operands[0]], float(operands[1]))
        elif op == 'RG': st['stroke'] = tuple(o)
        elif op == 'rg': st['fill'] = tuple(o)
        elif op == 'G': st['stroke'] = (o[0],)*3
        elif op == 'g': st['fill'] = (o[0],)*3
        elif op == 'gs':
            g = gs_res[operands[0]]
            if '/CA' in g: st['CA'] = float(g.CA)
            if '/ca' in g: st['ca'] = float(g.ca)
        elif op == 'm': cur.append([('m', [apply(st['ctm'], o[0], o[1])])])
        elif op == 'l': cur[-1].append(('l', [apply(st['ctm'], o[0], o[1])]))
        elif op == 'c': cur[-1].append(('c', [apply(st['ctm'], o[i], o[i+1]) for i in (0,2,4)]))
        elif op == 'h': cur[-1].append(('h', []))
        elif op == 're':
            x, y, w, h = o
            cur.append([('m',[apply(st['ctm'],x,y)]),('l',[apply(st['ctm'],x+w,y)]),('l',[apply(st['ctm'],x+w,y+h)]),('l',[apply(st['ctm'],x,y+h)]),('h',[])])
        elif op == 'W': pending_clip = True
        elif op in ('S','f','B','n','f*','B*'):
            if pending_clip:
                pts = [p for sp in cur for seg in sp for p in seg[1]]
                xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
                st['clip'] = (min(xs),min(ys),max(xs),max(ys)); pending_clip=False
            if op != 'n':
                prims.append(dict(kind='path', op=op, sub=cur, lw=st['lw'], dash=st['dash'], cap=st['cap'], join=st['join'],
                                  stroke=st['stroke'], fill=st['fill'], ca=st['ca'], CA=st['CA'], clip=st['clip']))
            cur = []
        elif op == 'Do':
            prims.append(dict(kind='image', name=str(operands[0]), ctm=st['ctm'], clip=st['clip']))
    return pdf, page, prims
