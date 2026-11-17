import re, sys
src = open('/home/claude/urt_v3/manuscript_template.tex').read()
i = src.index('\\begin{thebibliography}'); j = src.index('\\end{thebibliography}') + len('\\end{thebibliography}')
block = src[i:j]
lines = block.split('\n')
dois = {
 'b3':'10.1109/TPWRD.2004.829920','b4':'10.1109/TPEL.2010.2060360','b5':'10.2219/rtriqr.45.64',
 'b6':'10.1049/iet-pel.2011.0292','b7':'10.1109/TPEL.2013.2292612','b8':'10.1049/iet-gtd.2015.0513',
 'b9':'10.1109/ACCESS.2019.2949099','b10':'10.3390/en13246662','b11':'10.1109/MELE.2019.2962886',
 'b12':'10.1109/TTE.2022.3158946','b13':'10.1109/JESTPE.2019.2953962','b14':'10.1016/j.epsr.2025.111830',
 'b20':'10.3390/en14010253','b21':'10.1109/TPWRD.2022.3144210','b22':'10.3390/en14041214',
 'b23':'10.1016/j.epsr.2025.111575','b24':'10.1016/j.epsr.2023.110048','b25':'10.1109/TTE.2022.3207212',
 'b26':'10.1109/TIA.1985.349618','b28':'10.1109/TTE.2016.2584921','b29':'10.1109/ICHQP.2000.897765',
 'b33':'10.1109/ICECA49313.2020.9297599','b34':'10.1109/TPEL.2007.900456'}
out=[]
for ln in lines:
    m = re.match(r'\\bibitem\{(\w+)\}', ln)
    if m:
        k = m.group(1)
        if k in dois:
            assert '\\url' not in ln, k
            ln = ln + ' \\url{https://doi.org/%s}' % dois[k]
        if k == 'b2':
            ln = ln.replace(' (Hoboken, NJ: Wiley) \\url{https://doi.org/10.1002/9781119517733}', ' (Publicis Publishing/Wiley)')
            assert '9781119517733' not in ln
        if k == 'b33':
            assert 'pp 1652--9' in ln
            ln = ln.replace('pp 1652--9', 'pp 12--20')
        if k == 'c3':
            ln = ln.replace('Final Report} (Ljubljana', 'Final Report} (corrigendum of 8 September 2023) (Ljubljana')
            assert 'corrigendum' in ln
        if k == 'b31':
            out.append('% FLAG b31: EN 50160:2010+A3:2019 is listed as withdrawn; current edition is EN 50160:2022 (published Dec 2022; amendment A1:2025).')
            out.append('% Replacement candidate (authors to confirm that the 2 % / 95 % weekly unbalance clause is unchanged before switching):')
            out.append('% \\bibitem{b31} EN 50160:2022 \\textit{Voltage Characteristics of Electricity Supplied by Public Electricity Networks} (Brussels: CENELEC)')
        if k == 'c4' or k == 'c5':
            pass
    out.append(ln)
res='\n'.join(out)
open('refs_verified.tex','w').write(res+'\n')
print(res.count('\\bibitem'))
