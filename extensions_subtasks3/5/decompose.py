"""Decomposition of the annual-objective differences J = Jcap + Jloss + Jviol for every reported comparison.
Reads stored results only (no heavy computation); writes only to /home/claude/subtasks3/5/.
Run: nice -n 15 env PYTHONDONTWRITEBYTECODE=1 python3 decompose.py
"""
import sys, os, json
import numpy as np
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/claude/code")
os.chdir("/home/claude/code")
from analyse import load, methods
from rpc_sizing.params import RPC

OUT = "/home/claude/subtasks3/5/"
W = RPC["weeks_per_year"]
W1 = RPC["cost_kUSD_per_MVA"] * 2 * RPC["crf"]      # 30.555 kUSD/(MVA yr)
rng = np.random.default_rng(20261112)


def dec(A, B, nameA="baseline", nameB="proposed"):
    """A = baseline, B = proposed; dicts with Jcap, Jloss, Jviol, Eviol (and optionally C)."""
    JA = A["Jcap"] + A["Jloss"] + A["Jviol"]
    JB = B["Jcap"] + B["Jloss"] + B["Jviol"]
    clA, clB = A["Jcap"] + A["Jloss"], B["Jcap"] + B["Jloss"]
    dJ = JB - JA
    d = dict(base=nameA, prop=nameB,
             C_base=A.get("C"), C_prop=B.get("C"),
             J_base=JA, J_prop=JB, dJ=dJ, dJ_pct=100 * dJ / JA,
             cap_base=A["Jcap"], cap_prop=B["Jcap"], dcap=B["Jcap"] - A["Jcap"],
             loss_base=A["Jloss"], loss_prop=B["Jloss"], dloss=B["Jloss"] - A["Jloss"],
             viol_base=A["Jviol"], viol_prop=B["Jviol"], dpen=B["Jviol"] - A["Jviol"],
             dpen_pct=100 * (B["Jviol"] - A["Jviol"]) / A["Jviol"] if A["Jviol"] > 0 else None,
             caploss_base=clA, caploss_prop=clB, dcaploss=clB - clA, dcaploss_pct=100 * (clB - clA) / clA,
             Eviol_base=A["Eviol"], Eviol_prop=B["Eviol"], dEviol=B["Eviol"] - A["Eviol"],
             dEviol_pct=100 * (B["Eviol"] - A["Eviol"]) / A["Eviol"] if A["Eviol"] > 0 else None,
             share_dJ_from_penalty_pct=100 * (B["Jviol"] - A["Jviol"]) / dJ if dJ != 0 else None,
             share_dJ_from_caploss_pct=100 * (clB - clA) / dJ if dJ != 0 else None,
             base_excess_J_pct=100 * (JA / JB - 1), base_excess_caploss_pct=100 * (clA / clB - 1),
             base_excess_Eviol_pct=100 * (A["Eviol"] / B["Eviol"] - 1) if B["Eviol"] > 0 else None)
    return d


def row(name, A, B):
    return dec(A, B, name[0], name[1])


def fmt(d):
    return (f"{d['base']:>22s} -> {d['prop']:<22s} dJ {d['dJ']:+7.1f} ({d['dJ_pct']:+5.1f}%)  dcap {d['dcap']:+6.1f} dloss {d['dloss']:+6.1f} "
            f"dpen {d['dpen']:+7.1f} | cap+loss {d['caploss_base']:.1f}->{d['caploss_prop']:.1f} ({d['dcaploss']:+.1f}, {d['dcaploss_pct']:+.1f}%) | "
            f"Eviol {d['Eviol_base']:.1f}->{d['Eviol_prop']:.1f} ({d['dEviol_pct'] if d['dEviol_pct'] is not None else float('nan'):+.1f}%)  "
            f"penalty share of dJ {d['share_dJ_from_penalty_pct'] if d['share_dJ_from_penalty_pct'] is not None else float('nan'):.0f}%")


out = {}
log = []


def add(key, d):
    out[key] = d
    log.append(f"[{key}]\n  " + fmt(d))


# ------------------------------------------------------------------ tA (approximate model, 60 weeks, 750 MVA)
base = load("base")
mA = methods(base, 750)
add("tA_prop_vs_p95", row(("percentile (12)", "proposed"), mA["p95"], mA["proposed"]))
add("tA_prop_vs_p95_Copt", row(("percentile, C opt.", "proposed"), mA["p95_Copt"], mA["proposed"]))
add("tA_p95Copt_vs_p95", row(("percentile (12)", "percentile, C opt."), mA["p95"], mA["p95_Copt"]))
add("tA_prop_vs_peak", row(("peak (11)", "proposed"), mA["peak"], mA["proposed"]))
add("tA_prop_vs_full", row(("full compensation", "proposed"), mA["full"], mA["proposed"]))

# ------------------------------------------------------------------ tEx (exact model in the loop)
A3 = json.load(open("/home/claude/subtasks/3/analysis3.json"))
AE = json.load(open("/home/claude/subtasks/3/approx_designs_exact.json"))
conv, conv_opt, prop = A3["conv"], A3["conv_opt"], A3["prop"]
add("tEx_prop_vs_corrected", row(("corrected percentile", "proposed (exact)"), conv, prop))
add("tEx_prop_vs_corrected_Copt", row(("corrected perc., C opt.", "proposed (exact)"), conv_opt, prop))
add("tEx_corrCopt_vs_corrected", row(("corrected percentile", "corrected perc., C opt."), conv, conv_opt))
add("tEx_approxprop_vs_approxconv_exacteval", row(("(12) approx. design", "proposed approx. design"), AE["approx_conv"], AE["approx_proposed"]))
add("tEx_prop_exact_vs_approxprop_exacteval", row(("proposed approx. design", "proposed (exact)"), AE["approx_proposed"], prop))

# out-of-sample (90 fresh weeks)
oos = json.load(open("/home/claude/subtasks/3/oos_cost.json"))
for k in oos:
    oos[k]["Eviol"] = oos[k]["Jviol"] / RPC["viol_price_kUSD_per_pct_h"]   # E_viol = Jviol / w3 (kUSD -> %.h/yr)
add("tEx_oos_prop_vs_corrected", row(("corrected perc. (OOS)", "proposed (OOS)"), oos["conv"], oos["prop"]))

# ------------------------------------------------------------------ suburban (tSub)
sb = load("suburban", "results_sub")
for S in (500, 750, 1000, 1500):
    if str(S) in sb["design"]:
        m = methods(sb, S)
        if m["p95"]["J"] > 5:
            add(f"tSub_{S}_prop_vs_p95", row((f"sub (12) @{S}", f"sub proposed @{S}"), m["p95"], m["proposed"]))
mS = methods(sb, 750)
add("tSub_750_prop_vs_p95_Copt", row(("sub perc. C opt. @750", "sub proposed @750"), mS["p95_Copt"], mS["proposed"]))

# ------------------------------------------------------------------ cost-weight sensitivity (t13) and operating cases (t8)
lab = [("Base", {}), ("w3_0", dict(viol=0)), ("w3_0p5", dict(viol=0.5)), ("w3_5", dict(viol=5)),
       ("price_40", dict(price=40)), ("price_160", dict(price=160)), ("convcost_75", dict(cost=75)), ("convcost_225", dict(cost=225))]
for l, w in lab:
    m = methods(base, 750, w)
    add(f"t13_{l}", row((f"(12) [{l}]", f"proposed [{l}]"), m["p95"], m["proposed"]))
LAB8 = ["freq_x0.5", "freq_x1.5", "power_x0.75", "power_x1.25", "no_regen", "regen_4MW", "speed_250", "speed_350",
        "stop_0.5", "poisson", "segments_prev", "diode", "grade_alt"]
for c in LAB8:
    ss = load(c, "results40")
    m = methods(ss, 750)
    if m["p95"]["J"] > 5:
        add(f"t8_{c}", row((f"(12) [{c}]", f"proposed [{c}]"), m["p95"], m["proposed"]))

# ------------------------------------------------------------------ SAA comparisons
saa = json.load(open("/home/claude/subtasks/5/results_saa_summary.json"))
sb_ = saa["base"]
add("tS_SAA1s_1pct_vs_prop", row(("SAA-1s alpha=1%", "proposed"), {**sb_["SAA_1s"]["0.01"]}, sb_["proposed"]))
add("tS_SAA1s_5pct_vs_prop", row(("SAA-1s alpha=5%", "proposed"), {**sb_["SAA_1s"]["0.05"]}, sb_["proposed"]))
add("tS_SAA1s_2pct_vs_prop", row(("SAA-1s alpha=2%", "proposed"), {**sb_["SAA_1s"]["0.02"]}, sb_["proposed"]))
add("tS_SAA1s_astar_vs_prop", row(("SAA-1s alpha*", "proposed"), sb_["SAA_1s_alpha_star"], sb_["proposed"]))
add("tS_SAA10_1pct_vs_prop", row(("SAA-10min 1%", "proposed"), sb_["SAA_10min"]["0.01"], sb_["proposed"]))
add("tS_SAA10_5pct_vs_prop", row(("SAA-10min 5%", "proposed"), sb_["SAA_10min"]["0.05"], sb_["proposed"]))
add("tS_prop_vs_p95", row(("percentile (12)", "proposed"), sb_["percentile"], sb_["proposed"]))
ss_ = saa["suburban"]
add("tS_sub_SAA1s_astar_vs_prop", row(("sub SAA-1s alpha*", "sub proposed"), ss_["SAA_1s_alpha_star"], ss_["proposed"]))

# ------------------------------------------------------------------ window budget (tWB)
WB = json.load(open("/home/claude/subtasks/7/results.json"))["compare"]
ref, des = WB["ref"], WB["designs"]
WBc = des["tab_v1.9_q0.99"]
add("tWB_causal_vs_prop15", row(("proposed (15)", "WB causal"), ref["proposed"], WBc))
add("tWB_causal_vs_p95", row(("percentile (12)", "WB causal"), ref["p95"], WBc))
add("tWB_oracle_vs_prop15", row(("proposed (15)", "WB oracle"), ref["proposed"], des["oracle_v2.0"]))
add("tWB_nofcst_vs_prop15", row(("proposed (15)", "WB no forecast"), ref["proposed"], des["uniform_v1.5"]))
add("tWB_causalcap2_vs_prop15", row(("proposed (15)", "WB causal cap 2%"), ref["proposed"], des["tab_v1.9_q0.99_cap2"]))

# ------------------------------------------------------------------ Pareto statement
par = json.load(open("/home/claude/subtasks/2/pareto.json"))
pm = par["methods"]
pareto = {}
pareto["approx_model_prop_vs_p95"] = dict(
    caploss_pct=out["tA_prop_vs_p95"]["dcaploss_pct"], Eviol_pct=out["tA_prop_vs_p95"]["dEviol_pct"],
    note="reproduces '6.8 % cheaper in capital and loss, 48 % less exceedance' (approx. model, (12) at eps=2)")
pareto["exact_model_prop_vs_corrected"] = dict(
    caploss_pct=out["tEx_prop_vs_corrected"]["dcaploss_pct"], Eviol_pct=out["tEx_prop_vs_corrected"]["dEviol_pct"])
pareto["exact_model_prop_vs_corrected_Copt"] = dict(
    caploss_pct=out["tEx_prop_vs_corrected_Copt"]["dcaploss_pct"], Eviol_pct=out["tEx_prop_vs_corrected_Copt"]["dEviol_pct"])
pareto["exact_model_prop_dominates_corrected_weakly"] = bool(
    prop["Jcap"] + prop["Jloss"] <= conv["Jcap"] + conv["Jloss"] + 1e-9 and prop["Eviol"] <= conv["Eviol"])
pareto["exact_model_prop_dominates_corrected_Copt"] = bool(
    prop["Jcap"] + prop["Jloss"] <= conv_opt["Jcap"] + conv_opt["Jloss"] and prop["Eviol"] <= conv_opt["Eviol"])
pareto["pareto_json_methods"] = {k: dict(on_front=v["on_front"], cost=v["cost"], Eviol=v["Eviol"]) for k, v in pm.items()}
pareto["pareto_json_proposed_idx"] = par["methods"].get("proposed", {})
out["pareto"] = pareto

# ------------------------------------------------------------------ compliance-only (w3 = 0) comparison, exact model
EX = json.load(open("/home/claude/code/results_exact/stepA2.json"))
cands, evs = EX["cands"], EX["evals"]
LIM = 2.0
best = None
rows_ = []
for i, (e, C) in enumerate(cands):
    w = [x[i] for x in evs]
    comply = float(np.mean([x["p95"] <= LIM + 1e-9 for x in w]))
    cap = W1 * C
    loss = RPC["energy_price_USD_MWh"] * np.mean([x["E_loss"] for x in w]) * W / 1000
    viol = RPC["viol_price_kUSD_per_pct_h"] * np.mean([x["E_viol"] for x in w]) * W
    rows_.append(dict(i=i, eps=e, C=C, comply=comply, cap=cap, loss=loss, viol=viol, caploss=cap + loss,
                      Eviol=np.mean([x["E_viol"] for x in w]) * W, p95=float(np.mean([x["p95"] for x in w])),
                      p95max=float(np.max([x["p95"] for x in w]))))
ok = [r for r in rows_ if r["comply"] >= 0.95]
b0 = min(ok, key=lambda r: r["caploss"])
out["exact_compliance_only"] = dict(
    best_caploss_candidate=b0, corrected=dict(cap=conv["Jcap"], loss=conv["Jloss"], caploss=conv["Jcap"] + conv["Jloss"]),
    dcaploss_pct_vs_corrected=100 * (b0["caploss"] / (conv["Jcap"] + conv["Jloss"]) - 1),
    Eviol_of_that_candidate=b0["Eviol"],
    note="min capital+loss among the 72 exact candidates meeting P95<=2% in >=95% of the weeks (w3=0 optimum of the grid)")
log.append(f"[exact w3=0]\n  min cap+loss among compliant exact candidates: eps={b0['eps']} C={b0['C']:.3f} cap+loss={b0['caploss']:.1f} "
           f"(corrected {conv['Jcap']+conv['Jloss']:.1f}; {out['exact_compliance_only']['dcaploss_pct_vs_corrected']:+.1f}%), Eviol {b0['Eviol']:.1f}, comply {b0['comply']}")


# ------------------------------------------------------------------ Pareto check on the 72 exact candidates (compliant ones)
def dom(a, b):   # b dominates a
    return b["caploss"] <= a["caploss"] and b["Eviol"] <= a["Eviol"] and (b["caploss"] < a["caploss"] or b["Eviol"] < a["Eviol"])
front_ex = [a for a in ok if not any(dom(a, b) for b in ok)]
def find(e, C):
    return [r for r in rows_ if r["eps"] == e and abs(r["C"] - C) < 1e-6][0]
pe = {}
for name, (e, C) in {"proposed_exact": (1.0, prop["C"]), "corrected": (1.9, conv["C"]), "corrected_Copt": (1.9, conv_opt["C"])}.items():
    r = find(e, C)
    pe[name] = dict(caploss=r["caploss"], Eviol=r["Eviol"], on_front=bool(any(r["i"] == f["i"] for f in front_ex)),
                    n_dominating=int(sum(bool(dom(r, b)) for b in ok)))
out["exact_pareto_check"] = dict(n_compliant=len(ok), n_front=len(front_ex), designs=pe)
log.append(f"[exact Pareto] {len(ok)} compliant candidates, {len(front_ex)} non-dominated: " + "; ".join(f"{k}: front={v['on_front']}, dominated by {v['n_dominating']}" for k, v in pe.items()))

# Corrected-percentile C-optimisation: J along the C grid at eps = 1.9 (grid factors 1, 1.1, 1.2, ...) and quadratic refinement
g = [r for r in rows_ if r["eps"] == 1.9]
g = sorted(g, key=lambda r: r["C"])[:4]
x = np.array([r["C"] for r in g[:3]]); y = np.array([r["cap"] + r["loss"] + r["viol"] for r in g[:3]])
cf = np.polyfit(x, y, 2)
xm = -cf[1] / (2 * cf[0])
out["corrected_Copt_grid"] = dict(
    grid=[dict(C=r["C"], J=r["cap"] + r["loss"] + r["viol"], comply=r["comply"]) for r in sorted([r for r in rows_ if r["eps"] == 1.9], key=lambda r: r["C"])],
    quad_min_C=float(xm), quad_min_J=float(np.polyval(cf, xm)),
    note="J(C) at eps=1.9 sampled at factors 1,1.1,1.2 x Chat only; the quadratic through the first three points is an ESTIMATE of the continuous optimum, not a computed value")
g1 = sorted([r for r in rows_ if r["eps"] == 1.0], key=lambda r: r["C"])
xa = np.array([r["C"] for r in g1[2:5]]); ya = np.array([r["cap"] + r["loss"] + r["viol"] for r in g1[2:5]])
cf1 = np.polyfit(xa, ya, 2); x1 = -cf1[1] / (2 * cf1[0])
out["proposed_C_grid_quad"] = dict(quad_min_C=float(x1), quad_min_J=float(np.polyval(cf1, x1)),
                                   note="same estimate for the proposed design (eps=1.0), through C=10.02,11.27,12.52")
log.append(f"[C-grid refinement] corrected eps=1.9: quad min at C={xm:.2f}, J~{np.polyval(cf, xm):.1f} (grid 558.8 at 13.01); "
           f"proposed eps=1.0: quad min C={x1:.2f}, J~{np.polyval(cf1, x1):.1f} (grid 489.3 at 11.27)")

# ------------------------------------------------------------------ tCI: fixed designs, bootstrap CI of the split (weeks resampled, B = 10000)
def week_terms(ev_weeks, idx):
    ev = [wk[idx] for wk in ev_weeks]
    El = np.array([e["E_loss"] for e in ev]) * W            # MWh/yr per week-sample
    Ev = np.array([e["E_viol"] for e in ev]) * W
    return ev[0]["C"], RPC["energy_price_USD_MWh"] * El / 1000, RPC["viol_price_kUSD_per_pct_h"] * Ev, Ev


def boot_split(ev_weeks, iA, iB, B=10000):
    CA, lA, vA, EA = week_terms(ev_weeks, iA)
    CB, lB, vB, EB = week_terms(ev_weeks, iB)
    n = len(lA)
    idx = rng.integers(0, n, size=(B, n))
    capA, capB = W1 * CA, W1 * CB
    mlA, mlB = lA[idx].mean(1), lB[idx].mean(1)
    mvA, mvB = vA[idx].mean(1), vB[idx].mean(1)
    JA, JB = capA + mlA + mvA, capB + mlB + mvB
    clA, clB = capA + mlA, capB + mlB
    q = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return dict(B=B, n_weeks=n,
                dJ_pct=q(100 * (JB / JA - 1)), dcaploss_pct=q(100 * (clB / clA - 1)), dcaploss=q(clB - clA),
                dpen=q(mvB - mvA), dloss=q(mlB - mlA), dEviol_pct=q(100 * (mvB / mvA - 1)),
                share_neg_caploss=float(np.mean(clB < clA)))


sbk = {}
d = base["design"]["750"]
ev = d["evals"]
sbk["high_speed_750"] = boot_split(ev, mA["p95"]["idx"], mA["proposed"]["idx"])
ds = sb["design"]["750"]
sbk["suburban_750"] = boot_split(ds["evals"], mS["p95"]["idx"], mS["proposed"]["idx"])
# exact model: corrected percentile -> proposed, 60 weeks, plus C-optimised baseline
ic = [i for i, (e, C) in enumerate(cands) if abs(C - conv["C"]) < 1e-9 and e == 1.9][0]
io = [i for i, (e, C) in enumerate(cands) if abs(C - conv_opt["C"]) < 1e-9 and e == 1.9][0]
ip = [i for i, (e, C) in enumerate(cands) if abs(C - prop["C"]) < 1e-9 and e == 1.0][0]
sbk["exact_prop_vs_corrected"] = boot_split(evs, ic, ip)
sbk["exact_prop_vs_corrected_Copt"] = boot_split(evs, io, ip)
out["tCI_bootstrap_of_split"] = sbk
for k, v in sbk.items():
    log.append(f"[boot {k}] dJ% {v['dJ_pct']}  dcap+loss% {v['dcaploss_pct']}  dcap+loss {v['dcaploss']}  dpen {v['dpen']}  dEviol% {v['dEviol_pct']}  P(cap+loss lower)={v['share_neg_caploss']:.3f}")

# check: the bootstrap point estimate uses the same fixed designs as ci_results.json
ci = json.load(open("/home/claude/subtasks/1/ci_results.json"))
out["tCI_reference"] = dict(
    high_speed=dict(red=ci["base"]["J_fixed_design"]["red"], red_ci=ci["base"]["J_fixed_design"]["red_ci"]),
    suburban=dict(red=ci["suburban"]["J_fixed_design"]["red"], red_ci=ci["suburban"]["J_fixed_design"]["red_ci"]))
out["tCI_split_point"] = dict(high_speed=out["tA_prop_vs_p95"], suburban=out["tSub_750_prop_vs_p95"])

# tEx table rows (for the LaTeX table)
out["tEx_rows"] = dict(
    pct_approx=dict(C=AE["approx_conv"]["C"], eps=AE["approx_conv"]["eps"], J=AE["approx_conv"]["J"], Jcap=AE["approx_conv"]["Jcap"],
                    Jloss=AE["approx_conv"]["Jloss"], Jviol=AE["approx_conv"]["Jviol"], Eviol=AE["approx_conv"]["Eviol"],
                    p95=AE["approx_conv"]["p95"], p95max=AE["approx_conv"]["p95max"], comply=AE["approx_conv"]["comply"]),
    pct_corr=conv, pct_corr_Copt=conv_opt, prop_approx=AE["approx_proposed"], prop_exact=prop)


# summary over the operating cases (base + 13 cases of Table 8)
_keys = ["tA_prop_vs_p95"] + [k for k in out if k.startswith("t8_")]
_cl = [k for k in _keys if out[k]["dcaploss"] < 0]
out["t8_summary"] = dict(n_cases=len(_keys), n_caploss_lower=len(_cl),
                         n_exceedance_lower=int(sum(bool(out[k]["dEviol"] < 0) for k in _keys)),
                         caploss_lower_pct_range=[min(-out[k]["dcaploss_pct"] for k in _cl), max(-out[k]["dcaploss_pct"] for k in _cl)],
                         caploss_higher=[(k, out[k]["dcaploss"]) for k in _keys if out[k]["dcaploss"] > 0],
                         exceedance_higher=[k for k in _keys if out[k]["dEviol"] >= 0])

json.dump(out, open(OUT + "decomposition.json", "w"), indent=1)
open(OUT + "decomposition.log", "w").write("\n".join(log) + "\n")
print("\n".join(log))
