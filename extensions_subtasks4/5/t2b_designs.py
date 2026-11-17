"""Task 2: three designs per line with the exact phasor model in the loop, on the SAME design weeks.
 (i)   corrected percentile: eps = 1.9 % fixed, C = Chat(1.9) = smallest C meeting the weekly criterion in
       >= ceil(.95 N) weeks (= X_(ceil .95N) of the weekly exact C_min);
 (ii)  corrected percentile, C optimised: eps = 1.9 %, C minimising J over (Chat x {1..2.5}) U absolute grid,
       subject to >= ceil(.95 N) compliant weeks;
 (iii) proposed: (C, eps) minimising J over the same candidate set, eps in the grid, same compliance rule.
Candidate set: stage 1 = Chat(eps) x {1,1.1,1.2,1.35,1.5,1.75,2,2.5} for the 9 eps (as exact_sizing.py);
stage 2 = absolute grid with step 0.25 MVA between the two neighbouring factor candidates of the best
stage-1 candidate, for every eps whose best stage-1 J is within 3 % of the overall best, and for eps = 1.9.
usage: python t2b_designs.py {hs|sub} [stage1|stage2|select]"""
import sys
from common5 import *

line = sys.argv[1]
what = sys.argv[2] if len(sys.argv) > 2 else "all"
NW = {"hs": 60, "sub": 40}[line]
STEP = 0.25
TOLJ = 1.03
stepA = json.load(open(f"{HERE}/stepA_{line}.json"))
chat = dict(zip(EPS, stepA["chat"]))
mreq = order_k(NW)


def key(eps, C):
    return f"{eps:.2f}_{C:.5f}"


def cache_path(k):
    return f"{HERE}/cache/ev_{line}_w{k:03d}.json"


def prefill_hs():
    """put the stored stepA2 evaluations (72 candidates x 60 weeks) into the per-week cache."""
    A2 = json.load(open(f"{CODE}/results_exact/stepA2.json"))
    for k in range(NW):
        f = cache_path(k)
        if os.path.exists(f):
            continue
        d = {key(e, C): ev for (e, C), ev in zip(A2["cands"], A2["evals"][k])}
        save_json(d, f)


def ensure(cands, nproc=1):
    """evaluate every (eps, C) in cands on every week (cached)."""
    t0 = time.time()
    for k in range(NW):
        f = cache_path(k)
        d = json.load(open(f)) if os.path.exists(f) else {}
        miss = [(e, C) for (e, C) in cands if key(e, C) not in d]
        if not miss:
            continue
        P, Q = load_week(line, k)
        for (e, C) in miss:
            d[key(e, C)] = evaluate_exact(P, Q, C, e)
        save_json(d, f)
        print(f"{line} week {k}: {len(miss)} new evals, {time.time()-t0:.0f}s", flush=True)


def get(cands):
    out = []
    for k in range(NW):
        d = json.load(open(cache_path(k)))
        out.append([d[key(e, C)] for (e, C) in cands])
    return out    # [week][cand]


def summarise(e, C, evs):
    J, cap, loss, viol = J_of(evs)
    p = np.array([x["p95"] for x in evs])
    return dict(eps=e, C=float(C), J=float(J), Jcap=float(cap), Jloss=float(loss), Jviol=float(viol),
                n_comply=int((p <= LIM + 1e-9).sum()), n_weeks=len(evs),
                p95_mean=float(p.mean()), p95_max=float(p.max()),
                p99_mean=float(np.mean([x["p99"] for x in evs])), vmax_mean=float(np.mean([x["vmax"] for x in evs])),
                share_above_pct=float(100 * np.mean([x["share"] for x in evs])),
                E_viol_h_yr=float(np.mean([x["E_viol"] for x in evs]) * WY),
                E_loss_MWh_yr=float(np.mean([x["E_loss"] for x in evs]) * WY),
                E_tr_GWh_yr=float(np.mean([x["E_tr"] for x in evs]) * WY / 1000))


def stage1_cands():
    return [(e, chat[e] * f) for e in EPS for f in C_FACT]


def stage2_cands(S1):
    ok = [s for s in S1 if s["n_comply"] >= mreq]
    best = min(ok, key=lambda s: s["J"])
    cands = []
    for e in EPS:
        se = [s for s in ok if s["eps"] == e]
        if not se:
            continue
        sb = min(se, key=lambda s: s["J"])
        if sb["J"] > TOLJ * best["J"] and e != 1.9:
            continue
        Cs = [chat[e] * f for f in C_FACT]
        i = int(np.argmin([abs(c - sb["C"]) for c in Cs]))
        lo = Cs[max(i - 1, 0)]
        hi = Cs[min(i + 1, len(Cs) - 1)]
        lo = max(lo, chat[e])
        g = np.arange(math.ceil(lo / STEP - 1e-9), math.floor(hi / STEP + 1e-9) + 1) * STEP
        cands += [(e, float(c)) for c in g if c >= chat[e] - 1e-9]
    return cands


if __name__ == "__main__":
    if line == "hs":
        prefill_hs()
    c1 = stage1_cands()
    if what in ("all", "stage1"):
        ensure(c1)
    ev1 = get(c1)
    S1 = [summarise(e, C, [w[i] for w in ev1]) for i, (e, C) in enumerate(c1)]
    save_json(S1, f"{HERE}/stage1_{line}.json")
    if what == "stage1":
        sys.exit()
    c2 = stage2_cands(S1)
    print("stage-2 candidates:", len(c2), flush=True)
    if what in ("all", "stage2"):
        ensure(c2)
    if what == "stage2":
        sys.exit()
    ev2 = get(c2)
    S2 = [summarise(e, C, [w[i] for w in ev2]) for i, (e, C) in enumerate(c2)]
    S = S1 + [s for s in S2 if key(s["eps"], s["C"]) not in {key(t["eps"], t["C"]) for t in S1}]
    save_json(S, f"{HERE}/candidates_{line}.json")
    okS = [s for s in S if s["n_comply"] >= mreq]
    prop = min(okS, key=lambda s: s["J"])
    i_pct = min((s for s in S if s["eps"] == 1.9 and s["n_comply"] >= mreq and abs(s["C"] - chat[1.9]) < 1e-9), key=lambda s: s["J"])
    pct_opt = min((s for s in okS if s["eps"] == 1.9), key=lambda s: s["J"])
    pct_opt_f = min((s for s in S1 if s["eps"] == 1.9 and s["n_comply"] >= mreq), key=lambda s: s["J"])
    prop_f = min((s for s in S1 if s["n_comply"] >= mreq), key=lambda s: s["J"])
    per_eps = []
    for e in EPS:
        se = [s for s in okS if s["eps"] == e]
        if se:
            b = min(se, key=lambda s: s["J"])
            per_eps.append(dict(eps=e, Chat=chat[e], C=b["C"], J=b["J"], n_comply=b["n_comply"]))
    res = dict(line=line, n_weeks=NW, m_required=mreq, chat=chat, order_stat=mreq,
               design_i=pct_opt if False else i_pct, design_ii=pct_opt, design_iii=prop,
               design_ii_factor_grid_only=pct_opt_f, design_iii_factor_grid_only=prop_f,
               per_eps=per_eps, n_cand_stage1=len(c1), n_cand_stage2=len(c2))
    save_json(res, f"{HERE}/designs_{line}.json")
    for nm in ("design_i", "design_ii", "design_iii", "design_ii_factor_grid_only", "design_iii_factor_grid_only"):
        s = res[nm]
        print(f"{nm:28s} eps={s['eps']:.2f} C={s['C']:.3f} J={s['J']:.1f} (cap {s['Jcap']:.1f} loss {s['Jloss']:.1f} viol {s['Jviol']:.1f}) comply {s['n_comply']}/{NW}")
