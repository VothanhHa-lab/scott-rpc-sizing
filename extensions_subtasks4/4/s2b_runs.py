"""(a) Run-level statistics from one library: stop/non-stop durations, inter-station moving times, energy per km."""
import sys, json
import numpy as np
from lg import *
case = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 0
cfg, p, tt = case_setup(case)
rng = np.random.default_rng(ex.seed_of(case) + k)
lib = build_library_d(p, rng, N_LIB, regen=cfg.get("regen", True), speed_kmh=cfg.get("speed"))
L = p["zone_length_m"] / 1000
rows = []; inter = []; dwell = []
for d in range(2):
    for P, x in lib[d]:
        dx = np.diff(x, prepend=x[0])
        st = (np.abs(dx) < 1e-9) & (x > 1.0) & (x < p["zone_length_m"] - 1.0)       # standing in the zone
        # dwell periods = runs of st
        idx = np.where(st)[0]
        periods = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1) if len(idx) else []
        periods = [q for q in periods if len(q) >= 10]
        dwell += [len(q) for q in periods]
        edges = [0] + [v for q in periods for v in (q[0], q[-1])] + [len(P)]
        for a in range(0, len(edges) - 1, 2):
            seg = (edges[a], edges[a + 1])
            if len(periods) and 0 < a < len(edges) - 2 and seg[1] > seg[0]:
                inter.append(seg[1] - seg[0])               # moving time between two dwell periods
        rows.append((len(P), len(periods), np.maximum(P, 0).sum() / 3.6, (-np.minimum(P, 0)).sum() / 3.6,
                     np.sum(P > 0.5 * p_el_max(p))))
rows = np.array(rows)
out = dict(case=case, week=k, n_runs=len(rows), L_km=L,
           dur_s_nonstop=float(rows[rows[:, 1] == 0, 0].mean()) if (rows[:, 1] == 0).any() else None,
           dur_s_stop=float(rows[rows[:, 1] > 0, 0].mean()) if (rows[:, 1] > 0).any() else None,
           share_stop=float((rows[:, 1] > 0).mean()), n_dwell_mean=float(rows[:, 1].mean()),
           dwell_s_mean=float(np.mean(dwell)) if dwell else None,
           interstation_move_s=dict(mean=float(np.mean(inter)), p5=float(np.quantile(inter, .05)), p95=float(np.quantile(inter, .95)), n=len(inter)) if inter else None,
           gross_kWh_per_km=float((rows[:, 2] / L).mean()), regen_kWh_per_km=float((rows[:, 3] / L).mean()),
           net_kWh_per_km=float(((rows[:, 2] - rows[:, 3]) / L).mean()),
           gross_kWh_per_km_nonstop=float((rows[rows[:, 1] == 0, 2] / L).mean()) if (rows[:, 1] == 0).any() else None,
           accel_s_per_run=float(rows[:, 4].mean()),
           Pel_max_MW=p_el_max(p))
json.dump(out, open(f"runs_{case}.json", "w"), indent=1)
print(json.dumps(out, indent=1))
