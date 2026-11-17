"""numbers_overrides.json: values of /home/claude/code/results/numbers.json that change with the corrected line search.
Apply in fill.py after loading numbers.json:  N.update(json.load(open('numbers_overrides.json')))"""
import json, os
import numpy as np
from common import *
from analyse import methods

N = json.load(open(f"{CODE}/results/numbers.json"))
T = json.load(open("tables_updated.json")); t13 = json.load(open("t13_updated.json"))
f1 = lambda x: f"{x:.1f}"; f0 = lambda x: f"{x:.0f}"
sb = load_summary("base"); M = methods(sb, 750)
R = json.load(open("reselect_base_750_1000_500.json"))["750"]
ov = {}
ov["TABLE_7"] = "\n".join(T["t7"]["tex_new"]); ov["TABLE_SUB"] = "\n".join(T["tSub"]["tex_new"])
tabA = N["TABLE_A"].split("\n"); newA = []
for i, line in enumerate(tabA):
    cells = line.rstrip("\\").split(" & ")
    cells[4] = T["tA_columns_new"]["p95_Copt"][i] if i != 1 else "2.0"
    newA.append(" & ".join(cells) + "\\\\")
ov["TABLE_A"] = "\n".join(newA)
co = R["p95copt_new"]
ov["Cco"] = f1(co["C"])
ov["vmax_lo"] = f1(min(M["p95"]["vmax"], co["vmax"], M["proposed"]["vmax"])); ov["vmax_hi"] = f1(max(M["p95"]["vmax"], co["vmax"], M["proposed"]["vmax"]))
ov["Jco_vs_p95"] = "the same" if abs(co["J"] - M["p95"]["J"]) / M["p95"]["J"] < 0.01 else f"a {100*(1-co['J']/M['p95']['J']):.0f}\\% lower"
ov["TABLE_13"] = "\n".join(t13["tex_new"])
reds = [100 * (1 - r["new"]["J"] / r["J_p95"]) for r in t13["rows"]]
Cs = [r["new"]["C"] for r in t13["rows"]]; es = [r["new"]["eps"] for r in t13["rows"]]
ov.update(w_red_lo=f0(min(reds)), w_red_hi=f0(max(reds)), w_C_lo=f1(min(Cs)), w_C_hi=f1(max(Cs)), w_eps_lo=f"{min(es):g}", w_eps_hi=f"{max(es):g}")
# t8
if os.path.exists("t8_updated.json"):
    t8 = json.load(open("t8_updated.json"))["t8"]; done = {r["case"] for r in t8}
    tex = open("tables_new.tex").read().split("\n")
    # rebuild TABLE_8 from the table file: lines between the t8 header and the next blank line
    i = next(k for k, l in enumerate(tex) if l.startswith("%% ===== Table t8")) + 1
    rows = []
    while tex[i].strip():
        if not tex[i].startswith("%%"):
            rows.append(tex[i].split(" % NOT")[0])
        i += 1
    ov["TABLE_8"] = "\n".join(rows)
    dJs = []
    import re
    for r in rows:
        dJs.append(float(re.findall(r"& (\d+)\\\\$", r)[0]))
    ov["s_dJlo"] = f0(min(dJs)); ov["s_dJhi"] = f0(max(dJs))
    ov["_t8_cases_rerun"] = ", ".join(sorted(done))
Rs = json.load(open("reselect_suburban_750_1000.json")); 
# suburban reduction range
msb = load_summary("suburban"); rr = []
for S in (750, 1000, 1500):
    jp = methods(msb, S)["p95"]["J"]
    jn = (Rs[str(S)]["new"]["J"] if str(S) in Rs else methods(msb, S)["proposed"]["J"])
    rr.append(100 * (1 - jn / jp))
ov["sb_red_lo"] = f0(min(rr)); ov["sb_red_hi"] = f0(max(rr))
diff = {k: v for k, v in ov.items() if k.startswith("_") or N.get(k) != v}
json.dump(diff, open("numbers_overrides.json", "w"), indent=1)
print("keys that change:", [k for k in diff if not k.startswith("_")])
for k, v in diff.items():
    if not k.startswith("TABLE"): print(k, ":", N.get(k), "->", v)
