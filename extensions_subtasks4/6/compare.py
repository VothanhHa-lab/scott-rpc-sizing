"""Comparisons (a) same w3 and (b) same exceedance cap, with the hardware items of costmodel.py.
Usage: compare.py <model: exact|approx|sub>  -> results/compare_<model>.json
exact : v7 exact-phasor candidate set (stepA2 + subtasks3/4 refinement + this agent's extra evaluations results/exact_extra.json)
approx: stored approximate-model set base.json + dense grid results/dense_base.json (60 weeks)
sub   : suburban approximate model, stored set + results/dense_sub.json (40 weeks)  [hook: exact suburban results of agent 5, see NOTES.md]
"""
import sys, os, json
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.interpolate import PchipInterpolator
from lib6 import *
import costmodel as cm

MODEL = sys.argv[1] if len(sys.argv) > 1 else "exact"
dec = cm.load_decision()
SCOTT = 0.0 if dec is None else float(dec.get("scott_extra_MVA_total", 0.0))   # hook: agent 2 decision.json (if it appears)

SCEN = {
    "v7": Hw("none", "central", trafo=False, name="v7 (no hardware items)"),
    "T": Hw("none", "central", trafo=True, name="coupling transformers only"),
    "TF": Hw("filter", "central", trafo=True, name="transformers + 100 Hz filter"),
    "TF_low": Hw("filter", "low", trafo=True, name="transformers + filter, low unit costs"),
    "TF_high": Hw("filter", "high", trafo=True, name="transformers + filter, high unit costs"),
    "F_only": Hw("filter", "central", trafo=False, name="filter only (transformers inside 150 kUSD/MVA)"),
    "TD": Hw("dc", "central", trafo=True, name=f"transformers + DC link H_dc = {cm.H_MOD_ms} ms"),
    "TD_low": Hw("dc", "low", trafo=True, name="transformers + DC link, low unit costs"),
    "TD_high": Hw("dc", "high", trafo=True, name="transformers + DC link, high unit costs"),
    "TFS": Hw("filter", "central", trafo=True, scott_MVA=20.0, name="transformers + filter + Scott up-rating 40 to 50 MVA per leg"),
}
if dec is not None and "scenario" in dec:
    SCEN["decision"] = Hw(dec["scenario"].get("opt", "filter"), "central", True, SCOTT, dec["scenario"].get("H_ms"), name="agent-2 decision")

if MODEL == "exact":
    S = exact_set([f"{RES}/exact_extra.json"]); EPS_PCT = 1.9; REF = exact_approx_designs()
elif MODEL == "approx":
    S = approx_set("base", "750", [f"{RES}/dense_base.json"], "approx_stored"); EPS_PCT = 2.0; REF = {}
elif MODEL == "sub":
    S = approx_set("sub", "750", [f"{RES}/dense_sub.json"], "sub_stored"); EPS_PCT = 2.0; REF = {}
elif MODEL == "subex":
    S = approx_set("sub", "750", [], "sub_stored")[0:0]
    _j = json.load(open(f"{RES}/exact_sub_records.json"))["records"]
    S = [Cand(x["eps"], x["C"], x["comply"], x["Ev"], x["El"], x["F"], "agent5", x.get("n", 40)) for x in _j]; EPS_PCT = 1.9; REF = {}
else:
    raise SystemExit("model?")
GRID_ONLY = os.environ.get("GRID_ONLY") == "1"          # only the 72 stored candidates (reproduces the v7 numbers exactly)
if GRID_ONLY:
    S = [c for c in S if c.src in ("stepA2", "stored")]
SUFFIX = "_gridonly" if GRID_ONLY else ""
nan_F = sum(1 for c in S if not np.isfinite(c.F))


def fam(S, kind):
    if kind == "pct":
        return [c for c in S if abs(c.eps - EPS_PCT) < 1e-9]
    return list(S)


def designs(hw):
    pct = [c for c in fam(S, "pct") if ok(c)]
    pmin = min(pct, key=lambda c: c.C)
    popt = min(pct, key=hw.J)
    prop = min([c for c in S if ok(c)], key=hw.J)
    return dict(pct_min=pmin, pct_opt=popt, prop=prop)


def delta(hw, A, B):
    a, b = hw.parts(A), hw.parts(B)
    d = {k: b[k] - a[k] for k in ("cap", "hw", "loss", "filt", "viol", "J", "caploss", "Eviol")}
    d["dJ_pct"] = 100 * d["J"] / a["J"]
    d["dcaploss_pct"] = 100 * d["caploss"] / a["caploss"]
    d["dEviol_pct"] = 100 * d["Eviol"] / a["Eviol"] if a["Eviol"] > 0 else None
    d["dC_pct"] = 100 * (b["C"] - a["C"]) / a["C"]
    return d


def family_min(hw, cap, kind, thr=0.95):
    """Minimise capital + hardware + losses subject to E_viol <= cap and weekly compliance >= thr.  Returns grid-only and interpolated optimum."""
    cs_all = [c for c in fam(S, kind) if ok(c, thr)]
    # grid-only: cheapest evaluated candidate that meets the cap
    feas = [c for c in cs_all if c.Ev * W <= cap + 1e-9]
    grid = min(feas, key=hw.CL) if feas else None
    best = None
    for eps in sorted(set(c.eps for c in cs_all)):
        cs = sorted([c for c in cs_all if c.eps == eps], key=lambda c: c.C)
        if len(cs) < 3:
            continue
        C = np.array([c.C for c in cs]); lE = np.log(np.maximum([c.Ev * W for c in cs], 1e-3))
        lin = np.array([(cm.W1_BASE + cm.a_hw(hw.opt, hw.level, hw.trafo, hw.H)) * c.C + cm.scott_const(hw.level, hw.scott) for c in cs])
        var = np.array([hw.CL(c) for c in cs]) - lin
        fE, fV = PchipInterpolator(C, lE), PchipInterpolator(C, var)
        xs = np.linspace(C.min(), C.max(), 4001)
        idx = np.where(fE(xs) <= np.log(cap))[0]
        if len(idx) == 0:
            continue
        x = xs[idx[0]]
        if idx[0] > 0:                                          # refine the crossing by bisection
            lo, hi = xs[idx[0] - 1], x
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if fE(mid) <= np.log(cap): hi = mid
                else: lo = mid
            x = hi
        cl = (cm.W1_BASE + cm.a_hw(hw.opt, hw.level, hw.trafo, hw.H)) * x + cm.scott_const(hw.level, hw.scott) + float(fV(x))
        r = dict(eps=float(eps), C=float(x), caploss=float(cl), Eviol=float(np.exp(fE(x))))
        if best is None or r["caploss"] < best["caploss"]:
            best = r
    gp = None if grid is None else dict(hw.parts(grid))
    return dict(grid=gp, interp=best)


out = dict(model=MODEL, n_candidates=len(S), nan_F=nan_F, scenarios={})
for key, hw in SCEN.items():
    if hw.opt == "filter" and nan_F:
        continue
    D = designs(hw)
    sc = dict(name=hw.name, designs={k: hw.parts(c) for k, c in D.items()})
    sc["ref_designs"] = {k: hw.parts(c) for k, c in REF.items()}
    # the design of the v7 cost model (certified / EMT-checked design) kept fixed under the new costs
    v7p = min([c for c in S if ok(c) and c.src in ("stepA2", "stored")], key=SCEN["v7"].J)
    sc["fixed_v7_prop"] = hw.parts(v7p)
    sc["fixed_v7_prop_delta_vs_pct_min"] = delta(hw, D["pct_min"], v7p)
    sc["fixed_v7_prop_delta_vs_pct_opt"] = delta(hw, D["pct_opt"], v7p)
    sc["fixed_v7_prop_penalty_vs_reselected_kUSD"] = hw.J(v7p) - hw.J(D["prop"])
    sc["delta_vs_pct_min"] = delta(hw, D["pct_min"], D["prop"])
    sc["delta_vs_pct_opt"] = delta(hw, D["pct_opt"], D["prop"])
    sc["items_at_prop"] = {k: v for k, v in cm.hardware(hw.opt, hw.level, D["prop"].C, hw.trafo, hw.scott, hw.H).items()}
    caps = {"cap_pct_opt": hw.parts(D["pct_opt"])["Eviol"], "cap_prop": hw.parts(D["prop"])["Eviol"]}
    if MODEL == "exact":
        caps["cap_v7_44.86"] = 44.86          # E_viol of the C-optimised corrected percentile design of v7 (13.01 MVA, Table tEx)
    sc["equal_exceedance"] = {}
    for cn, cv in caps.items():
        fp, fq = family_min(hw, cv, "pct"), family_min(hw, cv, "all")
        e = dict(cap=cv, pct=fp, prop=fq)
        for mode in ("grid", "interp"):
            a, b = (fp[mode], fq[mode])
            if a is not None and b is not None:
                a_cl, b_cl = a["caploss"], b["caploss"]
                e[f"saving_{mode}"] = dict(kUSD=a_cl - b_cl, pct=100 * (a_cl - b_cl) / a_cl)
        sc["equal_exceedance"][cn] = e
    out["scenarios"][key] = sc
    p = sc["designs"]
    print(f"[{MODEL}:{key}] pct_min C={p['pct_min']['C']:.2f} J={p['pct_min']['J']:.1f} | pct_opt C={p['pct_opt']['C']:.2f} J={p['pct_opt']['J']:.1f} | "
          f"prop C={p['prop']['C']:.2f} eps={p['prop']['eps']} J={p['prop']['J']:.1f} | dJ%% {sc['delta_vs_pct_min']['dJ_pct']:.1f}/{sc['delta_vs_pct_opt']['dJ_pct']:.1f} "
          f"dCL%% {sc['delta_vs_pct_min']['dcaploss_pct']:.1f}/{sc['delta_vs_pct_opt']['dcaploss_pct']:.1f}")
    for cn, e in sc["equal_exceedance"].items():
        s = e.get("saving_interp"); g = e.get("saving_grid")
        print(f"     {cn} cap={e['cap']:.1f}: pct interp C={e['pct']['interp']['C']:.2f} CL={e['pct']['interp']['caploss']:.1f} | prop interp eps={e['prop']['interp']['eps']} "
              f"C={e['prop']['interp']['C']:.2f} CL={e['prop']['interp']['caploss']:.1f} | saving interp {s['kUSD']:.1f} ({s['pct']:.1f}%)"
              + (f" grid {g['kUSD']:.1f} ({g['pct']:.1f}%)" if g else ""))
json.dump(out, open(f"{RES}/compare_{MODEL}{SUFFIX}.json", "w"), indent=1, default=float)
