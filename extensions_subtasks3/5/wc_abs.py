import re,sys
def count(t):
    t=t.replace('~',' ').replace('---',' ').replace('--','-')
    t=re.sub(r'\\%','%',t)
    toks=t.split()
    return len(toks), toks
if __name__=='__main__':
    s=open('/home/claude/urt_v4/manuscript_template.tex').read()
    a=re.search(r'\\begin\{abstract\}\n(.*?)\n\\end\{abstract\}',s,re.S).group(1)
    n,_=count(a); print(n)
