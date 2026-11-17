import json, sys
sys.path.insert(0,'/home/claude/subtasks4/6/scripts')
import costmodel as cm
out={}
for line in ['hs','sub']:
    D=json.load(open(f'/home/claude/subtasks4/5/designs_cons_{line}.json'))
    cand=json.load(open(f'/home/claude/subtasks4/5/candidates_cons_{line}.json'))
    req=D['m_required']
    res={}
    for lv in ['low','central','high']:
        a=cm.a_hw('dc',lv,True,26.2)
        def tot(x): 
            hw=a*x['C']; return dict(C=x['C'],eps=x['eps'],Jcap=x['Jcap'],Jloss=x['Jloss'],Jviol=x['Jviol'],Jhw=hw,J=x['J']+hw,CL=x['Jcap']+x['Jloss']+hw,Ev=x['E_viol_h_yr'],ok=x['n_comply'])
        dd={k:tot(D[k]) for k in ['design_i','design_ii','design_iii']}
        # equal-exceedance: caps
        eq={}
        for capname,cap in [('cap_ii',D['design_ii']['E_viol_h_yr']),('cap_iii',D['design_iii']['E_viol_h_yr'])]:
            ok=[tot(x) for x in cand if x['n_comply']>=req and x['E_viol_h_yr']<=cap+1e-9]
            P=[x for x in ok if abs(x['eps']-1.9)<1e-6]; Q=[x for x in ok if abs(x['eps']-1.9)>1e-6]
            bp=min(P,key=lambda x:x['CL']) if P else None; bq=min(Q,key=lambda x:x['CL']) if Q else None
            eq[capname]=dict(cap=cap,percentile=bp,proposed=bq,red=(100*(bq['CL']-bp['CL'])/bp['CL'] if bp and bq else None))
        res[lv]=dict(designs=dd,a_hw=a,
            red_i=100*(dd['design_iii']['J']-dd['design_i']['J'])/dd['design_i']['J'],
            red_ii=100*(dd['design_iii']['J']-dd['design_ii']['J'])/dd['design_ii']['J'],
            redCL_i=100*(dd['design_iii']['CL']-dd['design_i']['CL'])/dd['design_i']['CL'],
            redCL_ii=100*(dd['design_iii']['CL']-dd['design_ii']['CL'])/dd['design_ii']['CL'],eq=eq)
    out[line]=res
json.dump(out,open('econ_cons_A26.json','w'),indent=1)
for line in out:
    r=out[line]['central']; print(line,'a_hw',round(r['a_hw'],2))
    for k,v in r['designs'].items(): print(' ',k,{a:round(b,2) for a,b in v.items()})
    print('  red J vs i/ii',round(r['red_i'],1),round(r['red_ii'],1),' CL',round(r['redCL_i'],1),round(r['redCL_ii'],1))
    for c,e in r['eq'].items(): print('  ',c,round(e['cap'],1),e['percentile'] and (e['percentile']['C'],round(e['percentile']['CL'],1)), e['proposed'] and (e['proposed']['C'],e['proposed']['eps'],round(e['proposed']['CL'],1)), e['red'] and round(e['red'],1))
    for lv in ['low','high']: print('  ',lv,round(out[line][lv]['red_i'],1),round(out[line][lv]['red_ii'],1))
