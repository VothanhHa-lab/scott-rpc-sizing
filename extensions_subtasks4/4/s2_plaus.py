"""(a) Simulated statistics of the stored planning scenarios (no measured data).
Reads data/{case}_wNNN.npz (baseline b_*, correlated c_*), writes plaus_{case}.json."""
import sys, json, glob
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing.params import TRAIN, TIMETABLE
from rpc_sizing import experiment as ex
case = sys.argv[1]
cfg = ex.CASES[case]
tt = dict(TIMETABLE, **cfg.get("tt", {}))
p = dict(TRAIN); p.update(cfg.get("train", {}))
files = sorted(glob.glob(f"data/{case}_w*.npz"))
h0 = int(tt["t_start_h"])
N = 7 * 24 * 3600
tod = (np.arange(N) // 3600) % 24
op = tod >= h0                                     # operating hours of the timetable (entries; trains still run after 24 h)
res = {}
for sc in ("b", "c"):
    rows = []
    for fn in files:
        d = np.load(fn)
        P = d[f"{sc}_P"].astype(float); Q = d[f"{sc}_Q"].astype(float); S = np.hypot(P, Q)
        nz = d[f"{sc}_nz"].astype(int); na = d[f"{sc}_na"].astype(int); nh = d[f"{sc}_nh"].astype(int)
        m = nz > 0                                  # seconds with at least one train in the zone
        P15 = np.convolve(P, np.ones(900) / 900, mode="valid")[::60]
        r = dict(P_mean=P.mean(), P_mean_op=P[op].mean(), P_p95=np.quantile(P[op], .95), P_p99=np.quantile(P[op], .99),
                 P_max=P.max(), P_min=P.min(), S_p95=np.quantile(S[op], .95), S_p99=np.quantile(S[op], .99), S_max=S.max(),
                 P15_max=P15.max(), E_MWh=P.clip(0).sum() / 3600, Eregen_MWh=(-P).clip(0).sum() / 3600,
                 Ep_gross=d[f"{sc}_Sp"].astype(float).sum() / 3600, En_gross=d[f"{sc}_Sn"].astype(float).sum() / 3600,
                 nz_mean_op=nz[op].mean(), nz_p95=np.quantile(nz[op], .95), nz_p99=np.quantile(nz[op], .99), nz_max=nz.max(),
                 na_mean_op=na[op].mean(), na_p95=np.quantile(na[op], .95), na_p99=np.quantile(na[op], .99), na_max=na.max(),
                 nh_mean_op=nh[op].mean(), nh_p95=np.quantile(nh[op], .95), nh_p99=np.quantile(nh[op], .99), nh_max=nh.max(),
                 frac_nh_ge1=float((nh[op] >= 1).mean()), frac_nh_ge2=float((nh[op] >= 2).mean()), frac_nh_ge3=float((nh[op] >= 3).mean()),
                 frac_na_ge2=float((na[op] >= 2).mean()), frac_na_ge3=float((na[op] >= 3).mean()), frac_na_ge4=float((na[op] >= 4).mean()),
                 frac_nz_ge3=float((nz[op] >= 3).mean()), frac_nz_ge5=float((nz[op] >= 5).mean()),
                 frac_Pneg=float((P[op] < 0).mean()))
        rows.append(r)
    keys = rows[0].keys()
    res[sc] = {k: dict(mean=float(np.mean([r[k] for r in rows])), min=float(np.min([r[k] for r in rows])),
                       max=float(np.max([r[k] for r in rows]))) for k in keys}
    res[sc]["n_weeks"] = len(rows)
# library statistics (per run)
ls = np.vstack([np.load(fn)["libstat"] for fn in files[:min(10, len(files))]])
L = p["zone_length_m"] / 1000
res["lib"] = dict(n_runs=int(len(ls)), dur_s=dict(mean=float(ls[:, 0].mean()), p5=float(np.quantile(ls[:, 0], .05)), p95=float(np.quantile(ls[:, 0], .95))),
                  gross_kWh_per_km=dict(mean=float((ls[:, 1] / L).mean()), p5=float(np.quantile(ls[:, 1] / L, .05)), p95=float(np.quantile(ls[:, 1] / L, .95))),
                  regen_kWh_per_km=dict(mean=float((ls[:, 2] / L).mean())),
                  net_kWh_per_km=dict(mean=float(((ls[:, 1] - ls[:, 2]) / L).mean())),
                  v_avg_kmh=dict(mean=float(ls[:, 3].mean()), p5=float(np.quantile(ls[:, 3], .05)), p95=float(np.quantile(ls[:, 3], .95))),
                  P_el_max_MW=p["P_wheel_max_MW"] / p["eta_t"] + p["P_aux_MW"])
json.dump(res, open(f"plaus_{case}.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:3500])
