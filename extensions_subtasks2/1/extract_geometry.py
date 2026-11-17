import re,sys,json
def parse_color(c):
    if c in (None,'none'): return None
    v=[float(x.strip().rstrip('%'))/100 for x in re.findall(r'rgb\(([^)]*)\)',c)[0].split(',')]
    return tuple(round(x,4) for x in v)
def attr(t,n):
    m=re.search(r'\b'+n+r'="([^"]*)"',t); return m.group(1) if m else None
def run(svg):
    s=open(svg).read()
    s=re.sub(r'<defs>.*?</defs>','',s,flags=re.S)
    items=[]
    for m in re.finditer(r'<path\b[^>]*>',s):
        t=re.sub(r'\s+',' ',m.group(0))
        d=attr(t,'d'); tr=attr(t,'transform')
        if tr:
            a,b,c,dd,e,f=[float(x) for x in re.findall(r'matrix\(([^)]*)\)',tr)[0].split(',')]
        else: a,b,c,dd,e,f=1,0,0,1,0,0
        toks=re.findall(r'[MLCZ]|-?[\d.]+',d)
        segs=[];i=0;cmd=None
        while i<len(toks):
            if toks[i] in 'MLCZ': cmd=toks[i]; i+=1
            n={'M':2,'L':2,'C':6,'Z':0}[cmd]
            vals=[float(x) for x in toks[i:i+n]]; i+=n
            pts=[]
            for k in range(0,len(vals),2):
                x,y=vals[k],vals[k+1]
                pts+= [round(a*x+c*y+e,3), round(b*x+dd*y+f,3)]
            segs.append((cmd,pts))
            if cmd=='Z': pass
        sw=attr(t,'stroke-width'); 
        it=dict(fill=parse_color(attr(t,'fill')),stroke=parse_color(attr(t,'stroke')),
                lw=round(float(sw)*abs(a),3) if sw else 0,
                dash=[round(float(x)*abs(a),3) for x in attr(t,'stroke-dasharray').split()] if attr(t,'stroke-dasharray') else None,
                cap=attr(t,'stroke-linecap'),join=attr(t,'stroke-linejoin'),segs=segs)
        items.append(it)
    return items
if __name__=='__main__':
    its=run(sys.argv[1])
    for i,it in enumerate(its):
        xs=[v for c,p in it['segs'] for v in p[0::2]]; ys=[v for c,p in it['segs'] for v in p[1::2]]
        print(i,'F' if it['fill'] else '-',it['fill'],it['stroke'],it['lw'],it['dash'],len(it['segs']),'bbox',round(min(xs),1),round(min(ys),1),round(max(xs),1),round(max(ys),1))
