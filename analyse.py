"""Post-processing: design values, optimisation over (C, eps_u), tables."""
import json, sys
import numpy as np
from rpc_sizing.params import RPC, GRID

W = RPC["weeks_per_year"]


def load(case, d="results"):
    with open(f"{d}/{case}.json") as f:
        return json.load(f)


def cost_terms(evals_week_list, idx, w=None):
    """Mean annual cost terms over weeks for candidate idx."""
    w = w or {}
    cc = w.get("cost", RPC["cost_kUSD_per_MVA"])
    pe = w.get("price", RPC["energy_price_USD_MWh"])
    pv = w.get("viol", RPC["viol_price_kUSD_per_pct_h"])
    ev = [wk[idx] for wk in evals_week_list]
    C = ev[0]["C"]
    cap = cc * 2 * C * RPC["crf"]
    loss = pe * np.mean([e["E_loss"] for e in ev]) * W / 1000
    viol = pv * np.mean([e["E_viol"] for e in ev]) * W
    return cap + loss + viol, cap, loss, viol


def metrics(evals_week_list, idx):
    ev = [wk[idx] for wk in evals_week_list]
    return dict(
        C=ev[0]["C"], eps=ev[0]["eps_u"],
        p95_mean=np.mean([e["p95"] for e in ev]),
        comply=np.mean([e["p95"] <= GRID["vuf_lim"] + 1e-6 for e in ev]),
        vmax=np.mean([e["vmax10"] for e in ev]),
        share=np.mean([e["share_above"] for e in ev]),
        Eviol=np.mean([e["E_viol"] for e in ev]) * W,
        Eloss=np.mean([e["E_loss"] for e in ev]) * W,
        Etr=np.mean([e["E_transfer"] for e in ev]) * W,
    )


def methods(summary, Ssc, w=None):
    d = summary["design"][str(Ssc)]
    cands, ev = d["cands"], d["evals"]
    eps_grid = summary["eps_grid"]
    nf = len(summary["c_fact"])
    lim = GRID["vuf_lim"]
    i_conv = eps_grid.index(lim) * nf                     # (eps=lim, C95)
    i_conv_opt = min(range(eps_grid.index(lim) * nf, eps_grid.index(lim) * nf + nf),
                     key=lambda i: cost_terms(ev, i, w)[0])
    i_prop = min(range(len(eps_grid) * nf), key=lambda i: cost_terms(ev, i, w)[0])
    i_peak, i_full = len(cands) - 2, len(cands) - 1
    out = {}
    for name, i in [("full", i_full), ("peak", i_peak), ("p95", i_conv),
                    ("p95_Copt", i_conv_opt), ("proposed", i_prop)]:
        m = metrics(ev, i)
        J = cost_terms(ev, i, w)
        m.update(J=J[0], Jcap=J[1], Jloss=J[2], Jviol=J[3], idx=i)
        out[name] = m
    return out


def weekly_cmin(summary, Ssc, eps):
    i = summary["eps_grid"].index(eps)
    return np.array([wk["cmin"][str(Ssc)][i] for wk in summary["weeks"]])


def ci95(x):
    x = np.asarray(x, float)
    from scipy import stats
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return m, h


if __name__ == "__main__":
    s = load(sys.argv[1] if len(sys.argv) > 1 else "base")
    for Ssc in s["design"]:
        print("Ssc", Ssc)
        for k, v in methods(s, int(Ssc)).items():
            print(f"  {k:9s} C={v['C']:6.2f} eps={v['eps']:.2f} P95={v['p95_mean']:.2f} "
                  f"comply={v['comply']:.2f} vmax={v['vmax']:.2f} Eviol={v['Eviol']:.1f} "
                  f"Eloss={v['Eloss']:.0f} J={v['J']:.0f} ({v['Jcap']:.0f}/{v['Jloss']:.0f}/{v['Jviol']:.0f})")
