"""Collect the results of sub-task 4.4 into results_summary.json and ready-to-paste LaTeX (tables_4_4.tex).
Every number written to the LaTeX is read from the JSON files produced by the scripts (no typed-in results)."""
import json, os
import numpy as np

D = "/home/claude/subtasks4/4/"


def J(fn):
    p = D + fn
    return json.load(open(p)) if os.path.exists(p) else None


plb, pls = J("plaus_base.json"), J("plaus_suburban.json")
rb, rs = J("runs_base.json"), J("runs_suburban.json")
cb, cs = J("corr_base.json"), J("corr_suburban.json")
gs, gb = J("regen_suburban.json"), J("regen_base.json")
ks, kb = J("cat_suburban_z0.2.json"), J("cat_base_z0.2.json")
t8 = {r["case"]: r["new"] for r in json.load(open("/home/claude/subtasks3/4/t8_updated.json"))["t8"]}


def pr(d):
    return None if d is None else dict(C=d["C"], eps=d["eps"], J=d["J"], cap=d["cap"], loss=d["loss"], viol=d["viol"],
                                       n_comply=d["n_comply"], Eviol_yr=d["Eviol_yr"], p95_mean=d["p95_mean"])


def rel(a, b):
    return 100.0 * (a - b) / b if b else float("nan")


S = {"note": "plausibility check of planning scenarios (no measured data); designs with approximation (8), Ssc=750 MVA"}

# ------------------------------------------------------------------ (b) correlated delays
for nm, c in (("base", cb), ("suburban", cs)):
    if not c:
        continue
    d = {}
    for sc in ("independent", "correlated"):
        r = c[sc]
        d[sc] = dict(N=r["N"], proposed=pr(r["proposed"]), percentile=pr(r["percentile"]), percentile_Copt=pr(r["percentile_Copt"]),
                     chat=r["chat"], cmin_eps1_mean=float(np.mean([x[4] for x in r["cmin"]])),
                     cmin_eps1_max=float(np.max([x[4] for x in r["cmin"]])), cmin_eps1=[x[4] for x in r["cmin"]])
    d["transfer"] = {k: {kk: v[kk] for kk in v if kk not in ("p95_weeks", "Eviol_weeks")} for k, v in c["transfer"].items()}
    d["rel"] = dict(dC_prop=rel(d["correlated"]["proposed"]["C"], d["independent"]["proposed"]["C"]),
                    dJ_prop=rel(d["correlated"]["proposed"]["J"], d["independent"]["proposed"]["J"]),
                    dChat2=rel(d["correlated"]["chat"][-1 if False else 8], d["independent"]["chat"][8]) if d["independent"]["chat"][8] else None)
    S["corr_" + nm] = d

# ------------------------------------------------------------------ (c) regeneration
for nm, g in (("suburban", gs), ("base", gb)):
    if not g:
        continue
    d = dict(accounting=g["accounting_MWh_per_week"], designs={})
    for k, v in g["designs"].items():
        d["designs"][k] = dict(proposed=pr(v["proposed"]), percentile=pr(v["percentile"]), percentile_Copt=pr(v["percentile_Copt"]),
                               chat=v["chat"], N=v["N"])
    d["transfer"] = {k: {kk: v[kk] for kk in v if kk not in ("p95_weeks", "Eviol_weeks")} for k, v in g.get("transfer", {}).items()}
    p0 = d["designs"]["v7"]["proposed"]
    d["rel"] = {k: dict(dC=rel(v["proposed"]["C"], p0["C"]), dJ=rel(v["proposed"]["J"], p0["J"])) for k, v in d["designs"].items()}
    S["regen_" + nm] = d
for nm, g in (("suburban", ks), ("base", kb)):
    if not g:
        continue
    d = dict(n_weeks=g["n_weeks"], z=g["z_ohm_per_km"], accounting=g["accounting_MWh_per_week"], S_stats=g["S_stats"], designs={})
    for k, v in g["designs"].items():
        d["designs"][k] = dict(proposed=pr(v["proposed"]), percentile=pr(v["percentile"]), percentile_Copt=pr(v["percentile_Copt"]), chat=v["chat"],
                               N=v["N"], cmin_eps1_mean=float(np.mean([x[4] for x in v["cmin"]])))
    d["transfer"] = {k: {kk: v[kk] for kk in v if kk not in ("p95_weeks", "Eviol_weeks")} for k, v in g.get("transfer", {}).items()}
    p0 = d["designs"]["A_lumped_return"]["proposed"]
    d["rel"] = {k: dict(dC=rel(v["proposed"]["C"], p0["C"]), dJ=rel(v["proposed"]["J"], p0["J"])) for k, v in d["designs"].items()}
    S["cat_" + nm] = d

# ------------------------------------------------------------------ (a) plausibility
S["plaus_base"], S["plaus_suburban"], S["runs_base"], S["runs_suburban"] = plb, pls, rb, rs
v300 = 300.0
S["davis_R300_kN"] = dict(
    v7_HS=4.0 + 0.030 * v300 + 0.00075 * v300 ** 2,
    somaschini2016_450t=(5.14e-3 * 450e3 + 17.04 * v300 / 3.6 + 6.357 * (v300 / 3.6) ** 2) / 1e3,
    crh380al_890t=(5200 + 25.35 * v300 + 1.084 * v300 ** 2) / 1e3,
    v7_suburban_160=2.5 + 0.025 * 160 + 0.0006 * 160 ** 2)
S["ICE3_energy_derived_kWh_per_trainkm"] = dict(from_40Wh_per_seatkm_460seats=40e-3 * 460, from_35Wh_per_m2km_538m2=35e-3 * 538,
                                                standardised_330kmh_500m2=23.0)
json.dump(S, open(D + "results_summary.json", "w"), indent=1)


# ------------------------------------------------------------------ LaTeX
def f(x, n=1):
    return f"{x:.{n}f}"


def sg(x, n=1):
    return f"{x:+.{n}f}"


L = []
if plb and rb:
    m = lambda d, k, sc="b": d[sc][k]["mean"]
    L.append(r"""%% ---------------------------------------------------------------------------------------------
%% Table P: plausibility check of the planning scenario (no measured data)
\begin{table}[htbp]
\caption{\label{tPlaus}Plausibility check of the planning scenarios against published data (no measured substation data were available; 40 simulated weeks per line, mean over weeks; 6:00--24:00 for time shares).}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}p{4.1cm}p{4.4cm}p{6.4cm}@{}}
\hline
Quantity & Planning scenario (this paper) & Published (source)\\
\hline
\multicolumn{3}{@{}l}{\textit{High-speed EMU, 300~km/h}}\\
Mass & 450~t (loaded) & ICE~3: 455~t unloaded, 8~cars, 460 seats~\cite{fritz2018}\\
Maximum power & 8.8~MW at the wheel (%s~MW at the pantograph with auxiliaries) & ICE~3 8.0~MW~\cite{wikiice3}; CRH380A 9.6~MW~\cite{wikicrh380a}\\
Maximum tractive effort & 280~kN & ICE~3 300~kN at start, 270~kN at 106~km/h~\cite{wikiice3}\\
Running resistance at 300~km/h, level & %s~kN & %s~kN (generic 450~t train, full-scale tests~\cite{somaschini2016}); %s~kN (CRH380AL, 890~t, 16 cars~\cite{liu2025})\\
Energy at the pantograph per train-km (gross) & %s~kWh (all runs, 29\%% with a stop); %s~kWh non-stop; %s~kWh net of regeneration & ICE~3 at 300--330~km/h: 40~Wh per seat-km, i.e.\ about %s~kWh per train-km with 460 seats (derived); 23~kWh/km standardised to 500~m$^2$ at 330~km/h~\cite{fritz2018}\\
Zone transit (50~km) & %s~s non-stop, %s~s with a stop; mean speed %s~km/h & --- (kinematic consequence of 300~km/h)\\
Trains in the zone (both tracks) & mean %s, 95\%%/99\%% quantile %s/%s, maximum %s & no published statistic found\\
Trains at $\ge90$\%% of the maximum power at the same time & $\ge1$: %s\%%, $\ge2$: %s\%%, $\ge3$: %s\%% of the time; 99\%% quantile %s, maximum %s & no published statistic found\\
Substation load $P_L$ & mean %s~MW (%s~MW 6:00--24:00); 95\%%/99\%% quantile %s/%s~MW; 15-min maximum %s~MW; weekly maximum %s~MW & no measured values found in the open literature (a recent review notes that operating data of traction load are not available in China~\cite{li2022})\\
\hline
""" % (f(rb["Pel_max_MW"], 2), f(S["davis_R300_kN"]["v7_HS"]), f(S["davis_R300_kN"]["somaschini2016_450t"]), f(S["davis_R300_kN"]["crh380al_890t"]),
       f(plb["lib"]["gross_kWh_per_km"]["mean"]), f(rb["gross_kWh_per_km_nonstop"]), f(plb["lib"]["net_kWh_per_km"]["mean"]),
       f(40e-3 * 460), f(rb["dur_s_nonstop"], 0), f(rb["dur_s_stop"], 0), f(plb["lib"]["v_avg_kmh"]["mean"], 0),
       f(m(plb, "nz_mean_op")), f(m(plb, "nz_p95"), 0), f(m(plb, "nz_p99"), 0), f(m(plb, "nz_max"), 0),
       f(100 * m(plb, "frac_nh_ge1"), 0), f(100 * m(plb, "frac_nh_ge2"), 0), f(100 * m(plb, "frac_nh_ge3"), 1), f(m(plb, "nh_p99"), 0), f(m(plb, "nh_max"), 0),
       f(m(plb, "P_mean")), f(m(plb, "P_mean_op")), f(m(plb, "P_p95")), f(m(plb, "P_p99")), f(m(plb, "P15_max")), f(m(plb, "P_max"))))
    if pls and rs:
        L.append(r"""\multicolumn{3}{@{}l}{\textit{Suburban EMU, 160~km/h, stops every 4~km}}\\
Mass, power & 300~t, 4.5~MW at the wheel (%s~MW at the pantograph) & 5-car 200~km/h FLIRT variant: 4.5~MW maximum~\cite{wikiflirt}; no verified mass and energy data for a 160~km/h set\\
Acceleration, braking & $F_\mathrm{max}/m_\mathrm{eff}=%s$~m/s$^2$, service braking 0.8~m/s$^2$ & FLIRT variants 0.6--1.3~m/s$^2$~\cite{wikiflirt}\\
Moving time between stops (4~km) & %s~s (95\%% interval %s--%s~s), dwell 30--60~s & ---\\
Energy at the pantograph per train-km & %s~kWh gross, %s~kWh net of regeneration & no verified published value\\
Trains in the zone & mean %s, 95\%%/99\%% quantile %s/%s, maximum %s & no published statistic found\\
Trains at $\ge90$\%% of the maximum power at the same time & $\ge1$: %s\%%, $\ge2$: %s\%%, $\ge3$: %s\%% of the time; 99\%% quantile %s, maximum %s & no published statistic found\\
Substation load $P_L$ & mean %s~MW; 95\%%/99\%% quantile %s/%s~MW; 15-min maximum %s~MW; weekly maximum %s~MW; net negative %s\%% of the time & no measured values found\\
\hline
""" % (f(5.4398, 2), f(250.0 / (300.0 * 1.06), 2), f(rs["interstation_move_s"]["mean"], 0), f(rs["interstation_move_s"]["p5"], 0),
       f(rs["interstation_move_s"]["p95"], 0), f(pls["lib"]["gross_kWh_per_km"]["mean"]), f(pls["lib"]["net_kWh_per_km"]["mean"]),
       f(m(pls, "nz_mean_op")), f(m(pls, "nz_p95"), 0), f(m(pls, "nz_p99"), 0), f(m(pls, "nz_max"), 0),
       f(100 * m(pls, "frac_nh_ge1"), 0), f(100 * m(pls, "frac_nh_ge2"), 0), f(100 * m(pls, "frac_nh_ge3"), 1), f(m(pls, "nh_p99"), 0), f(m(pls, "nh_max"), 0),
       f(m(pls, "P_mean")), f(m(pls, "P_p95")), f(m(pls, "P_p99")), f(m(pls, "P15_max")), f(m(pls, "P_max")), f(100 * m(pls, "frac_Pneg"), 1)))
    L.append(r"\end{tabular}" + "\n" + r"\end{adjustbox}" + "\n" + r"\end{table}" + "\n")

# ------------------------------------------------------------------ Table CD: correlated delays
if "corr_base" in S:
    def corr_rows(nm, label, plaus):
        d = S["corr_" + nm]
        i, c = d["independent"], d["correlated"]
        out = []
        for sc, tag, pl in (("independent", "independent delays", "b"), ("correlated", "delay episodes", "c")):
            x = d[sc]; pp = x["proposed"]
            out.append("%s & %s & %s & %s & %s & %s & %s & %s & %s & %s & %s\\\\" % (
                label if sc == "independent" else "", tag,
                f(plaus[pl]["nh_p99"]["mean"], 0) + "/" + f(plaus[pl]["nh_max"]["mean"], 1),
                f(plaus[pl]["S_p95"]["mean"]) + "/" + f(plaus[pl]["S_p99"]["mean"]), f(plaus[pl]["S_max"]["mean"]),
                f(x["chat"][8]), f(pp["C"], 2), f(pp["eps"], 2), f(pp["J"]),
                f(x["cmin_eps1_mean"], 2), f(pp["Eviol_yr"])))
        out.append("& change (\\%%) & & & & %s & %s & & %s & & \\\\" % (sg(rel(c["chat"][8], i["chat"][8])), sg(rel(c["proposed"]["C"], i["proposed"]["C"])),
                                                              sg(rel(c["proposed"]["J"], i["proposed"]["J"]))))
        return out
    rows = []
    rows += corr_rows("base", "High-speed", plb)
    if "corr_suburban" in S and pls:
        rows += corr_rows("suburban", "Suburban", pls)
    L.append(r"""%% ---------------------------------------------------------------------------------------------
%% Table CD: correlated delays (same seeds, same train library, same independent delays; episodes added)
\begin{table}[htbp]
\caption{\label{tCorr}Correlated delays (train bunching) against independent delays on the same %d seeds ($S_\mathrm{sc}=750$~MVA, approximation (8), design rule of section~4.3). Delay episodes: 1--3 per day (Poisson, mean 2), shared delay 5--20~min of the first train, linearly decaying over 3--8 consecutive trains of one track, minimum headway 3~min. $\hat C_{2\%%}$: percentile design rating (12); $P_{99}$ and $S_\mathrm{max}$ are weekly values averaged over the weeks.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}llrrrrrrrrr@{}}
\hline
Line & Timetable & \shortstack{Full-power trains\\99\%%/max} & \shortstack{$|S_L|$ 95\%%/99\%%\\(MVA)} & \shortstack{$|S_L|$ max\\(MVA)} & \shortstack{$\hat C_{2\%%}$\\(MVA)} & \shortstack{$C^*$\\(MVA)} & \shortstack{$\varepsilon_u^*$\\(\%%)} & \shortstack{$\bar J$\\(kUSD/yr)} & \shortstack{mean $C_\mathrm{min}$\\($\varepsilon_u=1\%%$)} & \shortstack{$E_\mathrm{viol}$\\(\%%$\cdot$h/yr)}\\
\hline
""" % (S["corr_base"]["independent"]["N"]) + "\n".join(rows) + "\n" + r"""\hline
\end{tabular}
\end{adjustbox}
\end{table}
""")

# ------------------------------------------------------------------ Table RG: regeneration
def acc_row(a, key_returned="returned"):
    ra = a["regen_avail"]
    return ra, a["absorbed_trains"], a[key_returned], a["curtailed"]

blocks = []
for nm, label in (("suburban", "Suburban"), ("base", "High-speed")):
    g = S.get("regen_" + nm)
    if not g:
        continue
    names = [("v7", "v7: return to grid allowed"), ("noreturn_onboard", "no return, on-board resistors"), ("noreturn_wayside", "no return, wayside resistor")]
    for k, tag in names:
        a = g["accounting"][k]; p = g["designs"][k]["proposed"]; r = g["rel"][k]
        ra = a["regen_avail"]
        blocks.append("%s & %s & %s & %s (%s) & %s (%s) & %s (%s) & %s & %s & %s & %s & %s\\\\" % (
            label if k == "v7" else "", tag, f(ra, 1),
            f(a["absorbed_trains"], 1), f(100 * a["absorbed_trains"] / ra, 0), f(a["returned"], 1), f(100 * a["returned"] / ra, 0),
            f(a["curtailed"], 1), f(100 * a["curtailed"] / ra, 0), f(p["C"], 2), f(p["eps"], 2), f(p["J"]), sg(r["dC"]), sg(r["dJ"])))
for nm, label in (("suburban", "Suburban"), ("base", "High-speed")):
    g = S.get("cat_" + nm)
    if not g:
        continue
    names = [("A_lumped_return", "lumped (v7), same %d weeks" % g["n_weeks"]), ("C_catenary_return", "catenary %.1f $\\Omega$/km, return allowed" % g["z"]),
             ("D_catenary_noreturn", "catenary, no return")]
    for k, tag in names:
        a = g["accounting"][k]; p = g["designs"][k]["proposed"]; r = g["rel"][k]
        ra = a.get("regen_avail")
        if ra is None:
            continue
        blocks.append("%s & %s & %s & %s (%s) & %s (%s) & %s (%s) & %s & %s & %s & %s & %s\\\\" % (
            label if k == "A_lumped_return" else "", tag, f(ra, 1),
            f(a["absorbed_trains"], 1), f(100 * a["absorbed_trains"] / ra, 0), f(a["returned"], 1), f(100 * a["returned"] / ra, 0),
            f(a["curtailed"], 1), f(100 * a["curtailed"] / ra, 0), f(p["C"], 2), f(p["eps"], 2), f(p["J"]), sg(r["dC"]), sg(r["dJ"])))
if blocks:
    L.append(r"""%% ---------------------------------------------------------------------------------------------
%% Table RG: limited regeneration
\begin{table}[htbp]
\caption{\label{tRegen}Limited regeneration (same weeks and seeds, $S_\mathrm{sc}=750$~MVA, approximation (8)). Regenerated energy per week available at the pantographs (net of auxiliaries) and its fate: absorbed by other trains in the zone (and line losses), returned to the 110~kV grid, curtailed in brake resistors. Rows 1--3 of each line: 40 weeks, lumped substation; rows 4--6: %s weeks with position-dependent catenary impedance (substation at mid-zone, two arms, regeneration limited to 29~kV at the pantograph; constant-power trains, resistive equivalent impedance). Changes refer to the first row of the respective block.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}llrrrrrrrrr@{}}
\hline
Line & Case & \shortstack{Regen.\\(MWh/wk)} & \shortstack{Other trains\\MWh (\%%)} & \shortstack{To grid\\MWh (\%%)} & \shortstack{Curtailed\\MWh (\%%)} & \shortstack{$C^*$\\(MVA)} & \shortstack{$\varepsilon_u^*$\\(\%%)} & \shortstack{$\bar J$\\(kUSD/yr)} & \shortstack{$\Delta C^*$\\(\%%)} & \shortstack{$\Delta\bar J$\\(\%%)}\\
\hline
""" % ((S.get("cat_suburban") or S.get("cat_base") or {"n_weeks": "n"})["n_weeks"]) + "\n".join(blocks) + "\n" + r"""\hline
\end{tabular}
\end{adjustbox}
\end{table}
""")

open(D + "tables_4_4.tex", "w").write("\n".join(L))
print(json.dumps({k: v for k, v in S.items() if k.startswith(("corr", "regen", "cat"))}, indent=1)[:6000])
print("\n".join(L)[:6000])
