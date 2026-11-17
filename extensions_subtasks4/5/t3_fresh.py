"""Task 3: fresh independent verification of the locked designs (i)-(iii) of both lines.
usage: python t3_fresh.py lock | gen {hs|sub} | eval {hs|sub}
 lock : freeze the designs (eps, C) of designs_hs.json / designs_sub.json into designs_locked.json
        (with SHA-256 of the source files and a UTC time stamp) BEFORE any new week is generated.
 gen  : generate 60 new weeks with unused seeds: hs  = week_case('base', k, SEED0+950000),
                                                  sub = week_case('suburban', k, SEED0+960000);
        weeks stored as float32 npz (like the design weeks) + manifest with SHA-256.
 eval : exact-model evaluation of each locked design on the new weeks (evaluation uses the stored float32 data).
"""
import sys, datetime
from common5 import *
from scipy import stats

mode = sys.argv[1]
NNEW = 60
LOCK = f"{HERE}/designs_locked.json"


def seeds_used_before():
    """all seeds that the earlier experiments can have used: seed_of(case)+k (k < 200) and SEED0+900000+k."""
    used = set()
    for c in CASES:
        used |= {seed_of(c) + k for k in range(200)}
    used |= {SEED0 + 900000 + k for k in range(200)}
    return used


if mode == "lock":
    out = dict(utc=datetime.datetime.utcnow().isoformat() + "Z", lines={}, sources={})
    for line in ("hs", "sub"):
        d = json.load(open(f"{HERE}/designs_{line}.json"))
        out["sources"][line] = dict(file=f"designs_{line}.json", sha256=sha256(f"{HERE}/designs_{line}.json"))
        out["lines"][line] = {n: dict(eps=d[n]["eps"], C=d[n]["C"], J_design=d[n]["J"], n_comply_design=d[n]["n_comply"])
                              for n in ("design_i", "design_ii", "design_iii")}
    save_json(out, LOCK)
    print(json.dumps(out, indent=1))

elif mode == "gen":
    line = sys.argv[2]
    assert os.path.exists(LOCK), "lock the designs first"
    case, base, tag = {"hs": ("base", SEED_HS_NEW, "hs_new"), "sub": ("suburban", SEED_SUB_NEW, "sub_new")}[line]
    new = {base + k for k in range(NNEW)}
    assert not (new & seeds_used_before()), "seed collision"
    man = []
    t0 = time.time()
    for k in range(NNEW):
        f = f"{HERE}/newweeks/{tag}_w{k:03d}.npz"
        if not os.path.exists(f):
            P, Q = week_case(case, k, base)
            np.savez_compressed(f, P=P.astype(np.float32), Q=Q.astype(np.float32))
            print(f"{tag} week {k} generated {time.time()-t0:.0f}s", flush=True)
        d = np.load(f)
        P = d["P"].astype(float)
        man.append(dict(file=os.path.basename(f), seed=int(base + k), sha256=sha256(f), n=int(len(P)),
                        mean_P_MW=float(P.mean()), peak_S_MVA=float(np.hypot(P, d["Q"]).max())))
    save_json(dict(line=line, case=case, seed_base=int(base), seed_base_formula=("SEED0+950000" if line == "hs" else "SEED0+960000"),
                   SEED0=SEED0, n_weeks=NNEW, generator="rpc_sizing.experiment.week_case(case, k, seed_base)",
                   no_collision_with_seeds=f"seed_of(case)+k (k<200, all {len(CASES)} cases) and SEED0+900000+k (k<200)",
                   weeks=man), f"{HERE}/newweeks/manifest_{tag}.json")

elif mode == "eval":
    line = sys.argv[2]
    tag = {"hs": "hs_new", "sub": "sub_new"}[line]
    lock = json.load(open(LOCK))["lines"][line]
    fres = f"{HERE}/results_t3_{line}.json"
    res = json.load(open(fres)) if os.path.exists(fres) else {}
    t0 = time.time()
    for nm in ("design_i", "design_ii", "design_iii"):
        if nm in res and len(res[nm]["weekly"]) == NNEW:
            continue
        e, C = lock[nm]["eps"], lock[nm]["C"]
        wk = []
        for k in range(NNEW):
            P, Q = load_week(tag, k)
            wk.append(evaluate_exact(P, Q, C, e))
        res[nm] = dict(eps=e, C=C, weekly=wk)
        save_json(res, fres)
        print(nm, "done", round(time.time() - t0), "s", flush=True)
    summ = {}
    for nm in ("design_i", "design_ii", "design_iii"):
        wk = res[nm]["weekly"]
        p = np.array([w["p95"] for w in wk])
        nv = int((p > LIM + 1e-9).sum())
        J, cap, loss, viol = J_of(wk)
        summ[nm] = dict(eps=res[nm]["eps"], C=res[nm]["C"], n_weeks=NNEW, n_viol=nv, rate=nv / NNEW,
                        cp95_upper=cp_upper(nv, NNEW), p95_mean=float(p.mean()), p95_max=float(p.max()),
                        p99_mean=float(np.mean([w["p99"] for w in wk])), vmax_mean=float(np.mean([w["vmax"] for w in wk])),
                        share_above_pct=float(100 * np.mean([w["share"] for w in wk])),
                        J=float(J), Jcap=float(cap), Jloss=float(loss), Jviol=float(viol),
                        E_viol_h_yr=float(np.mean([w["E_viol"] for w in wk]) * WY),
                        E_loss_MWh_yr=float(np.mean([w["E_loss"] for w in wk]) * WY),
                        E_tr_GWh_yr=float(np.mean([w["E_tr"] for w in wk]) * WY / 1000))
        # J per week (for paired comparison)
        summ[nm]["Jw"] = [J_parts(res[nm]["C"], w["E_loss"], w["E_viol"])[0] for w in wk]
    for a, b in (("design_iii", "design_i"), ("design_iii", "design_ii")):
        d = np.array(summ[a]["Jw"]) - np.array(summ[b]["Jw"])
        try:
            pw = float(stats.wilcoxon(summ[a]["Jw"], summ[b]["Jw"]).pvalue)
        except ValueError:
            pw = float("nan")
        summ[f"paired_{a}_minus_{b}"] = dict(mean=float(d.mean()), ci95=float(1.96 * d.std(ddof=1) / np.sqrt(len(d))),
                                              share_lower=float(np.mean(d < 0)), wilcoxon_p=pw)
    save_json(summ, f"{HERE}/summary_t3_{line}.json")
    for nm in ("design_i", "design_ii", "design_iii"):
        s = summ[nm]
        print(f"{line} {nm}: eps {s['eps']} C {s['C']:.3f}  viol {s['n_viol']}/{NNEW} CP95 {s['cp95_upper']:.3f}  J {s['J']:.1f}"
              f" ({s['Jcap']:.1f}/{s['Jloss']:.1f}/{s['Jviol']:.1f})")
