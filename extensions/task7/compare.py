"""Paired comparison of designs (same 60 weeks, same cost model)."""
import glob
from common import *
from scipy import stats
from rpc_sizing.params import RPC, GRID
Wk = RPC["weeks_per_year"]
d = BASE["design"]["750"]; ev = d["evals"]
m15 = methods(BASE, 750)

def Jw_stored(i):
    C = d["cands"][i][1]
    cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
    return np.array([cap + RPC["energy_price_USD_MWh"] * wk[i]["E_loss"] * Wk / 1000 +
                     RPC["viol_price_kUSD_per_pct_h"] * wk[i]["E_viol"] * Wk for wk in ev])
ref = {n: dict(C=m15[n]["C"], eps=m15[n]["eps"], J=m15[n]["J"], Jcap=m15[n]["Jcap"], Jloss=m15[n]["Jloss"],
               Jviol=m15[n]["Jviol"], comply=m15[n]["comply"], p95=m15[n]["p95_mean"], vmax=m15[n]["vmax"],
               share=m15[n]["share"], Eviol=m15[n]["Eviol"], Eloss=m15[n]["Eloss"], Etr=m15[n]["Etr"],
               Jweek=Jw_stored(m15[n]["idx"]).tolist(),
               Eviol_wk=[wk[m15[n]["idx"]]["E_viol"] for wk in ev])
       for n in ["full", "peak", "p95", "p95_Copt", "proposed"]}
# greedy eps=0 (15) with J-optimal factor, and its compliance design
nf = len(BASE["c_fact"])
i0 = min(range(nf), key=lambda f: sum(Jw_stored(f)) )
ref["eps0_best"] = dict(C=d["cands"][i0][1], J=float(Jw_stored(i0).mean()), idx=i0, Jweek=Jw_stored(i0).tolist())
ref["cmin_design_eps"] = {str(e): float(d["c_design"][j]) for j, e in enumerate(BASE["eps_grid"])}

def paired(a, b):
    a, b = np.asarray(a), np.asarray(b); x = a - b; n = len(x)
    h = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n)
    rng = np.random.default_rng(1); bs = [rng.choice(x, n).mean() for _ in range(4000)]
    return dict(mean=float(x.mean()), ci_t=float(h), ci_boot=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                rel_pct=float(x.mean() / b.mean() * 100), share_cheaper=float(np.mean(x < 0)),
                p_wilcoxon=float(stats.wilcoxon(x).pvalue), foldA=float(x[:30].mean()), foldB=float(x[30:].mean()))

out = dict(ref={k: {a: b for a, b in v.items() if a not in ("Jweek", "Eviol_wk")} for k, v in ref.items()}, designs={})
for f in sorted(glob.glob(os.path.join(HERE, "design_*.json"))):
    D = json.load(open(f)); best = min(D["cands"], key=lambda c: c["J"])
    o = {k: best[k] for k in ["f", "C", "J", "Jcap", "Jloss", "Jviol", "comply", "p95_mean", "vmax", "share", "Eviol", "Eloss", "Etr", "dsx_max", "sx_max"]}
    o.update(kind=D["kind"], vstar=D["vstar"], q=D["q"], cdes=D["cdes"], cmin_wk=D["cmin_wk"])
    o["cands"] = [{k: c[k] for k in ["f", "C", "J", "Jcap", "Jloss", "Jviol", "comply", "Eviol", "Etr"]} for c in D["cands"]]
    for rn in ["proposed", "p95", "p95_Copt"]:
        o["vs_" + rn] = paired(best["Jweek"], ref[rn]["Jweek"])
    o["Eviol_wk_vs_proposed"] = paired(np.array(best["Eviol_wk"]) * Wk, np.array(ref["proposed"]["Eviol_wk"]) * Wk)
    out["designs"][D["name"]] = o
    print(f"{D['name']:18s} cdes={D['cdes']:.2f} best f={best['f']} C={best['C']:.2f} J={best['J']:.1f} comply={best['comply']:.2f} "
          f"vs proposed {o['vs_proposed']['rel_pct']:.1f}% (p={o['vs_proposed']['p_wilcoxon']:.2g}, cheaper in {100*o['vs_proposed']['share_cheaper']:.0f}% weeks) "
          f"vs p95 {o['vs_p95']['rel_pct']:.1f}%")
json.dump(out, open(os.path.join(HERE, "compare.json"), "w"), indent=1)
