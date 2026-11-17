"""Fresh verification, part 2 (consistent capacity limit).
usage: python t3b_fresh.py lock | gen {hs|sub} | eval {hs|sub} {A|B} {v7|cons} {v7|cons}
 sets : A = weeks of t3_fresh.py (seeds SEED0+950000 hs / +960000 sub), used for the v7-model designs;
        B = NEW weeks, seeds SEED0+970000 hs / +980000 sub, generated only after the designs of the consistent model are locked.
 eval {line} {set} {designs family} {model}: designs (i)-(iii) of the family ('v7': designs_locked.json; 'cons': designs_cons_locked.json)
        evaluated on the weeks of the set with the given capacity-limit model."""
import sys, datetime
from common_cons import *
from scipy import stats

mode = sys.argv[1]
NNEW = 60
LOCKC = f"{HERE}/designs_cons_locked.json"
SEEDS = {("hs", "A"): SEED0 + 950000, ("sub", "A"): SEED0 + 960000, ("hs", "B"): SEED0 + 970000, ("sub", "B"): SEED0 + 980000}
TAG = {("hs", "A"): "hs_new", ("sub", "A"): "sub_new", ("hs", "B"): "hsB_new", ("sub", "B"): "subB_new"}
CASE = {"hs": "base", "sub": "suburban"}


def wfile(line, S, k):
    return f"{HERE}/newweeks/{TAG[(line, S)]}_w{k:03d}.npz"


def loadw(line, S, k):
    d = np.load(wfile(line, S, k))
    return d["P"].astype(float), d["Q"].astype(float)


def seeds_used_before():
    used = set()
    for c in CASES:
        used |= {seed_of(c) + k for k in range(200)}
    used |= {SEED0 + 900000 + k for k in range(200)}
    used |= {SEEDS[(l, "A")] + k for l in ("hs", "sub") for k in range(NNEW)}
    return used


if mode == "lock":
    out = dict(utc=datetime.datetime.utcnow().isoformat() + "Z", lines={}, sources={})
    for line in ("hs", "sub"):
        fn = f"{HERE}/designs_cons_{line}.json"
        d = json.load(open(fn))
        out["sources"][line] = dict(file=os.path.basename(fn), sha256=sha256(fn))
        out["lines"][line] = {n: dict(eps=d[n]["eps"], C=d[n]["C"], J_design=d[n]["J"], n_comply_design=d[n]["n_comply"])
                              for n in ("design_i", "design_ii", "design_iii")}
    save_json(out, LOCKC)
    print(json.dumps(out, indent=1))

elif mode == "gen":
    line = sys.argv[2]
    assert os.path.exists(LOCKC), "lock the consistent-model designs first"
    base = SEEDS[(line, "B")]
    assert not ({base + k for k in range(NNEW)} & seeds_used_before()), "seed collision"
    man = []; t0 = time.time()
    for k in range(NNEW):
        f = wfile(line, "B", k)
        if not os.path.exists(f):
            P, Q = week_case(CASE[line], k, base)
            np.savez_compressed(f, P=P.astype(np.float32), Q=Q.astype(np.float32))
            print(f"{TAG[(line,'B')]} week {k} generated {time.time()-t0:.0f}s", flush=True)
        P, Q = loadw(line, "B", k)
        man.append(dict(file=os.path.basename(f), seed=int(base + k), sha256=sha256(f), n=int(len(P)),
                        mean_P_MW=float(P.mean()), peak_S_MVA=float(np.hypot(P, Q).max())))
    save_json(dict(line=line, case=CASE[line], seed_base=int(base), seed_base_formula=("SEED0+970000" if line == "hs" else "SEED0+980000"),
                   SEED0=SEED0, n_weeks=NNEW, generator="rpc_sizing.experiment.week_case(case, k, seed_base)",
                   no_collision_with_seeds="seed_of(case)+k (k<200), SEED0+900000+k (k<200), set A seeds",
                   weeks=man), f"{HERE}/newweeks/manifest_{TAG[(line,'B')]}.json")

elif mode == "eval":
    line, S, fam, model = sys.argv[2:6]
    lock = json.load(open(f"{HERE}/designs_locked.json" if fam == "v7" else LOCKC))["lines"][line]
    tag = f"{line}_{S}_{fam}_{model}"
    fres = f"{HERE}/results_t3b_{tag}.json"
    res = json.load(open(fres)) if os.path.exists(fres) else {}
    t0 = time.time()
    for nm in ("design_i", "design_ii", "design_iii"):
        if nm in res and len(res[nm]["weekly"]) == NNEW:
            continue
        e, C = lock[nm]["eps"], lock[nm]["C"]
        wk = [evaluate_model(*loadw(line, S, k), C, e, model) for k in range(NNEW)]
        res[nm] = dict(eps=e, C=C, weekly=wk)
        save_json(res, fres)
        print(tag, nm, "done", round(time.time() - t0), "s", flush=True)
    summ = {}
    for nm in ("design_i", "design_ii", "design_iii"):
        wk = res[nm]["weekly"]
        p = np.array([w["p95"] for w in wk]); nv = int((p > LIM + 1e-9).sum())
        J, cap, loss, viol = J_of(wk)
        summ[nm] = dict(eps=res[nm]["eps"], C=res[nm]["C"], n_weeks=NNEW, n_viol=nv, rate=nv / NNEW, cp95_upper=cp_upper(nv, NNEW),
                        p95_mean=float(p.mean()), p95_max=float(p.max()), p99_mean=float(np.mean([w["p99"] for w in wk])),
                        vmax_mean=float(np.mean([w["vmax"] for w in wk])), share_above_pct=float(100 * np.mean([w["share"] for w in wk])),
                        J=float(J), Jcap=float(cap), Jloss=float(loss), Jviol=float(viol),
                        E_viol_h_yr=float(np.mean([w["E_viol"] for w in wk]) * WY), E_loss_MWh_yr=float(np.mean([w["E_loss"] for w in wk]) * WY),
                        E_tr_GWh_yr=float(np.mean([w["E_tr"] for w in wk]) * WY / 1000))
        summ[nm]["Jw"] = [J_parts(res[nm]["C"], w["E_loss"], w["E_viol"])[0] for w in wk]
    for a, b in (("design_iii", "design_i"), ("design_iii", "design_ii")):
        d = np.array(summ[a]["Jw"]) - np.array(summ[b]["Jw"])
        try:
            pw = float(stats.wilcoxon(summ[a]["Jw"], summ[b]["Jw"]).pvalue)
        except ValueError:
            pw = float("nan")
        summ[f"paired_{a}_minus_{b}"] = dict(mean=float(d.mean()), ci95=float(1.96 * d.std(ddof=1) / np.sqrt(len(d))),
                                              share_lower=float(np.mean(d < 0)), wilcoxon_p=pw)
    save_json(summ, f"{HERE}/summary_t3b_{tag}.json")
    for nm in ("design_i", "design_ii", "design_iii"):
        s = summ[nm]
        print(f"{tag} {nm}: eps {s['eps']} C {s['C']:.3f} viol {s['n_viol']}/{NNEW} CP95 {s['cp95_upper']:.3f} J {s['J']:.1f} ({s['Jcap']:.1f}/{s['Jloss']:.1f}/{s['Jviol']:.1f})")
