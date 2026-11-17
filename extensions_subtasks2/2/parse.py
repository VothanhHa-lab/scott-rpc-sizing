import re,sys,numpy as np
def parse(f):
    s=open(f).read(); s=s[s.find('</defs>'):]
    out=[]
    for m in re.finditer(r'<path ([^>]*?)/>',s):
        a=m.group(1)
        d=re.search(r' d="([^"]*)"',a).group(1)
        tr=re.search(r'transform="matrix\(([^)]*)\)"',a)
        T=[float(x) for x in tr.group(1).split(',')] if tr else [1,0,0,1,0,0]
        col=re.search(r'stroke="([^"]*)"',a); fill=re.search(r' fill="([^"]*)"',a)
        lw=re.search(r'stroke-width="([^"]*)"',a); da=re.search(r'stroke-dasharray="([^"]*)"',a)
        nums=[float(x) for x in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?',d)]
        pts=np.array(nums).reshape(-1,2) if len(re.findall('[CM LZ]',d))>0 and 'C' not in d else None
        out.append(dict(d=d,T=T,col=col.group(1) if col else None,fill=fill.group(1) if fill else None,lw=float(lw.group(1)) if lw else None,da=da.group(1) if da else None))
    return out
def tpts(p):
    d=p['d']; nums=np.array([float(x) for x in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?',d)])
    pts=nums.reshape(-1,2)
    a,b,c,dd,e,f=p['T']
    X=a*pts[:,0]+c*pts[:,1]+e; Y=b*pts[:,0]+dd*pts[:,1]+f
    return X,Y
