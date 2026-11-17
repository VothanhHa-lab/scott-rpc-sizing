"""(c2) Position-dependent catenary impedance, voltage-limited regeneration, representative weeks.
usage: python s5_catenary.py CASE NW [z_ohm_per_km] -> cat_{case}_z{z}.json, data_cat/*.npz"""
import sys, json, time
import numpy as np
from lg import *
from cat import *
from dz import design, evaluate_design
case = sys.argv[1]; NW = int(sys.argv[2]); z = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
tag = f"{case}_z{z:g}"
t0 = time.time()
log = lambda s: print(f"[{tag} {time.time()-t0:.0f}s] {s}", flush=True)
V = {"A_lumped_return": [], "B_lumped_noreturn": [], "C_catenary_return": [], "D_catenary_noreturn": []}
ACC = {k: [] for k in V}
STAT = []
h = 3600.0
for k in range(NW):
    w, lib, p, tt = week(case, k, want_pos=True)
    st = np.load(f"data/{case}_w{k:03d}.npz")
    assert np.abs(w["P"].astype(np.float32) - st["b_P"]).max() == 0.0          # identical to the stored baseline week
    tanphi = w["tanphi"]
    P0, X, act, kmax = build_slots(lib, w["trains"], p["zone_length_m"])
    xs = p["zone_length_m"] / 2000.0
    vv = clip_variants(w["P"], w["Q"], w["Sp"], w["Sn"], tanphi)
    V["A_lumped_return"].append(vv["v7"][:2]); ACC["A_lumped_return"].append(vv["v7"][2])
    V["B_lumped_noreturn"].append(vv["noreturn_onboard"][:2]); ACC["B_lumped_noreturn"].append(vv["noreturn_onboard"][2])
    for nm, nr in (("C_catenary_return", False), ("D_catenary_noreturn", True)):
        r = catenary_week(P0, X, act, kmax, xs, 750.0, tanphi, z=z, no_return=nr)
        Sp = r["Ptrac"]; ret = np.maximum(-r["Psub"], 0.0)
        acc = dict(regen_avail=r["reg_nom"].sum() / h, regen_delivered=r["reg_del"].sum() / h,
                   curtailed=(r["reg_nom"] - r["reg_del"]).sum() / h, returned=ret.sum() / h,
                   absorbed_trains=(r["reg_del"].sum() - ret.sum()) / h, traction=Sp.sum() / h,
                   line_loss=r["loss"].sum() / h, E_sub=np.maximum(r["Psub"], 0).sum() / h,
                   Umax_p99=float(np.nanquantile(r["Umax"][~np.isnan(r["Umax"])], .99)),
                   Umax_max=float(np.nanmax(r["Umax"])), Umin_min=float(np.nanmin(r["Umin"])),
                   Umin_p01=float(np.nanquantile(r["Umin"][~np.isnan(r["Umin"])], .01)),
                   frac_time_Ulim=float(np.mean(((r["reg_nom"] - r["reg_del"]) > 1e-3) & (r["reg_nom"] > 0)) / max(np.mean(r["reg_nom"] > 0), 1e-9)),
                   frac_time_below_19=float(np.nanmean(r["Umin"][~np.isnan(r["Umin"])] < 19.0)),
                   iters_max=int(max(r["iters"])))
        V[nm].append((r["Psub"], r["Qsub"])); ACC[nm].append(acc)
        np.savez_compressed(f"data_cat/{tag}_w{k:03d}_{nm[0]}.npz", P=r["Psub"].astype(np.float32), Q=r["Qsub"].astype(np.float32))
    log(f"week {k}: " + ", ".join(f"{nm[0]}: P95(S)={np.quantile(np.hypot(*V[nm][-1]),.95):.1f}" for nm in V))
acc_sum = {nm: {kk: float(np.mean([a[kk] for a in ACC[nm]])) for kk in ACC[nm][0]} for nm in ACC}
out = dict(case=case, n_weeks=NW, z_ohm_per_km=z, Unom_sub_kV=UNOM_SUB, Umax_kV=UMAX, x_sub_km=xs, accounting_MWh_per_week=acc_sum,
           S_stats={nm: dict(S_p95=float(np.mean([np.quantile(np.hypot(*w_), .95) for w_ in V[nm]])),
                             S_p99=float(np.mean([np.quantile(np.hypot(*w_), .99) for w_ in V[nm]])),
                             S_max=float(np.mean([np.hypot(*w_).max() for w_ in V[nm]]))) for nm in V}, designs={})
json.dump(out, open(f"cat_{tag}.json", "w"))
for nm in V:
    log(f"design {nm}")
    out["designs"][nm] = design(V[nm], Ssc=750.0, log=log)
    json.dump(out, open(f"cat_{tag}.json", "w"))
pv = out["designs"]["A_lumped_return"]["proposed"]
out["transfer"] = {nm: evaluate_design(V[nm], pv["C"], pv["eps"]) for nm in V}
json.dump(out, open(f"cat_{tag}.json", "w"))
log("done")
