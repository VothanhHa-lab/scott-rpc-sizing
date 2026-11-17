"""Code checks (item 4): C=0, |S_L|=0, week->year, units, 10-min alignment, quantile definition, monotonicity."""
import sys, json, warnings
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *
from rpc_sizing import experiment as ex
out = {}
warnings.simplefilter("error", RuntimeWarning)          # any numpy RuntimeWarning (div by zero, invalid) becomes an exception

# ---- 1. C = 0 ----
P, Q = load_week("base", 3)
r = {}
sx, v = rpc.compensate(P, Q, 0.0, 1.0, SSC)
r["compensate_C0_sx_max"] = float(sx.max())
r["compensate_C0_vuf_equals_S_over_Ssc"] = bool(np.allclose(v, np.hypot(P, Q) / SSC * 100))
e0 = rpc.evaluate(P, Q, 0.0, 1.0, SSC)
r["evaluate_C0"] = e0
r["annual_cost_C0"] = rpc.annual_cost(e0)
r["c_min_returns_0_if_unneeded"] = rpc.c_min(P * 0.01, Q * 0.01, 1.0, SSC)
v_ex, sx_ex = vuf_series_exact(P, Q, 0.0, 1.0)
r["exact_C0_matches_exact_uncompensated"] = bool(sx_ex.max() == 0.0)
# negative / tiny C
for Cn in (1e-9, 1e-3):
    s_, v_ = rpc.compensate(P, Q, Cn, 1.0, SSC)
    r[f"compensate_C{Cn}_ok"] = bool(np.all(np.isfinite(v_)) and s_.max() <= 0.96 * Cn + 1e-15)
out["C0"] = r

# ---- 2. |S_L| = 0 ----
r = {}
Z = np.zeros(1000)
sx, v = rpc.compensate(Z, Z, 5.0, 1.0, SSC)
r["compensate_zero_load_vuf_max"] = float(v.max()); r["compensate_zero_load_sx_max"] = float(sx.max())
try:
    vz, sz = vuf_series_exact(Z, Z, 5.0, 1.0)
    r["exact_zero_load_vuf_max"] = float(vz.max())
except Exception as ex_:
    r["exact_all_zero_array_raises"] = repr(ex_)
Z2 = np.zeros(1000); Z2[500] = 10.0
vz2, _ = vuf_series_exact(Z2, np.zeros(1000), 5.0, 1.0)
r["exact_one_nonzero_sample_vuf_zero_elsewhere"] = bool(np.all(vz2[np.arange(1000) != 500] == 0.0) and vz2[500] > 0)
r["evaluate_zero_week"] = rpc.evaluate(np.zeros(604800), np.zeros(604800), 5.0, 1.0, SSC)
r["c_min_zero_week"] = rpc.c_min(np.zeros(604800), np.zeros(604800), 1.0, SSC)
zero_frac, minpos, minU, neg = [], [], [], 0
for k in range(0, 60, 6):
    P, Q = load_week("base", k)
    S = np.hypot(P, Q)
    zero_frac.append(float(np.mean(S == 0))); minpos.append(float(S[S > 0].min()))
    U = rpc.busbar_voltage(P, Q, SSC); minU.append(float(U.min()))
r["fraction_of_samples_S_eq_0_(every 6th base week)"] = [min(zero_frac), max(zero_frac)]
r["smallest_positive_S_MVA"] = min(minpos)
r["min_busbar_voltage_pu_uncompensated"] = min(minU)
# is the exact path's mask (mag>0) the same as vuf = 0 ?  samples with S in (0, 1e-9)
P, Q = load_week("base", 0)
r["n_samples_0<S<1e-6"] = int(np.sum((np.hypot(P, Q) > 0) & (np.hypot(P, Q) < 1e-6)))
out["S0"] = r

# ---- 3. week -> year ----
W1 = 8760.0 / 168.0
Jterms = json.load(open(f"{OUT}/data/repro_approx_base.json"))["prop"]
dJ = (Jterms["Jloss"] + Jterms["Jviol"]) * (W1 / WY - 1)
out["weeks"] = dict(weeks_per_year_code=WY, ratio_8760_over_168=W1, rel_diff=W1 / WY - 1,
                    dJ_prop_kUSD=dJ, calendar_365_25_over_7=365.25 / 7, rel_diff_calendar=365.25 / 7 / WY - 1,
                    dJ_prop_calendar_kUSD=(Jterms["Jloss"] + Jterms["Jviol"]) * (365.25 / 7 / WY - 1),
                    samples_per_week_all=sorted({json.loads(l)["n_samples"] for n in ("base", "cert", "sub") for l in open(f"{OUT}/data/manifest_{n}.jsonl")}),
                    hours_per_week=604800 / 3600)

# ---- 4. units: eps_u in % everywhere ----
r = {}
S0 = 20.0                                   # MVA load, Ssc 750 -> uncompensated VUF 2.667 %
Pt = np.array([S0]); Qt = np.array([0.0])
for eps in (0.02, 2.0):
    sx, v = rpc.compensate(Pt, Qt, 100.0, eps, SSC)
    r[f"VUF_at_eps_u={eps}_unit_test_%"] = float(v[0])
r["note"] = "eps_u=2.0 -> VUF clipped to 2.0 % (percent); eps_u=0.02 would clip to 0.02 %: the code takes PERCENT everywhere"
r["GRID_vuf_lim"] = GRID["vuf_lim"]
r["EPS_GRID_experiment"] = ex.EPS_GRID.tolist()
try:
    rpc.c_min(Pt, Qt, 5.0, SSC)
except ValueError as e:
    r["c_min_raises_if_eps_above_lim"] = str(e)
# exact vs approx unit: exact solver returns percent (x100)
vexact, _ = solve(np.array([S0 + 0j]), np.array([0j]), SSC)
r["exact_VUF_%_uncompensated_20MVA"] = float(vexact[0]); r["approx_VUF_%"] = S0 / SSC * 100
out["units"] = r

# ---- 5. 10-min windows ----
r = {}
x = np.arange(1, 604801, dtype=float)
v10 = rpc.vuf10(x)
r["n_windows_604800"] = int(len(v10))
r["first_window_rms_equals_rms_of_samples_0..599"] = bool(np.isclose(v10[0], np.sqrt(np.mean(x[:600] ** 2))))
r["last_window_rms_equals_rms_of_samples_604200..604799"] = bool(np.isclose(v10[-1], np.sqrt(np.mean(x[-600:] ** 2))))
v_part = rpc.vuf10(np.arange(1, 605001, dtype=float))
r["n_windows_for_605000_samples"] = int(len(v_part))
r["partial_last_block_dropped"] = bool(len(v_part) == 1008)
r["window_start_offsets_s"] = "0, 600, 1200, ... measured from the first sample (t=0 = start of the simulated week, 00:00 of day 1)"
out["window"] = r

# ---- 6. quantile definitions ----
r = {}
rng = np.random.default_rng(1)
y = rng.random(1008)
ys = np.sort(y)
r["inverted_cdf_equals_X_(958)_of_1008"] = bool(rpc.p95(y) == ys[957])
r["linear_between_X_(957)_X_(958)"] = bool(ys[956] <= np.quantile(y, 0.95) <= ys[957])
r["ceil(0.95*1008)"] = int(math.ceil(0.95 * 1008)); r["floor(0.05*1008)_values_allowed_above"] = int(math.floor(0.05 * 1008 + 1e-9))
for N in (40, 60, 90, 120):
    xs = np.sort(rng.random(N))
    r[f"design_quantile_N={N}_is_X_({math.ceil(round(0.95 * N, 9))})"] = bool(q95(xs) == xs[math.ceil(round(0.95 * N, 9)) - 1])
# effect of the within-week quantile definition on compliance counts of the stored designs
RB = json.load(open(f"{OUT}/data/repro_approx_base.json"))
des = {"proposed": (RB["prop"]["eps"], RB["prop"]["C"]), "percentile12": (2.0, RB["p95"]["C"])}
for nm, (e, C) in des.items():
    cnt = {"inverted_cdf": 0, "linear": 0, "higher": 0}; dmax = 0.0
    for k in range(60):
        P, Q = load_week("base", k)
        v10 = rpc.vuf10(rpc.compensate(P, Q, C, e, SSC)[1])
        for m in cnt:
            cnt[m] += int(np.quantile(v10, 0.95, method=m) <= LIM + 1e-9)
        dmax = max(dmax, abs(np.quantile(v10, 0.95, method="linear") - rpc.p95(v10)))
    r[f"weeks_compliant_{nm}_by_quantile_method"] = cnt
    r[f"max|P95_linear-P95_inverted|_{nm}_%"] = dmax
out["quantile"] = r
json.dump(out, open(f"{OUT}/data/checks_a.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
