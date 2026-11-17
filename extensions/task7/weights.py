from common import *
from rpc_sizing.params import RPC
out = {}
D = json.load(open(os.path.join(HERE, "design_tab_v1.9_q0.99.json")))
Do = json.load(open(os.path.join(HERE, "design_oracle_v2.0.json")))
for cost in [100.0, 150.0, 200.0]:
    for viol in [1.0, 2.0, 4.0]:
        w = dict(cost=cost, price=RPC["energy_price_USD_MWh"], viol=viol)
        Jp = methods(BASE, 750, w)["proposed"]["J"]
        Jw = lambda c: c["Jcap"] * cost / 150.0 + c["Jloss"] + c["Jviol"] * viol / 2.0
        cb = min(D["cands"], key=Jw); co = min(Do["cands"], key=Jw)
        out[f"cost{cost:g}_viol{viol:g}"] = dict(J15=Jp, Jwb=Jw(cb), Cwb=cb["C"], f=cb["f"], Joracle=Jw(co), red_pct=(Jw(cb) / Jp - 1) * 100, red_oracle_pct=(Jw(co) / Jp - 1) * 100)
        print(cost, viol, {k: round(v, 2) for k, v in out[f"cost{cost:g}_viol{viol:g}"].items()})
json.dump(out, open(os.path.join(HERE, "weights.json"), "w"), indent=1)
