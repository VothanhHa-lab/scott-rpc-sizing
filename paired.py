import json, numpy as np
from analyse import load, methods
from rpc_sizing.params import RPC
from scipy import stats
s = load('base'); d = s['design']['750']; ev = d['evals']; W = RPC['weeks_per_year']
m = methods(s, 750)
def Jw(i):
    C = d['cands'][i][1]
    cap = RPC['cost_kUSD_per_MVA']*2*C*RPC['crf']
    return np.array([cap + RPC['energy_price_USD_MWh']*wk[i]['E_loss']*W/1000 + RPC['viol_price_kUSD_per_pct_h']*wk[i]['E_viol']*W for wk in ev])
out = {}
for ref in ['p95', 'p95_Copt', 'peak']:
    a = Jw(m['proposed']['idx']); b = Jw(m[ref]['idx']); diff = a - b
    n = len(diff); h = stats.t.ppf(0.975, n-1)*diff.std(ddof=1)/np.sqrt(n)
    w = stats.wilcoxon(diff)
    out[ref] = dict(mean=diff.mean(), ci=h, rel=diff.mean()/b.mean()*100, share_cheaper=float(np.mean(diff < 0)), p_wilcoxon=float(w.pvalue))
    print(ref, {k: round(v, 4) for k, v in out[ref].items()})
# also E_viol paired
ia, ib = m['proposed']['idx'], m['p95']['idx']
dv = np.array([wk[ia]['E_viol']-wk[ib]['E_viol'] for wk in ev])*W
print('Eviol diff mean %.1f, share lower %.2f, p=%.2g' % (dv.mean(), np.mean(dv < 0), stats.wilcoxon(dv).pvalue))
out['Eviol'] = dict(mean=dv.mean(), share_lower=float(np.mean(dv < 0)), p=float(stats.wilcoxon(dv).pvalue))
json.dump(out, open('results/paired.json', 'w'), indent=1)
