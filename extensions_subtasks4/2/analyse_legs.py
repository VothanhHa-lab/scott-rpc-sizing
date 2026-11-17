"""Statistics of the stored per-second leg series (data/legs_w*.npz): Scott leg loading, RPC leg
current, 10-min / 1-h rms, overload durations, episodes. Writes results/*.json, *.csv."""
import sys, os, json, glob
import numpy as np
D = "/home/claude/subtasks4/2/data"; R = "/home/claude/subtasks4/2/results"
os.makedirs(R, exist_ok=True)
THR = [1.0, 1.2, 1.5, 2.0]
C = 11.27; UKV = 27.5
WEEKS = list(range(60))


def runs(b):
    """(count, longest) of consecutive True runs of a boolean array."""
    if not b.any():
        return 0, 0
    d = np.diff(np.concatenate(([0], b.view(np.int8), [0])))
    st = np.flatnonzero(d == 1); en = np.flatnonzero(d == -1)
    return len(st), int((en - st).max())


def roll_rms(x, w):
    c = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2)))
    return np.sqrt((c[w:] - c[:-w]) / w)


def quant(x, q):
    return float(np.quantile(x, q, method="inverted_cdf"))


def leg_stats(x, rating_scale=1.0, nz=None):
    """x: loading in pu of the 40 MVA rating (1 s). rating_scale=2 -> pu of 20 MVA."""
    y = x * rating_scale
    out = dict(max=float(y.max()),
               p95=quant(y, .95), p99=quant(y, .99), p999=quant(y, .999))
    if nz is not None:
        yn = y[nz]
        out.update(p95_nz=quant(yn, .95), p99_nz=quant(yn, .99), p999_nz=quant(yn, .999))
    for t in THR:
        b = y > t
        n, L = runs(b)
        out[f"dur_{t}"] = int(b.sum()); out[f"ep_{t}"] = n; out[f"longest_{t}"] = L
    return out


def week_stats(k):
    d = np.load(f"{D}/legs_w{k:03d}.npz")
    nz = d["S_alpha"] > 0
    nz_b = d["S_beta"] > 0
    r = dict(week=k, n_nonzero=int(nz.sum()))
    for leg in ("alpha", "beta"):
        S = d[f"S_{leg}"]; I = d[f"I_{leg}_pu40"]
        for nm, x in (("S", S / 40.0), ("I", I)):
            for sc, lab in ((1.0, "40"), (2.0, "20")):
                r[f"{leg}_{nm}_{lab}"] = leg_stats(x, sc, nz)
            r[f"{leg}_{nm}_rms10"] = float(roll_rms(x, 600).max())
            r[f"{leg}_{nm}_rms60"] = float(roll_rms(x, 3600).max())
            r[f"{leg}_{nm}_rms10_20"] = 2 * r[f"{leg}_{nm}_rms10"]
            r[f"{leg}_{nm}_rms60_20"] = 2 * r[f"{leg}_{nm}_rms60"]
    # RPC legs (pu of rated C current)
    for leg, key in (("alpha", "I_rpc_alpha_pu"), ("beta", "I_rpc_beta_pu"), ("beta_own", "I_rpc_beta_pu_ownloss")):
        x = d[key]
        r[f"rpc_{leg}"] = dict(max=float(x.max()), p99=quant(x, .99), p999=quant(x, .999),
                                n_gt1=int((x > 1.0).sum()), n_gt1_005=int((x > 1.005).sum()),
                                rms10=float(roll_rms(x, 600).max()), rms60=float(roll_rms(x, 3600).max()))
    r["Ua_min"] = float(d["U_alpha"][nz].min()); r["Ub_min"] = float(d["U_beta"][nz].min())
    r["Ua_p01"] = quant(d["U_alpha"][nz], .01)
    r["vuf_max"] = float(d["vuf"].max())
    # exact VUF P95 of 10-min rms values (cross-check with v7 results)
    v = d["vuf"].astype(np.float64)[:600 * (len(d["vuf"]) // 600)].reshape(-1, 600)
    v10 = np.sqrt((v ** 2).mean(axis=1))
    r["vuf10_p95"] = quant(v10, .95); r["vuf10_max"] = float(v10.max())
    r["peak_SL"] = float(np.hypot(d["P_L"], d["Q_L"]).max())
    r["sx_over_C_max"] = float(d["sx_abs"].max() / C)
    return r


if __name__ == "__main__":
    out = []
    for k in WEEKS:
        out.append(week_stats(k)); print(k, flush=True) if k % 10 == 0 else None
    json.dump(out, open(f"{R}/week_stats.json", "w"))
