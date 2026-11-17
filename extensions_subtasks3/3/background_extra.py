"""Extra runs for the background-unbalance study (same models, same 60 weeks).
(1) IEC-law conventional baseline: eps_u = remaining budget (lim^a - b^a)^(1/a).
(2) Design ignoring the background: C = 10.44 MVA, eps_u = 1 % (no-background design,
    taken from results_background.json) evaluated under every background scenario:
    share of weeks meeting P95 <= 2 %, mean P95, E_viol, J.
"""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/subtasks3/3"); sys.path.insert(0, "/home/claude/code")
import background_unbalance as bu
from rpc_sizing import rpc

R = json.load(open(bu.OUT + "/results_background.json"))
Cnone = R["scen"]["none_0.0"]["proposed"]["C"]; Enone = R["scen"]["none_0.0"]["proposed"]["eps_u"]
out = dict(C_nobg_design=Cnone, eps_nobg_design=Enone, iec_conv={}, ignore_bg={})
# (1) IEC conventional
for b in bu.BG:
    eps = float((bu.LIM ** bu.ALPHA - b ** bu.ALPHA) ** (1 / bu.ALPHA))
    cm = []
    for k in range(bu.NW):
        wk = bu.Week(*bu.load(k)); cm.append(bu.cmin(wk, eps, "iec", b))
    Ch = bu.quant95(cm)
    ev = []; 
    for k in range(bu.NW):
        wk = bu.Week(*bu.load(k)); ev.append(bu.eval_week(wk, Ch, eps, "iec", b))
    Eloss = np.mean([e["E_loss"] for e in ev]); Ev = np.mean([e["real"][0]["E_viol"] for e in ev])
    J, cap = bu.J_of(Ch, Eloss, Ev)
    out["iec_conv"][str(b)] = dict(eps_u=eps, Chat=Ch, J=float(J), E_viol_h_yr=float(Ev * bu.W),
                                   comply=float(np.mean([e["real"][0]["p95"] <= bu.LIM + 1e-6 for e in ev])))
    print("iec conv", b, out["iec_conv"][str(b)], flush=True)
# (2) design ignoring background
names = [("none", 0.0)] + [(n, b) for b in bu.BG for n in ("alg", "rand", "worst", "iec")]
acc = {n: [] for n in names}
for k in range(bu.NW):
    wk = bu.Week(*bu.load(k))
    for (n, b) in names:
        acc[(n, b)].append(bu.eval_week(wk, Cnone, Enone, "rand" if n in ("rand", "worst") else n, b))
for (n, b), ev in acc.items():
    if n == "worst":
        P = [max(x["p95"] for x in w["real"]) for w in ev]
        Evs = [max(x["E_viol"] for x in w["real"]) for w in ev]
        comp = [max(x["p95"] for x in w["real"]) <= bu.LIM + 1e-6 for w in ev]
    else:
        P = [np.mean([x["p95"] for x in w["real"]]) for w in ev]
        Evs = [np.mean([x["E_viol"] for x in w["real"]]) for w in ev]
        comp = [np.mean([x["p95"] <= bu.LIM + 1e-6 for x in w["real"]]) for w in ev]
    Eloss = np.mean([w["E_loss"] for w in ev]); Evm = float(np.mean(Evs))
    J, _ = bu.J_of(Cnone, Eloss, Evm)
    out["ignore_bg"][f"{n}_{b}"] = dict(comply=float(np.mean(comp)), p95_mean=float(np.mean(P)),
                                        p95_max=float(np.max(P)), E_viol_h_yr=Evm * bu.W, J=float(J))
    print("ignore", n, b, out["ignore_bg"][f"{n}_{b}"], flush=True)
json.dump(out, open(bu.OUT + "/results_background_extra.json", "w"), indent=1)
