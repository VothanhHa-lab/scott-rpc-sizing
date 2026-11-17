"""Per-week CSV export of every reported design, all evaluated on the same stored 1-s weekly load.
Needs data/repro_approx_{base,sub}.json (from repro_approx.py). Usage: export_csv.py [approx|exact|cert|all]"""
import sys, json, time, csv
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

what = sys.argv[1] if len(sys.argv) > 1 else "all"
RB = json.load(open(f"{OUT}/data/repro_approx_base.json"))
RS = json.load(open(f"{OUT}/data/repro_approx_sub.json"))
SA = json.load(open(CODE + "/results_exact/stepA.json"))
EPS_A = SA["eps"]; CM = np.array(SA["cmin"])
cdes_ex = {e: q95(CM[:, j]) for j, e in enumerate(EPS_A)}          # exact-model Chat(eps), stored weekly minima
C_FACT = [1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0, 2.5]
c_ex_prop = cdes_ex[1.0] * 1.35                                      # 11.2706
c_ex_corr = cdes_ex[1.9] * 1.0                                       # 11.8251
c_ex_corr_opt = cdes_ex[1.9] * 1.1                                   # 13.0076 (best of the eight factors, Table 12)


def pc_opt(name, rep, N):
    """Percentile (eps=2 %) with optimised C: old 8 candidates U absolute grid (0.25 .. 5 step .25, then .5), as round-3 s2_reselect."""
    W1 = RPC["cost_kUSD_per_MVA"] * 2 * RPC["crf"]
    ws = [load_week(name, k) for k in range(N)]
    Cs = {}
    i2 = rep["eps_grid"].index(2.0)
    chat = rep["cdes"][i2]
    old = [chat * f for f in C_FACT]
    Jold_best = min(rep["J"][i2 * 8 + j] for j in range(8))
    Cmax = min(rep["c_peak"], rep["J"][rep["i_prop"]] / W1)           # round-3 definition (J_old_best of the *whole* search)
    grid = [round(0.25 * i, 2) for i in range(0, 21)]
    c = 5.0
    while c < Cmax + 0.5:
        c += 0.5; grid.append(round(c, 2))
    grid = [g for g in grid if g <= Cmax + 0.5]
    best = None
    need = int(math.ceil(round(0.95 * N, 9)))
    prof = []
    for C in sorted(set(old + grid)):
        evs = [rpc.evaluate(P, Q, C, 2.0, SSC) for P, Q in ws]
        nc = sum(e["p95"] <= LIM + 1e-9 for e in evs)
        cap = RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
        J = cap + RPC["energy_price_USD_MWh"] * np.mean([e["E_loss"] for e in evs]) * WY / 1000 + \
            RPC["viol_price_kUSD_per_pct_h"] * np.mean([e["E_viol"] for e in evs]) * WY
        prof.append((C, J, int(nc)))
        if nc >= need and (best is None or J < best[1]):
            best = (C, J, int(nc))
    return best, prof


def run_design(tag, setname, model, eps, C, sink):
    t = time.time()
    rows = []
    for k in range(NW[setname]):
        P, Q = load_week(setname, k)
        m = eval_week(P, Q, C, eps, model)
        m["week"] = k
        rows.append(m)
    cols = ["week", "C", "eps_u", "P95", "P99", "vmax10", "share_gt2_pct", "E_viol", "E_loss", "J_cap", "J_loss", "J_viol", "J", "E_transfer"]
    with open(f"{OUT}/csv/{tag}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["week"]] + [repr(r[c]) if isinstance(r[c], float) else r[c] for c in cols[1:]])
    sink[tag] = dict(set=setname, model=model, eps_u=eps, C=C, rows=rows)
    print(tag, "C=%.4f eps=%.2f" % (C, eps), "J=%.2f" % np.mean([r["J"] for r in rows]), round(time.time() - t), "s", flush=True)


res = {}
if what in ("approx", "all"):
    # --- high-speed, approximation (8) ---
    bestb, profb = pc_opt("base", RB, 60)
    print("percentile C-opt (base):", bestb, flush=True)
    json.dump(dict(best=bestb, prof=profb), open(f"{OUT}/data/pcopt_base.json", "w"))
    run_design("hs_approx_proposed", "base", "approx", RB["prop"]["eps"], RB["prop"]["C"], res)
    run_design("hs_approx_percentile12", "base", "approx", 2.0, RB["p95"]["C"], res)
    run_design("hs_approx_percentile_Copt", "base", "approx", 2.0, bestb[0], res)
    run_design("hs_approx_peak11", "base", "approx", 2.0, RB["c_peak"], res)
    run_design("hs_approx_full", "base", "approx", 0.0, RB["c_full"], res)
    # --- suburban ---
    bests, profs = pc_opt("sub", RS, 40)
    print("percentile C-opt (sub):", bests, flush=True)
    json.dump(dict(best=bests, prof=profs), open(f"{OUT}/data/pcopt_sub.json", "w"))
    run_design("sub_approx_proposed", "sub", "approx", RS["prop"]["eps"], RS["prop"]["C"], res)
    run_design("sub_approx_percentile12", "sub", "approx", 2.0, RS["p95"]["C"], res)
    run_design("sub_approx_percentile_Copt", "sub", "approx", 2.0, bests[0], res)
if what in ("exact", "all"):
    run_design("hs_exact_proposed", "base", "exact", 1.0, c_ex_prop, res)
    run_design("hs_exact_percentile_corrected", "base", "exact", 1.9, c_ex_corr, res)
    run_design("hs_exact_percentile_corrected_Copt", "base", "exact", 1.9, c_ex_corr_opt, res)
    run_design("hs_exact_of_approx_proposed", "base", "exact", RB["prop"]["eps"], RB["prop"]["C"], res)
    run_design("hs_exact_of_approx_percentile12", "base", "exact", 2.0, RB["p95"]["C"], res)
if what in ("cert", "all"):
    run_design("cert_exact_proposed", "cert", "exact", 1.0, c_ex_prop, res)
    run_design("cert_exact_percentile_corrected", "cert", "exact", 1.9, c_ex_corr, res)
json.dump(res, open(f"{OUT}/data/export_{what}.json", "w"))
