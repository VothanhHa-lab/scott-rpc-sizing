"""Check of the interpolation used for the equal-exceedance optimum: curves built WITHOUT the extra exact evaluations predict E_viol and E_loss
at the extra candidates, which were evaluated with the exact model on all 60 weeks."""
import sys, os, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.interpolate import PchipInterpolator
from lib6 import *
S0 = exact_set()                                      # stored + earlier refinement only
ex = json.load(open(f"{RES}/exact_extra.json"))["records"]
rows = []
for r in ex:
    cs = sorted([c for c in S0 if c.eps == r["eps"] and ok(c)], key=lambda c: c.C)
    if len(cs) < 3 or not (cs[0].C <= r["C"] <= cs[-1].C):
        continue
    C = np.array([c.C for c in cs])
    fE = PchipInterpolator(C, np.log(np.maximum([c.Ev * W for c in cs], 1e-3)))
    fL = PchipInterpolator(C, [c.El * W for c in cs])
    pe, pl = float(np.exp(fE(r["C"]))), float(fL(r["C"]))
    ae, al = r["Ev"] * W, r["El"] * W
    rows.append(dict(eps=r["eps"], C=r["C"], Eviol_pred=pe, Eviol_exact=ae, err_pct=100 * (pe / ae - 1), Eloss_pred=pl, Eloss_exact=al,
                     dloss_kUSD=0.08 * (pl - al)))
    print(f"eps={r['eps']:.2f} C={r['C']:6.2f}  E_viol pred {pe:6.2f} exact {ae:6.2f} ({100*(pe/ae-1):+5.1f} %)   loss cost error {0.08*(pl-al):+.2f} kUSD/yr")
json.dump(rows, open(f"{RES}/validate_interp.json", "w"), indent=1)
if rows:
    print("max |E_viol error| %:", max(abs(x["err_pct"]) for x in rows), " max |loss cost error| kUSD/yr:", max(abs(x["dloss_kUSD"]) for x in rows))
