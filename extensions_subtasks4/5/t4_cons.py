"""Designs (i)-(iii) with the CONSISTENT capacity limit (exact feeder-terminal voltage in the cap, common_cons.py),
same design weeks, same cost model, same compliance rule (>= ceil(.95 N) weeks with P95 <= 2 %).
 stage A : weekly minimum rating C_min'(eps=1.9) (bisection, tol 0.02 MVA, warm start from the v7-model value);
           Chat'(1.9) = X_(ceil .95N)  -> design (i)
 stage B : local re-optimisation on an absolute grid of step 0.25 MVA
           (iii) eps in {0.5, 0.75, 1.0, 1.25}, window [C_v7(eps) - 0.5, C_v7(eps) + 1.0], extended by 4 steps whenever the best
                 compliant C of an eps (within 3 % of the best J) sits on the window edge;
           (ii)  eps = 1.9, window [Chat', Chat'*1.1 + 1.0], same extension rule.
usage: python t4_cons.py {hs|sub} {A|B}"""
import sys
from common_cons import *

line = sys.argv[1]; stage = sys.argv[2]
NW = {"hs": 60, "sub": 40}[line]
mreq = order_k(NW)
STEP = 0.25


def key(eps, C):
    return f"{eps:.2f}_{C:.5f}"


def cpath(k):
    return f"{HERE}/cache/evc_{line}_w{k:03d}.json"


def ensure(cands):
    t0 = time.time()
    for k in range(NW):
        f = cpath(k)
        d = json.load(open(f)) if os.path.exists(f) else {}
        miss = [(e, C) for (e, C) in cands if key(e, C) not in d]
        if not miss:
            continue
        P, Q = load_week(line, k)
        for (e, C) in miss:
            d[key(e, C)] = evaluate_model(P, Q, C, e, "cons")
        save_json(d, f)
        print(f"{line} cons week {k}: {len(miss)} new evals {time.time()-t0:.0f}s", flush=True)


def get(cands):
    out = []
    for k in range(NW):
        d = json.load(open(cpath(k)))
        out.append([d[key(e, C)] for (e, C) in cands])
    return out


def summarise(e, C, evs):
    J, cap, loss, viol = J_of(evs)
    p = np.array([x["p95"] for x in evs])
    return dict(eps=e, C=float(C), J=float(J), Jcap=float(cap), Jloss=float(loss), Jviol=float(viol),
                n_comply=int((p <= LIM + 1e-9).sum()), n_weeks=len(evs), p95_mean=float(p.mean()), p95_max=float(p.max()),
                p99_mean=float(np.mean([x["p99"] for x in evs])), vmax_mean=float(np.mean([x["vmax"] for x in evs])),
                share_above_pct=float(100 * np.mean([x["share"] for x in evs])),
                E_viol_h_yr=float(np.mean([x["E_viol"] for x in evs]) * WY),
                E_loss_MWh_yr=float(np.mean([x["E_loss"] for x in evs]) * WY),
                E_tr_GWh_yr=float(np.mean([x["E_tr"] for x in evs]) * WY / 1000))


if stage == "A":
    d7 = json.load(open(f"{HERE}/stepA_{line}.json"))
    j = EPS.index(1.9)
    cm = []
    t0 = time.time()
    for k in range(NW):
        f = f"{HERE}/cache/stepAc_{line}_w{k:03d}.json"
        if os.path.exists(f):
            cm.append(json.load(open(f))["cmin"]); continue
        P, Q = load_week(line, k)
        c = cmin_model(P, Q, 1.9, "cons", guess=d7["cmin"][k][j])
        save_json(dict(k=k, eps=1.9, cmin=c, cmin_v7=d7["cmin"][k][j]), f)
        cm.append(c)
        print(f"{line} week {k} cmin' {c:.3f} (v7 {d7['cmin'][k][j]:.3f}) {time.time()-t0:.0f}s", flush=True)
    chat = design_quantile(cm)
    save_json(dict(line=line, eps=1.9, cmin=cm, chat=chat, chat_v7=d7["chat"][j], order_stat=mreq), f"{HERE}/stepA_cons_{line}.json")
    print(line, "Chat'(1.9) =", chat, "v7:", d7["chat"][j])

elif stage == "B":
    A = json.load(open(f"{HERE}/stepA_cons_{line}.json"))
    chat = A["chat"]
    dv = json.load(open(f"{HERE}/designs_{line}.json"))
    centre = {p["eps"]: p["C"] for p in dv["per_eps"]}
    S = {}      # key -> summary

    def run(cands):
        ensure(cands)
        ev = get(cands)
        for i, (e, C) in enumerate(cands):
            S[key(e, C)] = summarise(e, C, [w[i] for w in ev])

    def grid(lo, hi):
        return [round(x * STEP, 6) for x in range(int(math.ceil(lo / STEP - 1e-9)), int(math.floor(hi / STEP + 1e-9)) + 1)]

    run([(1.9, chat)])                                   # design (i)
    EPSB = [0.5, 0.75, 1.0, 1.25]
    win = {e: [centre[e] - 0.5, centre[e] + 1.0] for e in EPSB}
    win[1.9] = [chat, chat * 1.1 + 1.0]
    for rnd in range(4):
        cands = [(e, C) for e in win for C in grid(*win[e]) if key(e, C) not in S]
        if cands:
            run(cands)
        okS = [s for s in S.values() if s["n_comply"] >= mreq]
        best = min([s["J"] for s in okS], default=1e18)
        changed = False
        for e in win:
            se = [s for s in okS if s["eps"] == e]
            if not se:       # nothing compliant: extend upwards
                win[e][1] += 4 * STEP; changed = True; continue
            b = min(se, key=lambda s: s["J"])
            if e != 1.9 and b["J"] > 1.03 * best:
                continue
            Cs = grid(*win[e])
            if b["C"] >= Cs[-1] - 1e-9:
                win[e][1] += 4 * STEP; changed = True
            elif b["C"] <= Cs[0] + 1e-9 and e != 1.9:
                win[e][0] -= 4 * STEP; changed = True
        if not changed:
            break
    allS = list(S.values())
    save_json(allS, f"{HERE}/candidates_cons_{line}.json")
    okS = [s for s in allS if s["n_comply"] >= mreq]
    d_i = S[key(1.9, chat)]
    d_ii = min((s for s in okS if s["eps"] == 1.9), key=lambda s: s["J"])
    d_iii = min(okS, key=lambda s: s["J"])
    per_eps = []
    for e in sorted({s["eps"] for s in allS}):
        se = [s for s in okS if s["eps"] == e]
        if se:
            b = min(se, key=lambda s: s["J"]); per_eps.append(dict(eps=e, C=b["C"], J=b["J"], n_comply=b["n_comply"]))
    res = dict(line=line, model="cons", n_weeks=NW, m_required=mreq, chat=chat, design_i=d_i, design_ii=d_ii, design_iii=d_iii,
               per_eps=per_eps, windows=win, n_cand=len(allS))
    save_json(res, f"{HERE}/designs_cons_{line}.json")
    for nm in ("design_i", "design_ii", "design_iii"):
        s = res[nm]
        print(f"{nm:11s} eps={s['eps']:.2f} C={s['C']:.3f} J={s['J']:.1f} (cap {s['Jcap']:.1f} loss {s['Jloss']:.1f} viol {s['Jviol']:.1f}) comply {s['n_comply']}/{NW}")
    print("per eps:", [(p["eps"], round(p["C"], 2), round(p["J"], 1)) for p in per_eps])
