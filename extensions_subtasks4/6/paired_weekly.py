"""Weekly paired differences of the annual-objective terms (exact model, 60 base weeks) between the certified proposed design (eps 1.0, C 11.27)
and the corrected percentile designs (eps 1.9, C 11.83 = minimum rating; C 13.01 / 12.75 = rating optimised on the stored grid),
with the hardware items included (per-week filter statistic F from results/sx_exact_stored.json).
Output: results/paired_weekly.json; prints mean +- 1.96 se and the number of weeks with a lower objective."""
import sys, os, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
import costmodel as cm

CODE = "/home/claude/code"
RES = "/home/claude/subtasks4/6/results"
A2 = json.load(open(f"{CODE}/results_exact/stepA2.json"))
SX = json.load(open(f"{RES}/sx_exact_stored.json"))
cands = A2["cands"]
assert [tuple(c) for c in SX["cands"]] == [tuple(c) for c in cands]
W = cm.W_YEAR


def idx(eps, C):
    return min(range(len(cands)), key=lambda i: abs(cands[i][0] - eps) + abs(cands[i][1] - C))


def weekly_J(i, opt, level="central", trafo=True):
    e, C = cands[i]
    a_hw = cm.a_hw(opt, level, trafo)
    out = []
    for k in range(60):
        ev = A2["evals"][k][i]
        F = SX["F"][i][k]
        cap = cm.W1_BASE * C + a_hw * C
        loss = cm.PRICE_E / 1000 * (ev["E_loss"] + (cm.filter_loss_coeff() * F if opt == "filter" else 0.0)) * W
        viol = cm.W3 * ev["E_viol"] * W
        out.append(dict(cap=cap, loss=loss, viol=viol, J=cap + loss + viol, caploss=cap + loss, Ev=ev["E_viol"] * W))
    return out


res = {}
ip = idx(1.0, 11.2706)
for label, opt, trafo in (("v7", "none", False), ("TF", "filter", True), ("TD", "dc", True)):
    r = {}
    for bn, (e, C) in (("pct_min", (1.9, 11.825)), ("pct_opt_grid", (1.9, 13.01))):
        ib = idx(e, C)
        p, b = weekly_J(ip, opt, trafo=trafo), weekly_J(ib, opt, trafo=trafo)
        for key in ("J", "caploss", "viol"):
            d = np.array([x[key] for x in p]) - np.array([x[key] for x in b])
            h = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            r[f"{bn}_{key}"] = dict(mean=float(d.mean()), ci95=float(h), weeks_lower=int(np.sum(d < 0)), weeks_equal_or_higher=int(np.sum(d >= 0)),
                                    wilcoxon_p=float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else None)
    res[label] = dict(prop=cands[ip], **r)
    j = r["pct_min_J"]
    print(f"[{label}] proposed ({cands[ip][0]}, {cands[ip][1]:.2f}) minus corrected percentile (min rating): dJ {j['mean']:.1f} +- {j['ci95']:.1f} kUSD/yr, lower in {j['weeks_lower']}/60 weeks; "
          f"d(cap+loss) {r['pct_min_caploss']['mean']:.1f} +- {r['pct_min_caploss']['ci95']:.1f}; vs C-opt(grid) dJ {r['pct_opt_grid_J']['mean']:.1f} +- {r['pct_opt_grid_J']['ci95']:.1f}, lower in {r['pct_opt_grid_J']['weeks_lower']}/60")
json.dump(res, open(f"{RES}/paired_weekly.json", "w"), indent=1)
