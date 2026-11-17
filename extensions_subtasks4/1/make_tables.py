"""Summaries from the per-week CSVs -> data/summary.json, reproduction.md, reproduction.tex"""
import sys, json, csv, glob, os
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

def read(tag):
    with open(f"{OUT}/csv/{tag}.csv") as f:
        r = list(csv.DictReader(f))
    return {k: np.array([float(x[k]) for x in r]) for k in r[0]}

def summ(tag):
    d = read(tag)
    n = len(d["week"])
    s = dict(tag=tag, n_weeks=n, C=float(d["C"][0]), eps_u=float(d["eps_u"][0]),
             P95_mean=float(d["P95"].mean()), P95_max=float(d["P95"].max()), P99_mean=float(d["P99"].mean()),
             comply_weeks=int(np.sum(d["P95"] <= LIM + 1e-9)),
             vmax_mean=float(d["vmax10"].mean()), vmax_max=float(d["vmax10"].max()),
             share_mean_pct=float(d["share_gt2_pct"].mean()),
             Eviol_yr=float(d["E_viol"].mean() * WY), Eloss_yr=float(d["E_loss"].mean() * WY),
             Etr_GWh_yr=float(d["E_transfer"].mean() * WY / 1000),
             Jcap=float(d["J_cap"].mean()), Jloss=float(d["J_loss"].mean()), Jviol=float(d["J_viol"].mean()),
             J=float(d["J"].mean()), J_sd_weeks=float(d["J"].std(ddof=1)) if n > 1 else 0.0)
    s["J_check"] = s["Jcap"] + s["Jloss"] + s["Jviol"]
    return s

if __name__ == "__main__":
    tags = sorted(os.path.basename(p)[:-4] for p in glob.glob(f"{OUT}/csv/*.csv") if os.path.basename(p)[:-4] not in ("ALL_designs_long", "SUMMARY_means"))
    S = {t: summ(t) for t in tags}
    json.dump(S, open(f"{OUT}/data/summary.json", "w"), indent=1)
    for t, s in S.items():
        print(f"{t:40s} C={s['C']:8.4f} eps={s['eps_u']:.2f} P95={s['P95_mean']:.3f} comply={s['comply_weeks']}/{s['n_weeks']} "
              f"vmax={s['vmax_mean']:.2f}/{s['vmax_max']:.2f} share={s['share_mean_pct']:.2f} Ev={s['Eviol_yr']:.1f} El={s['Eloss_yr']:.0f} "
              f"Etr={s['Etr_GWh_yr']:.1f} J={s['Jcap']:.0f}/{s['Jloss']:.0f}/{s['Jviol']:.0f}={s['J']:.1f}")

    # ---- combined long CSV and summary CSV ----
    meta = {}
    for fn in ("export_approx", "export_exact", "export_cert"):
        meta.update({k: dict(set=v["set"], model=v["model"]) for k, v in json.load(open(f"{OUT}/data/{fn}.json")).items()})
    cols = ["week", "C", "eps_u", "P95", "P99", "vmax10", "share_gt2_pct", "E_viol", "E_loss", "J_cap", "J_loss", "J_viol", "J", "E_transfer"]
    order = ["hs_approx_proposed", "hs_approx_percentile12", "hs_approx_percentile_Copt", "hs_approx_peak11", "hs_approx_full",
             "hs_exact_proposed", "hs_exact_percentile_corrected", "hs_exact_percentile_corrected_Copt", "hs_exact_of_approx_proposed",
             "hs_exact_of_approx_percentile12", "sub_approx_proposed", "sub_approx_percentile12", "sub_approx_percentile_Copt",
             "cert_exact_proposed", "cert_exact_percentile_corrected"]
    assert set(order) == set(tags), set(order) ^ set(tags)
    with open(f"{OUT}/csv/ALL_designs_long.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "week_set", "model"] + cols)
        for t in order:
            d = read(t)
            for i in range(len(d["week"])):
                w.writerow([t, meta[t]["set"], meta[t]["model"], int(d["week"][i])] + [repr(float(d[c][i])) for c in cols[1:]])
    scols = ["tag", "n_weeks", "C", "eps_u", "comply_weeks", "P95_mean", "P95_max", "P99_mean", "vmax_mean", "vmax_max", "share_mean_pct",
             "Eviol_yr", "Eloss_yr", "Etr_GWh_yr", "Jcap", "Jloss", "Jviol", "J", "J_sd_weeks"]
    with open(f"{OUT}/csv/SUMMARY_means.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "week_set", "model"] + scols[1:])
        for t in order:
            s = S[t]
            w.writerow([t, meta[t]["set"], meta[t]["model"]] + [repr(s[c]) if isinstance(s[c], float) else s[c] for c in scols[1:]])
