"""(c) instants of the 65.8 MVA weekly-peak quantile; (d) candidate EMT operating points.
Reads data/legs_w*.npz. Writes results/peak_instants.csv, results/candidates.json/csv, results/candidate_traces.npz."""
import json, csv, numpy as np
D = "/home/claude/subtasks4/2/data"; R = "/home/claude/subtasks4/2/results"
C = 11.27
FIELDS = ["P_L", "Q_L", "P_alpha", "Q_alpha", "P_beta", "Q_beta", "U_alpha", "U_beta", "S_alpha", "S_beta", "I_alpha_pu40",
          "I_beta_pu40", "I_rpc_alpha_pu", "I_rpc_beta_pu", "sx_abs", "vuf"]


def hms(s):
    d, r = divmod(int(s), 86400)
    return f"day {d+1} {r//3600:02d}:{(r%3600)//60:02d}:{r%60:02d}"


def snap(d, k, i):
    r = dict(week=k, t_s=int(i), clock=hms(i))
    for f in FIELDS:
        r[f] = round(float(d[f][i]), 4)
    r["S_L"] = round(float(np.hypot(d["P_L"][i], d["Q_L"][i])), 3)
    r["sx_over_C"] = round(float(d["sx_abs"][i]) / C, 4)
    return r


def longest_run(b):
    if not b.any(): return 0, 0
    dd = np.diff(np.concatenate(([0], b.view(np.int8), [0])))
    st = np.flatnonzero(dd == 1); en = np.flatnonzero(dd == -1)
    j = int(np.argmax(en - st)); return int(st[j]), int(en[j])


W = {}
# ------------------------------------------------ pass over weeks
peak_rows = []
cand = {"sustained_sx": [], "low_U_near_sat": [], "reversal_5s": [], "reversal_10s": [], "step_up_1s": [], "step_down_1s": [],
        "max_alpha_rpc_current": [], "max_alpha_scott": [], "max_alpha_scott_I": []}
traces = {}
for k in range(60):
    d = {f: np.load(f"{D}/legs_w{k:03d}.npz")[f] for f in FIELDS}
    P = d["P_L"].astype(float); Q = d["Q_L"].astype(float)
    SL = np.hypot(P, Q)
    ip = int(np.argmax(SL))
    r = snap(d, k, ip); peak_rows.append(r)
    x = d["sx_abs"] / C
    # 1. sustained transfer: longest run x >= 0.9 and best 300-s mean
    a, b = longest_run(x >= 0.90)
    cs = np.concatenate(([0.0], np.cumsum(x.astype(float))))
    m300 = (cs[300:] - cs[:-300]) / 300.0
    j = int(np.argmax(m300))
    cand["sustained_sx"].append(dict(week=k, run090_start=a, run090_len=b - a, run090_clock=hms(a), best300_start=j,
                                     best300_mean=float(m300[j]), best300_clock=hms(j), snap_mid=snap(d, k, j + 150)))
    # 2. low busbar voltage with x >= 0.9
    sat = x >= 0.90
    if sat.any():
        Ua = np.where(sat, d["U_alpha"], 9.0); i2 = int(np.argmin(Ua)); cand["low_U_near_sat"].append(snap(d, k, i2))
    # alpha RPC current max, alpha scott max
    i3 = int(np.argmax(d["I_rpc_alpha_pu"])); cand["max_alpha_rpc_current"].append(snap(d, k, i3))
    cand["max_alpha_scott"].append(snap(d, k, int(np.argmax(d["S_alpha"]))))
    cand["max_alpha_scott_I"].append(snap(d, k, int(np.argmax(d["I_alpha_pu40"]))))
    # 3. reversals: traction (P>0) -> regeneration (P<0)
    for dt, key in ((5, "reversal_5s"), (10, "reversal_10s")):
        sw = P[dt:] - P[:-dt]
        ok = (P[:-dt] > 2.0) & (P[dt:] < -2.0)
        if ok.any():
            sw2 = np.where(ok, sw, 0.0); i4 = int(np.argmin(sw2))
            e = snap(d, k, i4); e.update(dt=dt, swing_MW=round(float(sw2[i4]), 3), P_end=round(float(P[i4 + dt]), 3), clock_end=hms(i4 + dt))
            cand[key].append(e)
    # 4. 1-s steps
    dP = np.diff(P)
    iu = int(np.argmax(dP)); idn = int(np.argmin(dP))
    e = snap(d, k, iu); e.update(dP_MW=round(float(dP[iu]), 3), P_next=round(float(P[iu + 1]), 3)); cand["step_up_1s"].append(e)
    e = snap(d, k, idn); e.update(dP_MW=round(float(dP[idn]), 3), P_next=round(float(P[idn + 1]), 3)); cand["step_down_1s"].append(e)
    W[k] = d if k in () else None
    if k % 10 == 0: print(k, flush=True)

# ------------------------------------------------ peak instants CSV
with open(f"{R}/peak_instants.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(peak_rows[0].keys())); wr.writeheader(); wr.writerows(peak_rows)

# ------------------------------------------------ select the top candidates
sel = {}
def top(lst, key, n=3, rev=True, distinct=True):
    s = sorted(lst, key=key, reverse=rev); out = []; seen = set()
    for e in s:
        if distinct and e["week"] in seen: continue
        seen.add(e["week"]); out.append(e)
        if len(out) == n: break
    return out
sel["sustained_sx_by_run090"] = top(cand["sustained_sx"], lambda e: e["run090_len"])
sel["sustained_sx_by_300s_mean"] = top(cand["sustained_sx"], lambda e: e["best300_mean"])
sel["lowest_Ua_near_saturation"] = top(cand["low_U_near_sat"], lambda e: e["U_alpha"], rev=False)
sel["highest_alpha_rpc_current"] = top(cand["max_alpha_rpc_current"], lambda e: e["I_rpc_alpha_pu"])
sel["highest_alpha_scott_S"] = top(cand["max_alpha_scott"], lambda e: e["S_alpha"])
sel["highest_alpha_scott_I"] = top(cand["max_alpha_scott_I"], lambda e: e["I_alpha_pu40"])
sel["reversal_5s"] = top(cand["reversal_5s"], lambda e: -e["swing_MW"], distinct=False)
sel["reversal_10s"] = top(cand["reversal_10s"], lambda e: -e["swing_MW"], distinct=False)
sel["step_up_1s"] = top(cand["step_up_1s"], lambda e: e["dP_MW"], distinct=False, n=5)
sel["step_down_1s"] = top(cand["step_down_1s"], lambda e: -e["dP_MW"], distinct=False, n=5)
json.dump(sel, open(f"{R}/candidates.json", "w"), indent=1)

# ------------------------------------------------ 5-min traces (1 s) around the chosen EMT cases
def pick(key):
    e = sel[key][0]
    return e
cases = {"A_sustained_transfer": (sel["sustained_sx_by_run090"][0]["week"], sel["sustained_sx_by_run090"][0]["run090_start"], 120),
         "B_low_voltage_saturation": (sel["lowest_Ua_near_saturation"][0]["week"], sel["lowest_Ua_near_saturation"][0]["t_s"], 150),
         "C_reversal_5s": (sel["reversal_5s"][0]["week"], sel["reversal_5s"][0]["t_s"], 60),
         "D_step_up_1s": (sel["step_up_1s"][0]["week"], sel["step_up_1s"][0]["t_s"], 60),
         "D2_step_down_1s": (sel["step_down_1s"][0]["week"], sel["step_down_1s"][0]["t_s"], 60),
         "E_peak_load_week15": (15, int(np.argmax(np.hypot(np.load(f"{D}/legs_w015.npz")["P_L"], np.load(f"{D}/legs_w015.npz")["Q_L"]))), 120)}
for nm, (k, t, half) in cases.items():
    z = np.load(f"{D}/legs_w{k:03d}.npz")
    i0 = max(0, t - half)
    for f in FIELDS + ["I_alpha_A", "I_beta_A", "I_rpc_alpha_A", "I_rpc_beta_A"]:
        traces[f"{nm}__{f}"] = z[f][i0:t + 3 * half].astype(np.float32)
    traces[f"{nm}__t0"] = np.array([k, i0])
np.savez_compressed(f"{R}/candidate_traces.npz", **traces)
print(json.dumps({k: [ (e['week'], e['clock']) for e in v] for k, v in sel.items()}, indent=0)[:1500])
