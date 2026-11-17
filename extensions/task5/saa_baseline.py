"""Chance-constrained (sample-average-approximation, SAA) RPC sizing baselines.

Run:  nice -n 15 python3 saa_baseline.py base|suburban [n_weeks]

Variants (all with the capacity-constrained compensation law (15) of the paper,
i.e. rpc.compensate with KAPPA and the busbar-voltage current limit):
  SAA-A(alpha): eps_u = 2 %, minimal C with
        (1/N) sum_i 1{VUF_inst,i > 2 %} <= alpha          (pooled 1-s samples)
  SAA-B(alpha): joint decision (eps_u, C): over eps_u in the grid, C_alpha(eps_u)
        is the smallest rating meeting the same chance constraint and the pair
        with minimum (capital + losses) cost is selected.
Both are then evaluated with the SAME model, cost (rpc.annual_cost) and criteria
as Table A of the paper.
"""
import sys, json, time
import numpy as np

sys.path.insert(0, "/home/claude/code")
from rpc_sizing import rpc
from rpc_sizing.params import GRID, RPC

SSC = 750.0
LIM = GRID["vuf_lim"]
W = RPC["weeks_per_year"]
EPS_GRID = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
ALPHAS = [0.05, 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002, 0.0001]


def load_weeks(case, n, step):
    d = {"base": "/home/claude/code/results/base_w%03d.npz",
         "suburban": "/home/claude/code/results_sub/suburban_w%03d.npz"}[case]
    ks = list(range(0, n, step))
    out = []
    for k in ks:
        z = np.load(d % k)
        out.append((z["P"].astype(np.float64), z["Q"].astype(np.float64)))
    return ks, out


class Pool:
    """Pooled 1-s samples; only samples with |S_L| > 2 % Ssc can violate."""

    def __init__(self, weeks):
        self.weeks = weeks
        self.N = sum(len(P) for P, _ in weeks)
        thr = LIM / 100.0 * SSC
        self.sub = []
        for P, Q in weeks:
            m = np.hypot(P, Q) > thr
            self.sub.append((P[m], Q[m]))

    def n_exceed(self, C, eps_u, idx=None):
        n = 0
        for j, (P, Q) in enumerate(self.sub):
            if idx is not None and j not in idx:
                continue
            _, v = rpc.compensate(P, Q, C, eps_u, SSC)
            n += int(np.count_nonzero(v > LIM + 1e-9))
        return n

    def frac(self, C, eps_u):
        return self.n_exceed(C, eps_u) / self.N

    def c_alpha(self, alpha, eps_u, tol=0.002):
        """Smallest C with pooled P{VUF_inst > lim} <= alpha (bisection)."""
        hi = max(float(np.hypot(P, Q).max()) for P, Q in self.weeks) / 2 * 1.1 + 0.1
        lo = 0.0
        if self.frac(0.0, eps_u) <= alpha:
            return 0.0
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            if self.frac(mid, eps_u) <= alpha:
                hi = mid
            else:
                lo = mid
        return hi


def week_c_alpha(P, Q, alpha, eps_u, tol=0.002):
    S = np.hypot(P, Q)
    m = S > LIM / 100.0 * SSC
    Ps, Qs = P[m], Q[m]
    n = len(P)
    f = lambda C: np.count_nonzero(rpc.compensate(Ps, Qs, C, eps_u, SSC)[1] > LIM + 1e-9) / n
    hi, lo = S.max() / 2 * 1.1 + 0.1, 0.0
    if f(0.0) <= alpha:
        return 0.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) <= alpha:
            hi = mid
        else:
            lo = mid
    return hi


def evaluate_design(weeks, C, eps_u):
    """Same criteria as the paper (rpc.evaluate) + P99 of the 10-min VUF."""
    evs, p99, sh_inst = [], [], []
    for P, Q in weeks:
        sx, v = rpc.compensate(P, Q, C, eps_u, SSC)
        v10 = rpc.vuf10(v)
        ex = np.maximum(0.0, v10 - LIM)
        ev = dict(C=C, eps_u=eps_u, p95=rpc.p95(v10), vmax10=float(v10.max()),
                  share_above=float(np.mean(v10 > LIM + 1e-9)),
                  E_viol=float(ex.sum() / 6.0), E_loss=rpc.losses_MWh(sx, C),
                  E_transfer=float(sx.sum() / 3600.0), sx_max=float(sx.max()))
        evs.append(ev)
        p99.append(float(np.quantile(v10, 0.99, method="inverted_cdf")))
        sh_inst.append(float(np.mean(v > LIM + 1e-9)))
    mean = lambda key: float(np.mean([e[key] for e in evs]))
    evm = {k: mean(k) for k in ["p95", "vmax10", "share_above", "E_viol", "E_loss", "E_transfer"]}
    evm["C"] = C
    J, cap, loss, viol = rpc.annual_cost(evm)
    return dict(C=C, eps=eps_u, p95_mean=evm["p95"],
                comply=float(np.mean([e["p95"] <= LIM + 1e-6 for e in evs])),
                vmax=evm["vmax10"], share=evm["share_above"], p99=float(np.mean(p99)),
                p95_max=float(max(e["p95"] for e in evs)),
                inst_share=float(np.mean(sh_inst)),
                Eviol=evm["E_viol"] * W, Eloss=evm["E_loss"] * W, Etr=evm["E_transfer"] * W,
                J=J, Jcap=cap, Jloss=loss, Jviol=viol,
                J_caploss=cap + loss)


def main():
    case = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else (60 if case == "base" else 40)
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    t0 = time.time()
    ks, weeks = load_weeks(case, n, step)
    pool = Pool(weeks)
    print(case, "weeks", len(ks), "samples", pool.N, "violating-candidate share",
          sum(len(p) for p, _ in pool.sub) / pool.N, flush=True)
    res = dict(case=case, weeks=ks, Ssc=SSC, N=pool.N)

    # reference designs (values of the manuscript: design values from base.json / suburban.json)
    sys.path.insert(0, "/home/claude/code")
    from analyse import load, methods
    summ = load("base", "/home/claude/code/results") if case == "base" else load("suburban", "/home/claude/code/results_sub")
    M = methods(summ, int(SSC))
    ref = {}
    for name in ["full", "peak", "p95", "p95_Copt", "proposed"]:
        ref[name] = evaluate_design(weeks, M[name]["C"], M[name]["eps"])
        ref[name]["J_manuscript"] = M[name]["J"]
    res["reference"] = ref
    print("reference done", time.time() - t0, flush=True)

    # sanity: our evaluation equals rpc.evaluate on the first week
    e1 = rpc.evaluate(weeks[0][0], weeks[0][1], M["proposed"]["C"], M["proposed"]["eps"], SSC)
    res["sanity_eval_p95_week0"] = (e1["p95"], evaluate_design(weeks[:1], M["proposed"]["C"], M["proposed"]["eps"])["p95_mean"])

    # SAA-A: eps_u = 2 %, alpha sweep
    A = {}
    for a in ALPHAS:
        C = pool.c_alpha(a, LIM)
        r = evaluate_design(weeks, C, LIM)
        r["alpha"] = a
        r["inst_share_pooled"] = pool.frac(C, LIM)
        A[f"{a:g}"] = r
        print(f"A alpha={a:g} C={C:.3f} comply={r['comply']:.2f} p95={r['p95_mean']:.2f} J={r['J']:.0f}", flush=True)
    res["SAA_A"] = A

    # SAA-B: joint (eps_u, C) chance constraint, cost = capital + losses
    B = {}
    for a in [0.05, 0.01]:
        cand = []
        for e in EPS_GRID:
            C = pool.c_alpha(a, e)
            r = evaluate_design(weeks, C, e)
            r["alpha"] = a
            r["inst_share_pooled"] = pool.frac(C, e)
            cand.append(r)
            print(f"B alpha={a:g} eps={e:g} C={C:.3f} J_capl={r['J_caploss']:.0f} comply={r['comply']:.2f}", flush=True)
        best = min(cand, key=lambda r: r["J_caploss"])
        B[f"{a:g}"] = dict(best=best, grid=cand)
    res["SAA_B"] = B

    # per-week alpha-quantile ratings (spread explains the compliance)
    pw = {}
    for a in [0.05, 0.01]:
        c = np.array([week_c_alpha(P, Q, a, LIM) for P, Q in weeks])
        pw[f"{a:g}"] = dict(mean=float(c.mean()), q95=float(np.quantile(c, 0.95, method="inverted_cdf")),
                            min=float(c.min()), max=float(c.max()), sd=float(c.std(ddof=1)))
    res["per_week_C_alpha"] = pw

    # loss/capital trade-off check: is the cost minimum at the bound C_alpha?
    chk = {}
    for a in [0.05, 0.01]:
        C0 = A[f"{a:g}"]["C"]
        Cs = [C0 * f for f in (1.0, 1.05, 1.1, 1.25, 1.5)]
        chk[f"{a:g}"] = [(C, evaluate_design(weeks, C, LIM)["J_caploss"]) for C in Cs]
    res["capl_cost_vs_C"] = chk

    res["runtime_s"] = time.time() - t0
    with open(f"/home/claude/subtasks/5/results_{case}.json", "w") as f:
        json.dump(res, f, indent=1)
    print("done", res["runtime_s"])


if __name__ == "__main__":
    main()
