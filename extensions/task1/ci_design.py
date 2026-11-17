"""Sub-task 1: uncertainty of the design values (order-statistic CI, bootstrap, convergence).
Run: nice -n 15 python3 ci_design.py   (single process)"""
import sys, json, time, os
sys.path.insert(0, "/home/claude/code")
os.chdir("/home/claude/code")
import numpy as np
from scipy import stats
from analyse import load, methods, weekly_cmin
from rpc_sizing import rpc
from rpc_sizing.params import RPC

OUT = "/home/claude/subtasks/1"
W = RPC["weeks_per_year"]
B = 10000
SEED = 20261111
SSC = 750


def qinv(x, p=0.95):
    return np.quantile(x, p, method="inverted_cdf")


def os_ci(N, p=0.95, conf=0.95):
    """Distribution-free CI [X_(r), X_(s)] for the p-quantile: coverage = P(r <= Bin(N,p) <= s-1).
    s = N+1 stands for an unbounded upper end. Returns the narrowest (s-r) interval with
    s <= N (if one exists) and the narrowest with s <= N+1; also the best coverage with s <= N."""
    cdf = lambda k: stats.binom.cdf(k, N, p)
    cov = lambda r, s: cdf(s - 1) - cdf(r - 1)
    best = {}
    for smax, tag in [(N, "bounded"), (N + 1, "open")]:
        c = [(s - r, -r, r, s) for r in range(1, N + 1) for s in range(r + 1, smax + 1) if cov(r, s) >= conf]
        if c:
            _, _, r, s = min(c)
            best[tag] = dict(r=r, s=s, coverage=float(cov(r, s)))
        else:
            best[tag] = None
    # best achievable coverage of [X_(r), X_(N)] for r small
    best["max_cov_bounded_upper"] = float(cov(1, N))
    best["rank_est"] = int(np.ceil(N * p))
    return best


def week_data(case_prefix, k):
    dd = "results" if case_prefix == "base" else "results_sub"
    d = np.load(f"/home/claude/code/{dd}/{case_prefix}_w{k:03d}.npz")
    return d["P"].astype(float), d["Q"].astype(float)


def J_table(prefix, N, eps, fac, x, ssc, cache):
    """J_w(C=fac*x_(j); eps) for every week w and every order statistic j (exact re-evaluation)."""
    xs = np.sort(x)
    key = (prefix, eps, fac)
    if key in cache:
        return xs, cache[key]
    T = np.zeros((N, N))
    for w in range(N):
        P, Q = week_data(prefix, w)
        for j, c in enumerate(xs):
            ev = rpc.evaluate(P, Q, float(fac * c), eps, ssc)
            T[w, j] = (RPC["cost_kUSD_per_MVA"] * 2 * ev["C"] * RPC["crf"]
                       + RPC["energy_price_USD_MWh"] * ev["E_loss"] * W / 1000
                       + RPC["viol_price_kUSD_per_pct_h"] * ev["E_viol"] * W)
    cache[key] = T
    return xs, T


def boot_case(label, summ, prefix, N, eps_star, fac_star, rng, cache):
    nf = summ["c_fact"]
    m = methods(summ, SSC)
    x2 = weekly_cmin(summ, SSC, 2.0)
    xs_ = weekly_cmin(summ, SSC, eps_star)
    res = dict(N=N, eps_star=eps_star, fac_star=fac_star)
    assert abs(m["proposed"]["C"] - fac_star * qinv(xs_)) < 1e-9, (m["proposed"]["C"], fac_star * qinv(xs_))
    assert abs(m["p95"]["C"] - qinv(x2)) < 1e-9
    r = int(np.ceil(N * 0.95))
    # ---- 1) order-statistic CI
    res["order_stat"] = {}
    for tag, x in [("eps2", x2), ("eps_star", xs_)]:
        info = os_ci(N)
        xsr = np.sort(x)
        d = dict(estimate=float(qinv(x)), rank_est=info["rank_est"], max_cov_bounded_upper=info["max_cov_bounded_upper"])
        for t in ["bounded", "open"]:
            v = info[t]
            if v is None:
                d[t] = None
            else:
                hi = float(xsr[v["s"] - 1]) if v["s"] <= N else None
                d[t] = dict(r=v["r"], s=v["s"], coverage=v["coverage"], lo=float(xsr[v["r"] - 1]), hi=hi)
        res["order_stat"][tag] = d
    # ---- 2) bootstrap design values
    idx = rng.integers(0, N, size=(B, N))
    out = {}
    for tag, x, fac in [("eps2", x2, 1.0), ("eps_star", xs_, fac_star)]:
        xb = x[idx]
        order = np.argsort(xb, axis=1, kind="stable")
        qpos = order[:, r - 1]                        # position (0..N-1) in resample of the quantile
        wk = np.take_along_axis(idx, qpos[:, None], 1)[:, 0]   # original week that provides the quantile
        qv = x[wk]
        out[tag] = dict(qv=qv, wk=wk)
        lo, hi = np.percentile(qv, [2.5, 97.5])
        res.setdefault("boot_design", {})[tag] = dict(
            estimate=float(qinv(x)), boot_mean=float(qv.mean()), boot_sd=float(qv.std(ddof=1)),
            lo=float(lo), hi=float(hi), rating_lo=float(fac * lo), rating_hi=float(fac * hi), factor=fac,
            n_distinct=int(len(np.unique(qv))))
    # ---- 3) bootstrap J, cost reduction
    # (a) designs fixed at the base-case values, only weeks resampled (stored evaluations)
    d750 = summ["design"][str(SSC)]
    ev = d750["evals"]
    def Jw_fixed(i):
        C = d750["cands"][i][1]
        return np.array([RPC["cost_kUSD_per_MVA"] * 2 * C * RPC["crf"]
                         + RPC["energy_price_USD_MWh"] * wk_[i]["E_loss"] * W / 1000
                         + RPC["viol_price_kUSD_per_pct_h"] * wk_[i]["E_viol"] * W for wk_ in ev])
    Jc, Jp = Jw_fixed(m["p95"]["idx"]), Jw_fixed(m["proposed"]["idx"])
    assert abs(Jc.mean() - m["p95"]["J"]) < 1e-6 and abs(Jp.mean() - m["proposed"]["J"]) < 1e-6
    Jc_b, Jp_b = Jc[idx].mean(1), Jp[idx].mean(1)
    red_b = 100 * (1 - Jp_b / Jc_b)
    pc = lambda a: [float(v) for v in np.percentile(a, [2.5, 97.5])]
    res["J_fixed_design"] = dict(
        J_p95=float(Jc.mean()), J_prop=float(Jp.mean()), red=float(100 * (1 - Jp.mean() / Jc.mean())),
        J_p95_ci=pc(Jc_b), J_prop_ci=pc(Jp_b), red_ci=pc(red_b), dJ_ci=pc(Jp_b - Jc_b),
        red_sd=float(red_b.std(ddof=1)), share_red_pos=float(np.mean(red_b > 0)))
    # (b) full design rule re-run in every resample: C = fac * 95%-quantile of resampled weekly C_min,
    #     J re-evaluated exactly (rpc.evaluate) at that C on the resampled weeks
    t0 = time.time()
    xs_c, Tc = J_table(prefix, N, 2.0, 1.0, x2, SSC, cache)
    xs_p, Tp = J_table(prefix, N, eps_star, fac_star, xs_, SSC, cache)
    print(label, "J tables", round(time.time() - t0), "s", flush=True)
    rank_of = {}
    for tag, x in [("eps2", x2), ("eps_star", xs_)]:
        rk = np.empty(N, int); rk[np.argsort(x, kind="stable")] = np.arange(N)
        rank_of[tag] = rk
    jc = rank_of["eps2"][out["eps2"]["wk"]]
    jp = rank_of["eps_star"][out["eps_star"]["wk"]]
    Jc_f = Tc[idx, jc[:, None]].mean(1)
    Jp_f = Tp[idx, jp[:, None]].mean(1)
    red_f = 100 * (1 - Jp_f / Jc_f)
    # consistency check: table at the base rank reproduces stored J
    jc0 = int(rank_of["eps2"][np.argsort(x2, kind="stable")[r - 1]]); jp0 = int(rank_of["eps_star"][np.argsort(xs_, kind="stable")[r - 1]])
    assert abs(Tc[:, jc0].mean() - m["p95"]["J"]) < 1e-6 and abs(Tp[:, jp0].mean() - m["proposed"]["J"]) < 1e-6
    res["J_full_rule"] = dict(
        J_p95_ci=pc(Jc_f), J_prop_ci=pc(Jp_f), red_ci=pc(red_f), dJ_ci=pc(Jp_f - Jc_f),
        J_p95_mean=float(Jc_f.mean()), J_prop_mean=float(Jp_f.mean()), red_mean=float(red_f.mean()),
        red_sd=float(red_f.std(ddof=1)), share_red_pos=float(np.mean(red_f > 0)),
        rating_p95_ci=pc(out["eps2"]["qv"]), rating_prop_ci=pc(fac_star * out["eps_star"]["qv"]))
    # (c) selection stability of eps_u (stored candidate grid, fixed C values, resampled weeks)
    cost_mat = np.array([Jw_fixed(i) for i in range(len(eps_g(summ)) * len(nf))])   # cand x weeks
    Jb_all = cost_mat[:, idx].mean(2) if False else None
    sel = np.zeros(len(eps_g(summ)))
    sel_c = {}
    chunk = 500
    for a in range(0, B, chunk):
        Jm = cost_mat[:, idx[a:a + chunk]].mean(2)          # cand x chunk
        bi = Jm.argmin(0)
        for b_ in bi:
            sel_c[int(b_)] = sel_c.get(int(b_), 0) + 1
            sel[int(b_) // len(nf)] += 1
    res["selection"] = dict(eps_share={f"{e:g}": float(v / B) for e, v in zip(eps_g(summ), sel)},
                            cand_share_top={str(k): v / B for k, v in sorted(sel_c.items(), key=lambda kv: -kv[1])[:4]},
                            base_idx=int(m["proposed"]["idx"]))
    return res


def eps_g(s):
    return s["eps_grid"]


def convergence(x_dict, N, rng, ns, R=4000):
    """Sampling spread of the design value (95 % quantile) for n weeks, drawing n weeks with
    replacement from the N simulated weeks (plug-in estimate; n = N reproduces the bootstrap)."""
    out = {}
    for tag, x in x_dict.items():
        ref = float(qinv(x))
        rows = []
        for n in ns:
            q = np.array([qinv(x[rng.integers(0, N, n)]) for _ in range(R)])
            rows.append(dict(n=n, median=float(np.median(q)), lo=float(np.percentile(q, 2.5)), hi=float(np.percentile(q, 97.5)),
                             sd=float(q.std(ddof=1)), sd_pct=100 * float(q.std(ddof=1)) / ref,
                             rel_lo=100 * (float(np.percentile(q, 2.5)) / ref - 1), rel_hi=100 * (float(np.percentile(q, 97.5)) / ref - 1),
                             within1=float(np.mean(np.abs(q / ref - 1) < 0.01)), within5=float(np.mean(np.abs(q / ref - 1) < 0.05))))
        out[tag] = dict(ref=ref, rows=rows)
    return out


if __name__ == "__main__":
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    cache = {}
    results = {}
    s = load("base")
    ms = methods(s, SSC)
    results["base"] = boot_case("base", s, "base", 60, ms["proposed"]["eps"], 1.35, rng, cache)
    sb = load("suburban", "results_sub")
    msb = methods(sb, SSC)
    # factor of the proposed candidate
    fsb = msb["proposed"]["C"] / qinv(weekly_cmin(sb, SSC, msb["proposed"]["eps"]))
    print("suburban eps*, factor", msb["proposed"]["eps"], fsb)
    results["suburban"] = boot_case("suburban", sb, "suburban", 40, msb["proposed"]["eps"], round(fsb, 2), rng, cache)
    results["convergence"] = dict(
        base=convergence(dict(eps2=weekly_cmin(s, SSC, 2.0), eps_star=weekly_cmin(s, SSC, ms["proposed"]["eps"])), 60, rng, ns=tuple(range(10, 61, 5))),
        suburban=convergence(dict(eps2=weekly_cmin(sb, SSC, 2.0), eps_star=weekly_cmin(sb, SSC, msb["proposed"]["eps"])), 40, rng,
                             ns=tuple(range(10, 41, 5))))
    results["meta"] = dict(B=B, seed=SEED, runtime_s=time.time() - t0)
    json.dump(results, open(f"{OUT}/ci_results.json", "w"), indent=1)
    print("done", round(time.time() - t0), "s")
