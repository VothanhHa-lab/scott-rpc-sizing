"""EMT candidate table (CSV) from results/candidates.json + data."""
import json, csv, numpy as np
R = "/home/claude/subtasks4/2/results"; D = "/home/claude/subtasks4/2/data"; C = 11.27
c = json.load(open(f"{R}/candidates.json"))
F = ["P_L", "Q_L", "P_alpha", "S_alpha", "I_alpha_pu40", "U_alpha", "U_beta", "I_rpc_alpha_pu", "I_rpc_beta_pu", "vuf", "sx_abs"]
def hms(s):
    d, r = divmod(int(s), 86400); return f"day {d+1} {r//3600:02d}:{(r%3600)//60:02d}:{r%60:02d}"
rows = []
def snap(case, rank, k, i, note, t_end=None):
    z = np.load(f"{D}/legs_w{k:03d}.npz")
    g = {f: float(z[f][i]) for f in F}
    rows.append(dict(case=case, rank=rank, week=k, t_s=int(i), clock=hms(i), P_L=round(g["P_L"], 2), Q_L=round(float(z["Q_L"][i]), 2),
                     S_L=round(float(np.hypot(z["P_L"][i], z["Q_L"][i])), 2), S_alpha=round(g["S_alpha"], 2), I_alpha_pu40=round(g["I_alpha_pu40"], 3),
                     U_alpha=round(g["U_alpha"], 4), U_beta=round(g["U_beta"], 4), sx_over_C=round(g["sx_abs"] / C, 3),
                     I_rpc_alpha_pu=round(g["I_rpc_alpha_pu"], 3), I_rpc_beta_pu=round(g["I_rpc_beta_pu"], 3), vuf_inst=round(g["vuf"], 2), note=note))
for r, e in enumerate(c["sustained_sx_by_run090"], 1):
    k = e["week"]; z = np.load(f"{D}/legs_w{k:03d}.npz")["sx_abs"] / C
    a = e["run090_start"]; L = e["run090_len"]
    snap("A_sustained_transfer", r, k, a + L // 2, f"midpoint of the longest run with |s_x|/C>=0.90: start {hms(a)}, length {L} s, mean {z[a:a+L].mean():.3f}")
for r, e in enumerate(c["lowest_Ua_near_saturation"], 1):
    snap("B_low_voltage_near_saturation", r, e["week"], e["t_s"], "lowest U_alpha among seconds with |s_x|/C>=0.90")
for r, e in enumerate(c["reversal_5s"], 1):
    snap("C_reversal_5s", r, e["week"], e["t_s"], f"P_L falls {e['swing_MW']} MW in 5 s to {e['P_end']} MW")
for r, e in enumerate(c["reversal_10s"], 1):
    snap("C_reversal_10s", r, e["week"], e["t_s"], f"P_L falls {e['swing_MW']} MW in 10 s to {e['P_end']} MW")
for r, e in enumerate(c["step_up_1s"], 1):
    snap("D_step_up_1s", r, e["week"], e["t_s"], f"dP_L = +{e['dP_MW']} MW in 1 s (to {e['P_next']} MW)")
for r, e in enumerate(c["step_down_1s"], 1):
    snap("D_step_down_1s", r, e["week"], e["t_s"], f"dP_L = {e['dP_MW']} MW in 1 s (to {e['P_next']} MW)")
pk = list(csv.DictReader(open(f"{R}/peak_instants.csv")))
for r, w in enumerate((15, 56, 12), 1):
    e = pk[w]; assert int(e["week"]) == w
    snap("E_weekly_peak_load", r, w, int(e["t_s"]), {15: "65.785 MVA: the 95th-percentile (57th of 60) weekly peak = 65.8 MVA of Table 15", 56: "65.798 MVA, neighbouring weekly peak", 12: "68.284 MVA, largest weekly peak"}[w])
for r, e in enumerate(c["highest_alpha_scott_I"][:3], 1):
    snap("F_highest_alpha_scott_current", r, e["week"], e["t_s"], "highest I_alpha/I_N (40 MVA)")
with open(f"{R}/emt_candidates.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
for r in rows: print(r["case"], r["rank"], r["week"], r["clock"], r["P_L"], r["S_L"], r["S_alpha"], r["U_alpha"], r["sx_over_C"], r["I_alpha_pu40"], r["note"][:60])
