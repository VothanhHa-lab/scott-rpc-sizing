"""Load generator for sub-task 4.4 (copy/extension of /home/claude/code/rpc_sizing/{load,experiment,train}.py;
the originals are NOT modified, they are imported read-only).

Differences with respect to the original week generator:
  * the train library is built with per-second positions (details=True);
  * a week is synthesised with exactly the same random-number consumption as load.week_load_pq
    (library first, then for every direction entry_times() and the run draws), so that with
    episodes=None the output is identical to the stored weeks (checked in check_repro());
  * optional correlated delay episodes (train bunching), drawn from a SEPARATE random stream so that the
    library, the independent delays and the run assignment are unchanged;
  * the weekly record also gives the positive part S+ and the negative part S- of the train powers,
    the number of trains in the zone and the number of accelerating trains.
"""
import sys
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing import train as tr, load as ld, experiment as ex
from rpc_sizing.params import TRAIN, TIMETABLE, SEED0

N_LIB = ex.N_LIB
SEC_WEEK = 7 * 24 * 3600


def case_setup(case):
    cfg = ex.CASES[case]
    p = dict(TRAIN)
    p.update(cfg.get("train", {}))
    eg, gg = tr.grade_profile(np.random.default_rng(cfg.get("grade_seed", SEED0)), p["zone_length_m"])
    p["_grade_edges"], p["_grades"] = eg, gg
    tt = dict(TIMETABLE, **cfg.get("tt", {}))
    return cfg, p, tt


def p_el_max(p):
    """Maximum electrical traction power of one train (MW)."""
    return p["P_wheel_max_MW"] / p["eta_t"] + p["P_aux_MW"]


def build_library_d(p, rng, n_per_dir, regen=True, speed_kmh=None):
    """Same random draws as train.build_library; returns lib[d] = list of (P_el, x_along_run_m)."""
    pp = dict(p)
    if speed_kmh is not None:
        pp["v_line_kmh"] = speed_kmh
    edges, grades = p["_grade_edges"], p["_grades"]
    L = p["zone_length_m"]
    edges_r = (L - edges[::-1])
    grades_r = -grades[::-1]
    lib = []
    for d, (e, g) in enumerate([(edges, grades), (edges_r, grades_r)]):
        runs = []
        for _ in range(n_per_dir):
            stop = rng.random() < p["p_stop"]
            restr = None
            if rng.random() < p["p_restriction"]:
                x1 = rng.uniform(3000.0, L - 8000.0)
                x2 = x1 + rng.uniform(*p["restriction_len_m"])
                restr = (x1, x2, rng.uniform(*p["restriction_v_kmh"]) / 3.6)
            mf = rng.uniform(*p["mass_factor"])
            P, lg = tr.run_train(pp, rng, e, g, stop, restr, mf, regen=regen, details=True)
            runs.append((P, lg[:, 0].copy()))
        lib.append(runs)
    return lib


# ---------------------------------------------------------------- delay episodes
EPISODE = dict(rate_min=1, rate_max=3, lam=2.0,        # episodes per day: Poisson(2) clipped to 1..3
               D_min_s=300.0, D_max_s=1200.0,          # shared delay of the first train 5..20 min
               M_min=3, M_max=8,                       # number of consecutive trains affected
               hmin_s=180.0)                            # minimum headway kept by the dispatcher (3 min)


def draw_episodes(epr, tt, ep=EPISODE):
    """List of dicts (day, t0_s, dir, D_s, M). Direction: one of the two tracks (a blocking incident)."""
    out = []
    for day in range(tt["days"]):
        n = int(np.clip(epr.poisson(ep["lam"]), ep["rate_min"], ep["rate_max"]))
        for _ in range(n):
            h0 = tt["t_start_h"] + epr.uniform(0.0, tt["t_end_h"] - tt["t_start_h"])
            out.append(dict(t0=(day * 24 + h0) * 3600.0, dir=int(epr.integers(2)),
                            D=epr.uniform(ep["D_min_s"], ep["D_max_s"]),
                            M=int(epr.integers(ep["M_min"], ep["M_max"] + 1))))
    return out


def apply_episodes(te, eps_dir, ep=EPISODE):
    """te: entry times (sorted, baseline) of one direction; returns modified entry times with the same
    train identities.  Train j of an episode (j = 0..M-1) gets the extra delay D (1 - j/M) (linear catch-up);
    the dispatcher keeps a minimum headway hmin to the preceding (already shifted) train."""
    te2 = te.copy()
    for e in sorted(eps_dir, key=lambda z: z["t0"]):
        i0 = int(np.searchsorted(te, e["t0"]))
        for j in range(e["M"]):
            i = i0 + j
            if i >= len(te2):
                break
            te2[i] = te2[i] + e["D"] * (1.0 - j / e["M"])
            if i > 0:
                te2[i] = max(te2[i], te2[i - 1] + ep["hmin_s"])
    return te2


# ---------------------------------------------------------------- week synthesis
def synth(rng, lib, tt, p, pf=None, epr=None, ep=EPISODE, want_pos=False):
    """Weekly record.  With epr=None the entry times are the baseline (independent delays) ones."""
    pf = TRAIN["pf"] if pf is None else pf
    tanphi = np.tan(np.arccos(pf))
    N = SEC_WEEK
    P = np.zeros(N); Q = np.zeros(N); Sp = np.zeros(N); Sn = np.zeros(N)
    nz = np.zeros(N, np.int16); na = np.zeros(N, np.int16); nh = np.zeros(N, np.int16)
    thr = 0.5 * p_el_max(p)
    thr9 = 0.9 * p_el_max(p)
    episodes = draw_episodes(epr, tt, ep) if epr is not None else []
    trains = []                                  # (dir, i0, run index) for position-dependent post-processing
    for d in range(2):
        te = ld.entry_times(rng, tt, "timetable", 1.0)
        idx = [int(rng.integers(len(lib[d]))) for _ in te]          # same draws as the original loop
        if episodes:
            te = apply_episodes(te, [e for e in episodes if e["dir"] == d], ep)
        for t, ri in zip(te, idx):
            run = lib[d][ri][0]
            i0 = int(t)
            if i0 >= N:
                continue
            i1 = min(i0 + len(run), N)
            seg = run[: i1 - i0]
            P[i0:i1] += seg
            Q[i0:i1] += tanphi * np.abs(seg)
            Sp[i0:i1] += np.maximum(seg, 0.0)
            Sn[i0:i1] += np.maximum(-seg, 0.0)
            nz[i0:i1] += 1
            na[i0:i1] += (seg > thr)
            nh[i0:i1] += (seg > thr9)
            if want_pos:
                trains.append((d, i0, ri))
    out = dict(P=P, Q=Q, Sp=Sp, Sn=Sn, nz=nz, na=na, nh=nh, tanphi=tanphi)
    if want_pos:
        out["trains"] = trains
        out["episodes"] = episodes
    return out


def week(case, k, correlated=False, want_pos=False, seed_ep_offset=7_000_000):
    """Generate week k of `case` (same seed rule as experiment.seed_of) -> dict, plus library."""
    cfg, p, tt = case_setup(case)
    seed = ex.seed_of(case)
    rng = np.random.default_rng(seed + k)
    lib = build_library_d(p, rng, N_LIB, regen=cfg.get("regen", True), speed_kmh=cfg.get("speed"))
    epr = np.random.default_rng(seed + seed_ep_offset + k) if correlated else None
    out = synth(rng, lib, tt, p, pf=cfg.get("pf"), epr=epr, want_pos=want_pos)
    return out, lib, p, tt


def week_both(case, k):
    """Baseline and correlated week from ONE library (same rng stream) -> (base, corr, lib, p, tt)."""
    cfg, p, tt = case_setup(case)
    seed = ex.seed_of(case)
    rng = np.random.default_rng(seed + k)
    lib = build_library_d(p, rng, N_LIB, regen=cfg.get("regen", True), speed_kmh=cfg.get("speed"))
    st = rng.bit_generator.state                      # state after the library
    base = synth(rng, lib, tt, p, pf=cfg.get("pf"))
    rng.bit_generator.state = st                      # identical entry times / run draws for the correlated week
    epr = np.random.default_rng(seed + 7_000_000 + k)
    corr = synth(rng, lib, tt, p, pf=cfg.get("pf"), epr=epr)
    return base, corr, lib, p, tt


def library_stats(lib, p):
    """Per-run statistics of the library: duration (s), energy drawn (kWh), net energy (kWh), mean speed."""
    L = p["zone_length_m"] / 1000.0
    rows = []
    for d in range(2):
        for P, x in lib[d]:
            ep_ = np.maximum(P, 0).sum() / 3600.0 * 1000.0
            en = (-np.minimum(P, 0)).sum() / 3600.0 * 1000.0
            rows.append((len(P), ep_, en, L / len(P) * 3600.0))
    return np.array(rows)


def check_repro(case="base", k=0):
    base, corr, lib, p, tt = week_both(case, k)
    d = {"base": "results", "suburban": "results_sub"}[case]
    st = np.load(f"/home/claude/code/{d}/{case}_w{k:03d}.npz")
    return (float(np.abs(base["P"].astype(np.float32) - st["P"]).max()),
            float(np.abs(base["Q"].astype(np.float32) - st["Q"]).max()),
            float(np.abs(corr["P"] - base["P"]).max()))


if __name__ == "__main__":
    import time
    for c in ("base", "suburban"):
        t = time.time()
        print(c, check_repro(c, 0), round(time.time() - t, 1), "s", flush=True)
