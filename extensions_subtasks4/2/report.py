"""Pooled (60-week) statistics + per-week CSV + summary JSON used by NOTES/LaTeX."""
import json, csv, numpy as np
D = "/home/claude/subtasks4/2/data"; R = "/home/claude/subtasks4/2/results"
THR = [1.0, 1.2, 1.3, 1.5, 2.0]
NW = 60; N = 604800


def runs(b):
    if not b.any(): return 0, 0
    d = np.diff(np.concatenate(([0], b.view(np.int8), [0])))
    st = np.flatnonzero(d == 1); en = np.flatnonzero(d == -1)
    return len(st), int((en - st).max())


def roll_rms(x, w):
    c = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2)))
    return np.sqrt((c[w:] - c[:-w]) / w)


def q(x, p): return float(np.quantile(x, p, method="inverted_cdf"))


series = {"alpha_S": [], "alpha_I": [], "beta_S": [], "beta_I": [], "rpc_a": [], "rpc_b": [], "rpc_bo": [], "Ua": []}
cnt = {}
rms = {}
for k in range(NW):
    z = np.load(f"{D}/legs_w{k:03d}.npz")
    series["alpha_S"].append(z["S_alpha"] / 40.0); series["alpha_I"].append(z["I_alpha_pu40"])
    series["beta_S"].append(z["S_beta"] / 40.0); series["beta_I"].append(z["I_beta_pu40"])
    series["rpc_a"].append(z["I_rpc_alpha_pu"]); series["rpc_b"].append(z["I_rpc_beta_pu"]); series["rpc_bo"].append(z["I_rpc_beta_pu_ownloss"])
    series["Ua"].append(z["U_alpha"])
    for nm in ("alpha_S", "alpha_I", "beta_S", "beta_I"):
        x = series[nm][-1]
        for t in THR:
            for sc, lab in ((1.0, "40"), (2.0, "20")):
                n, L = runs(x * sc > t)
                a = cnt.setdefault((nm, lab, t), [0, 0, 0]); a[0] += int((x * sc > t).sum()); a[1] += n; a[2] = max(a[2], L)
        r10 = roll_rms(x, 600).max(); r60 = roll_rms(x, 3600).max()
        rms.setdefault(nm, []).append((float(r10), float(r60)))
    for nm in ("rpc_a", "rpc_b", "rpc_bo"):
        x = series[nm][-1]
        for t in (1.0, 1.01, 1.02):
            n, L = runs(x > t); a = cnt.setdefault((nm, "C", t), [0, 0, 0]); a[0] += int((x > t).sum()); a[1] += n; a[2] = max(a[2], L)
        r10 = roll_rms(x, 600).max(); r60 = roll_rms(x, 3600).max()
        rms.setdefault(nm, []).append((float(r10), float(r60)))
pool = {k: np.concatenate(v) for k, v in series.items()}
tot = NW * N
out = {"n_seconds": tot, "n_weeks": NW}
for nm in ("alpha_S", "alpha_I", "beta_S", "beta_I"):
    x = pool[nm]; nzm = pool["alpha_S" if nm.startswith("alpha") else "beta_S"] > 0
    for sc, lab in ((1.0, "40"), (2.0, "20")):
        y = x * sc
        e = dict(max=float(y.max()), p95=q(y, .95), p99=q(y, .99), p999=q(y, .999),
                 p95_nz=q(y[nzm], .95), p99_nz=q(y[nzm], .99), p999_nz=q(y[nzm], .999), n_nonzero=int(nzm.sum()),
                 rms10_max=sc * max(a[0] for a in rms[nm]), rms60_max=sc * max(a[1] for a in rms[nm]),
                 rms10_week_p95=sc * q(np.array([a[0] for a in rms[nm]]), .95), rms60_week_p95=sc * q(np.array([a[1] for a in rms[nm]]), .95))
        for t in THR:
            d_, n_, L_ = cnt[(nm, lab, t)]
            e[f"thr{t}"] = dict(seconds=d_, hours=d_ / 3600, hours_per_week=d_ / 3600 / NW, share_pct=100 * d_ / tot, episodes=n_,
                                episodes_per_week=n_ / NW, longest_s=L_)
        out[f"{nm}_{lab}"] = e
for nm in ("rpc_a", "rpc_b", "rpc_bo"):
    x = pool[nm]
    e = dict(max=float(x.max()), p99=q(x, .99), p999=q(x, .999), rms10_max=max(a[0] for a in rms[nm]), rms60_max=max(a[1] for a in rms[nm]))
    for t in (1.0, 1.01, 1.02):
        d_, n_, L_ = cnt[(nm, "C", t)]; e[f"gt{t}"] = dict(seconds=d_, episodes=n_, longest_s=L_)
    out[nm] = e
Ua = pool["Ua"]; out["Ua_min"] = float(Ua[Ua > 0].min()); out["Ua_p001"] = q(Ua[Ua > 0], .001)
json.dump(out, open(f"{R}/pooled_summary.json", "w"), indent=1)

# per-week CSV
w = json.load(open(f"{R}/week_stats.json"))
with open(f"{R}/week_table.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["week", "peak_SL_MVA", "Sa_max_MVA", "Sa_max_pu40", "Ia_max_pu40", "Ia_P99_pu40", "Ia_P999_pu40", "s_gt1.0_S40", "ep_gt1.0_S40",
                 "longest_gt1.0_S40_s", "s_gt1.0_I40", "ep_gt1.0_I40", "longest_gt1.0_I40_s", "s_gt1.2_I40", "s_gt1.5_I40",
                 "rms10_max_I_pu40", "rms60_max_I_pu40", "rpcA_max_pu", "rpcA_s_gt1", "rpcB_max_pu", "Ua_min", "Ub_min", "vuf10_p95", "vuf10_max"])
    for x in w:
        a = x["alpha_S_40"]; b = x["alpha_I_40"]
        wr.writerow([x["week"], round(x["peak_SL"], 2), round(a["max"] * 40, 2), round(a["max"], 4), round(b["max"], 4), round(b["p99"], 4), round(b["p999"], 4),
                     a["dur_1.0"], a["ep_1.0"], a["longest_1.0"], b["dur_1.0"], b["ep_1.0"], b["longest_1.0"], b["dur_1.2"], b["dur_1.5"],
                     round(x["alpha_I_rms10"], 4), round(x["alpha_I_rms60"], 4), round(x["rpc_alpha"]["max"], 4), x["rpc_alpha"]["n_gt1"],
                     round(x["rpc_beta"]["max"], 4), round(x["Ua_min"], 4), round(x["Ub_min"], 4), round(x["vuf10_p95"], 4), round(x["vuf10_max"], 4)])
print(json.dumps({k: out[k] for k in ("alpha_S_40", "alpha_I_40")}, indent=1)[:3500])
