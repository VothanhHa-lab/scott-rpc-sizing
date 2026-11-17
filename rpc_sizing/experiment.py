"""Monte Carlo experiments (multi-week ensembles) for RPC sizing.

Design rule used for every method: the design value of the rating is the
95 % quantile, over the simulated weeks, of the weekly minimum rating that
meets P95[VUF_10min] <= eps_lim; i.e. the P95 criterion of EN 50160 is met in
at least 95 % of the simulated weeks. Peak sizing uses the 95 % quantile of
the weekly peak rating (11).
"""
import os
import json
import numpy as np
from multiprocessing import Pool
from .params import TRAIN, SEED0, GRID
from . import train as tr, load as ld, rpc

EPS_GRID = np.round(np.arange(0.0, 2.001, 0.25), 3)
C_FACT = np.array([1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0, 2.5])
N_LIB = 120


def base_params(grade_seed=SEED0):
    p = dict(TRAIN)
    e, g = tr.grade_profile(np.random.default_rng(grade_seed), p["zone_length_m"])
    p["_grade_edges"], p["_grades"] = e, g
    return p


CASES = {
    "base": {},
    "freq_x0.5": dict(freq=0.5),
    "freq_x1.5": dict(freq=1.5),
    "power_x0.75": dict(power=0.75),
    "power_x1.25": dict(power=1.25),
    "no_regen": dict(regen=False),
    "regen_4MW": dict(train=dict(P_reg_el_max_MW=4.0)),
    "speed_250": dict(speed=250.0),
    "speed_350": dict(speed=350.0),
    "stop_0.5": dict(train=dict(p_stop=0.5)),
    "poisson": dict(model="poisson"),
    "segments_prev": dict(model="segments"),
    "diode": dict(regen=False, pf=0.77),
    "grade_alt": dict(grade_seed=SEED0 + 7),
    # second case study: 25 kV suburban/regional line, all trains stop
    "suburban": dict(
        train=dict(mass_t=300.0, F_max_kN=250.0, P_wheel_max_MW=4.5,
                   P_reg_wheel_max_MW=5.0, P_reg_el_max_MW=4.5,
                   davis_A=2.5, davis_B=0.025, davis_C=0.0006, P_aux_MW=0.15,
                   b_service=0.8, v_line_kmh=160.0, zone_length_m=40000.0,
                   stations_x_m=[2000.0 + 4000.0 * i for i in range(10)],
                   station_x_m=2000.0, p_stop=1.0, dwell_s=(30.0, 60.0),
                   p_restriction=0.05, coast_lookahead_m=1000.0),
        tt=dict(t_start_h=5.0, n_peak=12, n_off=6, delay_mean_s=90.0,
                delay_max_s=600.0)),
}


def week_case(case, k, seed_base):
    """Generate week k of a case; returns P, Q (float64)."""
    cfg = CASES[case]
    p = dict(TRAIN)
    p.update(cfg.get("train", {}))
    eg, gg = tr.grade_profile(np.random.default_rng(cfg.get("grade_seed", SEED0)),
                              p["zone_length_m"])
    p["_grade_edges"], p["_grades"] = eg, gg
    rng = np.random.default_rng(seed_base + k)
    if cfg.get("model") == "segments":
        return ld.week_load_segments(rng, pf=cfg.get("pf", TRAIN["pf"]))
    lib = tr.build_library(p, rng, N_LIB, regen=cfg.get("regen", True),
                           speed_kmh=cfg.get("speed"))
    return ld.week_load_pq(rng, lib, model=cfg.get("model", "timetable"),
                           freq_factor=cfg.get("freq", 1.0),
                           pf=cfg.get("pf"), power_scale=cfg.get("power", 1.0),
                           tt=cfg.get("tt"))


def seed_of(case):
    return SEED0 + 1000 * (list(CASES).index(case) + 1)


def pass1(args):
    case, k, Ssc_list, store = args
    if store and os.path.exists(store % k):
        d = np.load(store % k)
        P, Q = d["P"].astype(float), d["Q"].astype(float)
        store = None
    else:
        P, Q = week_case(case, k, seed_of(case))
    if store:
        np.savez_compressed(store % k, P=P.astype(np.float32),
                            Q=Q.astype(np.float32))
    S = np.hypot(P, Q)
    out = dict(k=k, peakS=float(S.max()), meanP=float(P.mean()),
               minP=float(P.min()), regen_share=float(np.mean(P < 0)),
               cmin={})
    for Ssc in Ssc_list:
        out["cmin"][str(Ssc)] = [rpc.c_min(P, Q, e, Ssc) for e in EPS_GRID]
        out.setdefault("p95_unc", {})[str(Ssc)] = rpc.p95(rpc.vuf10(S / Ssc * 100))
    return out


def pass2(args):
    case, k, Ssc, cands, store, weekgen = args
    if store and os.path.exists(store % k):
        d = np.load(store % k)
        P, Q = d["P"].astype(float), d["Q"].astype(float)
    else:
        P, Q = week_case(case, k, seed_of(case))
    res = []
    for (e, C) in cands:
        ev = rpc.evaluate(P, Q, C, e, Ssc)
        res.append(ev)
    return res


def run_case(case, n_weeks, Ssc_list, outdir, procs=2, store=False):
    os.makedirs(outdir, exist_ok=True)
    st = os.path.join(outdir, f"{case}_w%03d.npz") if store else None
    with Pool(procs) as pool:
        r1 = pool.map(pass1, [(case, k, Ssc_list, st) for k in range(n_weeks)])
    summary = dict(case=case, n_weeks=n_weeks, eps_grid=EPS_GRID.tolist(),
                   c_fact=C_FACT.tolist(), weeks=r1, design={})
    for Ssc in Ssc_list:
        cm = np.array([w["cmin"][str(Ssc)] for w in r1])     # weeks x eps
        cdes = np.nanquantile(cm, 0.95, axis=0, method="inverted_cdf")
        peaks = np.array([max(0.0, w["peakS"] - GRID["vuf_lim"] / 100 * Ssc) / 2
                          for w in r1])
        fulls = np.array([w["peakS"] / 2 for w in r1])
        c_peak = float(np.quantile(peaks, 0.95, method="inverted_cdf"))
        c_full = float(np.quantile(fulls, 0.95, method="inverted_cdf"))
        cands = []
        for i, e in enumerate(EPS_GRID):
            for f in C_FACT:
                cands.append((float(e), float(cdes[i] * f)))
        cands.append((GRID["vuf_lim"], c_peak))
        cands.append((0.0, c_full))
        with Pool(procs) as pool:
            r2 = pool.map(pass2, [(case, k, Ssc, cands, st, True)
                                  for k in range(n_weeks)])
        summary["design"][str(Ssc)] = dict(c_design=cdes.tolist(),
                                           c_peak=c_peak, c_full=c_full,
                                           cands=cands, evals=r2)
    with open(os.path.join(outdir, f"{case}.json"), "w") as f:
        json.dump(summary, f)
    return summary
