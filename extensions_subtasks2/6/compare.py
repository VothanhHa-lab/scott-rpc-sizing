#!/usr/bin/env python3
"""Compare the Simulink results (CSV files from run_validation.m) with the Python models.

Usage
    python3 compare.py                         # reads simulink_out/, writes compare_out/
    python3 compare.py --indir DUMMY_simulink_out --prefix DUMMY_   # pipeline test with dummy data

Inputs (exact columns, see matlab/run_validation.m)
    caseA_results.csv    case_id,load_model,Ssc_MVA,k,dphi_deg, Sa/Sb set/act, IUF_pct, VUF_pct, ...
    caseB_results.csv    case_id,load_model,Ssc_MVA,rating_MVA, ...
    caseC_summary.csv    case_id,method,ff,Vdc_min_V,Vdc_max_V,Vdc_dev_max_pct,Ia_max_pu,Ib_max_pu,settle_s
    caseC_timeseries.csv case_id,method,t_s,Vdc_V,Ia_pu,Ib_pu,Pa_MW,Pb_MW
Outputs (in --outdir)
    <prefix>comparison_A.csv / _B.csv / _C.csv, <prefix>comparison_summary.md,
    <prefix>comparison_table.tex, <prefix>validation_fig.pdf / .png

If the first line of an input file starts with '# DUMMY' the data are treated as dummy data:
all outputs are stamped DUMMY and must not be used in the paper.
"""
import argparse, json, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ref_models as R                                  # noqa: E402

# acceptance thresholds, fixed before any Simulink number was seen
TOL = dict(vuf_rel_pct=1.0,       # |VUF_sim - VUF_py| / VUF_py            (A, B)
           vuf_abs_pp=0.005,      # used instead when VUF_py < 0.5 %
           iuf_abs_pp=0.3,        # |IUF_sim - IUF_py|
           S_rel_pct=1.0,         # feeder apparent power actually drawn
           vdc_abs_V=5.0,         # case C, vs continuous-time Python solution
           i_rel_pct=0.5,
           settle_abs_ms=3.0)

BLUE, ORANGE, GREEN, VERM, PURPLE, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#7f7f7f"
MODEL_COLOR = dict(CZ=BLUE, CP=ORANGE, CI=GREEN)
for f in fm.findSystemFonts():
    if "LiberationSans" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8, "axes.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


# ----------------------------------------------------------------------------- IO
def read_csv(path):
    if not os.path.exists(path):
        return None, False
    with open(path) as fh:
        first = fh.readline()
    return pd.read_csv(path, comment="#"), first.startswith("# DUMMY")


def py_row(rows, set_, cid, model):
    for r in rows:
        if r["set"] == set_ and r["id"] == cid and r["load_model"] == model:
            return r
    raise KeyError((set_, cid, model))


def check_reference_consistency(ref):
    """Recompute the Python rows and make sure python_reference.json is up to date."""
    worst = 0.0
    for r in ref["reference_rows"]:
        if r["set"] == "A":
            c = next(c for c in ref["caseA"] if c["id"] == r["id"]); Sa, Sb = R.case_A_loads(c)
        else:
            c = next(c for c in ref["caseB"] if c["id"] == r["id"]); Sa, Sb = R.case_B_loads(c)
        e = R.EXACT[r["load_model"]](Sa, Sb, c["Ssc_MVA"])
        worst = max(worst, abs(e["VUF_pct"] - r["VUF_exact_pct"]), abs(e["IUF_pct"] - r["IUF_exact_pct"]))
    return worst


# ----------------------------------------------------------------------------- tables A, B
def compare_AB(df, ref, set_):
    rows = []
    for _, s in df.iterrows():
        p = py_row(ref["reference_rows"], set_, s["case_id"], s["load_model"])
        Sa_py = complex(p["Sa_act_P_MW"], p["Sa_act_Q_Mvar"]); Sb_py = complex(p["Sb_act_P_MW"], p["Sb_act_Q_Mvar"])
        Sa_sm = complex(s["Sa_act_P_MW"], s["Sa_act_Q_Mvar"]); Sb_sm = complex(s["Sb_act_P_MW"], s["Sb_act_Q_Mvar"])
        # relative error of the apparent power actually drawn (only for feeders with a real load)
        errS = []
        for a, b in ((Sa_sm, Sa_py), (Sb_sm, Sb_py)):
            if abs(b) > 0.05:
                errS.append(abs(abs(a) - abs(b)) / abs(b) * 100)
        r = dict(set=set_, case_id=s["case_id"], load_model=s["load_model"], Ssc_MVA=s["Ssc_MVA"])
        if set_ == "A":
            r.update(k=s["k"], dphi_deg=s["dphi_deg"])
        else:
            r.update(rating_MVA=s["rating_MVA"])
        r.update(IUF_sim=s["IUF_pct"], IUF_eq7=p["IUF_eq7_pct"], IUF_py=p["IUF_exact_pct"],
                 VUF_sim=s["VUF_pct"], VUF_eq8=p["VUF_eq8_pct"], VUF_py=p["VUF_exact_pct"],
                 VUF_py_networksolve=p["VUF_network_solve_pct"])
        r["dIUF_abs_pp"] = r["IUF_sim"] - r["IUF_py"]
        r["dVUF_abs_pp"] = r["VUF_sim"] - r["VUF_py"]
        r["dVUF_rel_pct"] = r["dVUF_abs_pp"] / r["VUF_py"] * 100 if r["VUF_py"] > 1e-9 else np.nan
        r["dVUF_vs_eq8_rel_pct"] = (r["VUF_sim"] - r["VUF_eq8"]) / r["VUF_eq8"] * 100 if r["VUF_eq8"] > 1e-9 else np.nan
        r["dIUF_vs_eq7_abs_pp"] = r["IUF_sim"] - r["IUF_eq7"] if r["IUF_eq7"] is not None else np.nan
        r["S_err_pct"] = max(errS) if errS else np.nan
        ok_v = (abs(r["dVUF_rel_pct"]) <= TOL["vuf_rel_pct"]) if r["VUF_py"] >= 0.5 else (abs(r["dVUF_abs_pp"]) <= TOL["vuf_abs_pp"])
        ok_i = abs(r["dIUF_abs_pp"]) <= TOL["iuf_abs_pp"] if not np.isnan(r["dIUF_abs_pp"]) else True
        ok_s = (r["S_err_pct"] <= TOL["S_rel_pct"]) if not np.isnan(r["S_err_pct"]) else True
        r["PASS"] = bool(ok_v and ok_i and ok_s)
        if set_ == "B":
            r["paper_VUF_sim"] = {"B1_none": 3.77, "B2_Ponly": 2.67, "B3_eq11": 2.04, "B4_full": 0.00}[s["case_id"]]
        rows.append(r)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- table C
def compare_C(dfC, ref):
    pyC = pd.DataFrame(ref["python_caseC"])
    rows = []
    for _, s in dfC.iterrows():
        cid = s["case_id"]
        eu = pyC[(pyC.case_id == cid) & (pyC.method == "euler_dt2e-4")].iloc[0]
        co = pyC[(pyC.case_id == cid) & (pyC.method == "continuous_rk45")].iloc[0]
        r = dict(case_id=cid, method=s["method"])
        for key, unit in (("Vdc_min_V", "V"), ("Vdc_max_V", "V"), ("Ia_max_pu", "pu"), ("Ib_max_pu", "pu"), ("settle_s", "s")):
            r[key + "_sim"] = s[key]
            r[key + "_py_euler"] = eu[key]
            r[key + "_py_cont"] = co[key]
        r["d_Vdcmin_V"] = s["Vdc_min_V"] - co["Vdc_min_V"]
        r["d_Vdcmax_V"] = s["Vdc_max_V"] - co["Vdc_max_V"]
        r["d_Ia_rel_pct"] = (s["Ia_max_pu"] - co["Ia_max_pu"]) / co["Ia_max_pu"] * 100
        r["d_Ib_rel_pct"] = (s["Ib_max_pu"] - co["Ib_max_pu"]) / co["Ib_max_pu"] * 100
        r["d_settle_ms"] = (s["settle_s"] - co["settle_s"]) * 1e3
        # difference between the production Euler model of the paper and the continuous solution
        r["euler_vs_cont_Vdcmax_V"] = eu["Vdc_max_V"] - co["Vdc_max_V"]
        r["euler_vs_cont_Vdcmin_V"] = eu["Vdc_min_V"] - co["Vdc_min_V"]
        r["PASS"] = bool(abs(r["d_Vdcmin_V"]) <= TOL["vdc_abs_V"] and abs(r["d_Vdcmax_V"]) <= TOL["vdc_abs_V"]
                         and abs(r["d_Ia_rel_pct"]) <= TOL["i_rel_pct"] and abs(r["d_Ib_rel_pct"]) <= TOL["i_rel_pct"]
                         and abs(r["d_settle_ms"]) <= TOL["settle_abs_ms"])
        rows.append(r)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- figure
def make_figure(A, B, C, ts, ref, ser, dummy, path_pdf, path_png):
    fig, ax = plt.subplots(2, 3, figsize=(10.5, 6.0), constrained_layout=True)
    allAB = pd.concat([x for x in (A, B) if x is not None], ignore_index=True) if (A is not None or B is not None) else None
    # (a) parity plot of VUF
    a = ax[0, 0]
    if allAB is not None:
        for m, col in MODEL_COLOR.items():
            for s_, mk in (("A", "o"), ("B", "s")):
                d = allAB[(allAB.load_model == m) & (allAB.set == s_)]
                if len(d):
                    a.scatter(d.VUF_py, d.VUF_sim, s=22, marker=mk, color=col, edgecolor="k", linewidth=0.4,
                              label=f"{m}, case {s_}", zorder=3)
        mx = float(np.nanmax(allAB[["VUF_py", "VUF_sim"]].values)) * 1.05
        xx = np.linspace(0, mx, 50)
        a.plot(xx, xx, color="k", lw=0.8, zorder=1)
        a.fill_between(xx, xx * (1 - TOL["vuf_rel_pct"] / 100), xx * (1 + TOL["vuf_rel_pct"] / 100), color=SKY, alpha=0.35, lw=0, zorder=0,
                       label=f"$\\pm${TOL['vuf_rel_pct']:g} %")
        a.legend(frameon=False, fontsize=6.5, loc="upper left")
    a.set_xlabel("VUF, Python exact phasor model (%)"); a.set_ylabel("VUF, Simulink (%)")
    a.set_title("(a) VUF at the PCC: Simulink vs Python", fontsize=8, loc="left")
    # (b) relative errors
    b = ax[0, 1]
    if allAB is not None:
        d = allAB.reset_index(drop=True)
        d = d[d.VUF_py > 0.05]
        x = np.arange(len(d))
        b.axhspan(-TOL["vuf_rel_pct"], TOL["vuf_rel_pct"], color=SKY, alpha=0.35, lw=0)
        b.scatter(x, d.dVUF_rel_pct, s=22, c=[MODEL_COLOR[m] for m in d.load_model], edgecolor="k", linewidth=0.4, zorder=3,
                  label="Simulink vs Python exact (same load model)")
        b.scatter(x, d.dVUF_vs_eq8_rel_pct, s=26, marker="D", facecolor="none", edgecolor=VERM, linewidth=0.9, zorder=2,
                  label="Simulink vs approximation (8)")
        b.axhline(0, color="k", lw=0.5)
        b.set_xticks(x); b.set_xticklabels([f"{r.case_id.split('_',1)[0]}{i}" for i, r in enumerate(d.itertuples())],
                                           rotation=90, fontsize=5)
        b.set_xlabel("row index of comparison_A/B.csv (colour = load model)", fontsize=6.5)
        b.legend(frameon=False, fontsize=6.5, loc="best")
    b.set_ylabel("relative VUF difference (%)")
    b.set_title("(b) Difference per case", fontsize=8, loc="left")
    # (c) IUF case A (constant impedance, the model of eq. (7))
    c = ax[0, 2]
    if A is not None:
        d = A[A.load_model == "CZ"].reset_index(drop=True)
        x = np.arange(len(d))
        c.plot(x, d.IUF_eq7, linestyle="none", color=PURPLE, marker="^", ms=5, label="eq. (7)")
        c.plot(x, d.IUF_py, linestyle="none", color=ORANGE, marker="s", ms=4, label="Python exact (CZ)")
        c.plot(x, d.IUF_sim, linestyle="none", color=BLUE, marker="o", ms=7, mfc="none", mew=1.2, label="Simulink (CZ)")
        c.set_xticks(x); c.set_xticklabels([f"{int(r.Ssc_MVA)}\nk={r.k:g}\n{int(r.dphi_deg)}$^\\circ$" for r in d.itertuples()], fontsize=5)
        c.legend(frameon=False, fontsize=6.5)
    c.set_ylabel("IUF (%)"); c.set_title("(c) IUF, case A (Ssc, k, $\\Delta\\varphi$)", fontsize=8, loc="left")
    # (d)-(f) case C
    def series(case_id, method, key):
        d = ts[(ts.case_id == case_id) & (ts.method == method)]
        return d.t_s.values, d[key].values

    def py_series(ff, kind, key):
        t = ser[f"{kind}_ff{ff}_t"]; y = ser[f"{kind}_ff{ff}_{key}"]
        return t, y

    methods = sorted(ts.method.unique()) if ts is not None else []
    mcol = {"simulink": BLUE, "matlab_ode45": PURPLE}
    for j, (ff, ttl) in enumerate(((0, "(d) $V_\\mathrm{dc}$, PI only (no feed-forward)"), (1, "(e) $V_\\mathrm{dc}$, with feed-forward"))):
        e = ax[1, j]
        if ser is not None:
            t, y = py_series(ff, "euler", "Vdc"); e.plot(t, y, color=ORANGE, lw=1.2, ls="--", label="Python (Euler, 0.2 ms; paper)")
            t, y = py_series(ff, "cont", "Vdc"); e.plot(t, y, color=GREEN, lw=1.0, label="Python, continuous-time")
        for m in methods:
            t, y = series(f"C_ff{ff}", m, "Vdc_V")
            e.plot(t, y, color=mcol.get(m, GREY), lw=0.9, ls=":", label=m.replace("_", " "))
        e.axvline(R.T_STEP, color=GREY, lw=0.5)
        e.axhline(R.RPC["Vdc_ref"] * 1.1, color=GREY, lw=0.5, ls="-.")
        e.axhline(R.RPC["Vdc_ref"] * 0.9, color=GREY, lw=0.5, ls="-.")
        e.set_xlim(39.9, 40.4); e.set_xlabel("t (s)"); e.set_ylabel("$V_\\mathrm{dc}$ (V)")
        if ff == 1:
            e.set_ylim(3490, 3510)
        e.set_title(ttl, fontsize=8, loc="left")
        if j == 0:
            e.legend(frameon=False, fontsize=6.5, loc="upper right")
    f = ax[1, 2]
    if ser is not None:
        t, y = py_series(0, "cont", "Ia"); f.plot(t, y, color=GREEN, lw=1.4, label="$I_\\alpha$ Python cont.")
        t, y = py_series(0, "cont", "Ib"); f.plot(t, y, color=VERM, lw=1.4, label="$I_\\beta$ Python cont.")
    for m in methods:
        for key, lab, col in (("Ia_pu", "$I_\\alpha$", BLUE if m == "simulink" else SKY), ("Ib_pu", "$I_\\beta$", PURPLE if m == "simulink" else ORANGE)):
            t, y = series("C_ff0", m, key)
            f.plot(t, y, color=col, lw=0.9, ls=":", label=f"{lab} {m.replace('_',' ')}")
    f.set_xlim(39.9, 40.4); f.set_xlabel("t (s)"); f.set_ylabel("leg current (pu of rating)")
    f.set_title("(f) Leg currents, PI only", fontsize=8, loc="left")
    f.legend(frameon=False, fontsize=6, loc="lower right")
    if dummy:
        fig.text(0.5, 0.5, "DUMMY DATA\nNOT SIMULINK RESULTS", ha="center", va="center", fontsize=40, color="red",
                 alpha=0.25, rotation=25, weight="bold")
    fig.savefig(path_pdf)
    fig.savefig(path_png, dpi=200)
    plt.close(fig)


# ----------------------------------------------------------------------------- tex table
def fmt(x, nd=2):
    return "--" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def write_tex(path, A, B, C, dummy):
    L = []
    if dummy:
        L.append("% DUMMY DATA -- NOT SIMULINK RESULTS -- DO NOT USE IN THE PAPER")
    L.append("% Generated by compare.py. Simulink columns come from run_validation.m output.")
    if A is not None:
        sel = A[(A.load_model == "CZ")]
        keep = [(500, 0.0, 0), (500, 0.5, 0), (500, 1.0, 20), (1000, 0.0, 0), (1000, 0.5, 0), (1000, 1.0, 20)]
        L += ["\\begin{table}[htbp]",
              "\\caption{\\label{tVal1}Scott substation with linear (constant-impedance) loads: IUF and VUF at the PCC from expressions (7)--(8), the exact phasor model and the Simulink model.}",
              "\\centering", "\\begin{adjustbox}{max width=\\linewidth}",
              "\\begin{tabular}{@{}rrrrrrrrrr}", "\\hline",
              "$S_\\mathrm{sc}$ (MVA) & $k$ & $\\Delta\\varphi$ ($^\\circ$) & IUF (7) (\\%) & IUF exact (\\%) & IUF Simulink (\\%) & VUF (8) (\\%) & VUF exact (\\%) & VUF Simulink (\\%) & diff.\\ (\\%)\\\\",
              "\\hline"]
        for ssc, k, dp in keep:
            r = sel[(sel.Ssc_MVA == ssc) & (sel.k == k) & (sel.dphi_deg == dp)]
            if len(r):
                r = r.iloc[0]
                L.append(f"{int(ssc)} & {k:g} & {dp} & {fmt(r.IUF_eq7)} & {fmt(r.IUF_py)} & {fmt(r.IUF_sim)} & {fmt(r.VUF_eq8,3)} & {fmt(r.VUF_py,3)} & {fmt(r.VUF_sim,3)} & {fmt(r.dVUF_rel_pct)}\\\\")
        L += ["\\hline", "\\end{tabular}", "\\end{adjustbox}", "\\end{table}", ""]
    if B is not None:
        L += ["\\begin{table}[htbp]",
              "\\caption{\\label{tVal2}Ideal RPC transfer ($S_\\mathrm{sc}=500$~MVA, 18.5~MVA load, $\\cos\\varphi=0.89$): VUF for the rating of (11), exact phasor model and Simulink model, with the ideal converter and the load represented as current sources (CI) or as constant-power loads (CP).}",
              "\\centering", "\\begin{adjustbox}{max width=\\linewidth}",
              "\\begin{tabular}{@{}lrrrrrr}", "\\hline",
              "Option & rating (MVA) & VUF (8) (\\%) & CI exact / Simulink (\\%) & CP exact / Simulink (\\%) & diff.\\ CI (\\%) & diff.\\ CP (\\%)\\\\",
              "\\hline"]
        for cid, lab in (("B1_none", "No compensation"), ("B2_Ponly", "Active power only"), ("B3_eq11", "Along $\\underline{S}_L$, (11)"), ("B4_full", "Full compensation")):
            ci = B[(B.case_id == cid) & (B.load_model == "CI")]; cp = B[(B.case_id == cid) & (B.load_model == "CP")]
            if len(ci) and len(cp):
                ci, cp = ci.iloc[0], cp.iloc[0]
                L.append(f"{lab} & {fmt(ci.rating_MVA)} & {fmt(ci.VUF_eq8)} & {fmt(ci.VUF_py)} / {fmt(ci.VUF_sim)} & {fmt(cp.VUF_py)} / {fmt(cp.VUF_sim)} & {fmt(ci.dVUF_rel_pct)} & {fmt(cp.dVUF_rel_pct)}\\\\")
        L += ["\\hline", "\\end{tabular}", "\\end{adjustbox}", "\\end{table}", ""]
    if C is not None:
        L += ["\\begin{table}[htbp]",
              "\\caption{\\label{tVal3}Averaged RPC model, load step of $-10$~MW at $t=40$~s: Python (explicit Euler, 0.2~ms; used in the paper), Python (continuous time) and the Simulink/MATLAB solution of the same equations.}",
              "\\centering", "\\begin{adjustbox}{max width=\\linewidth}",
              "\\begin{tabular}{@{}llrrrrr}", "\\hline",
              "Controller & Solution & $V_\\mathrm{dc,min}$ (V) & $V_\\mathrm{dc,max}$ (V) & $I_\\alpha^\\mathrm{max}$ (pu) & $I_\\beta^\\mathrm{max}$ (pu) & settling (ms)\\\\",
              "\\hline"]
        for cid, lab in (("C_ff0", "PI only"), ("C_ff1", "with feed-forward")):
            sub = C[C.case_id == cid]
            if not len(sub):
                continue
            r = sub.iloc[0]
            L.append(f"{lab} & Python Euler & {fmt(r.Vdc_min_V_py_euler,1)} & {fmt(r.Vdc_max_V_py_euler,1)} & {fmt(r.Ia_max_pu_py_euler,3)} & {fmt(r.Ib_max_pu_py_euler,3)} & {fmt(r.settle_s_py_euler*1e3,1)}\\\\")
            L.append(f" & Python continuous & {fmt(r.Vdc_min_V_py_cont,1)} & {fmt(r.Vdc_max_V_py_cont,1)} & {fmt(r.Ia_max_pu_py_cont,3)} & {fmt(r.Ib_max_pu_py_cont,3)} & {fmt(r.settle_s_py_cont*1e3,1)}\\\\")
            for _, r in sub.iterrows():
                L.append(f" & {r.method.replace('_',' ')} & {fmt(r.Vdc_min_V_sim,1)} & {fmt(r.Vdc_max_V_sim,1)} & {fmt(r.Ia_max_pu_sim,3)} & {fmt(r.Ib_max_pu_sim,3)} & {fmt(r.settle_s_sim*1e3,1)}\\\\")
            L.append("\\hline")
        L += ["\\end{tabular}", "\\end{adjustbox}", "\\end{table}", ""]
    open(path, "w").write("\n".join(L))


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default=os.path.join(HERE, "simulink_out"))
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    ref = json.load(open(os.path.join(HERE, "python_reference.json")))
    drift = check_reference_consistency(ref)
    print(f"python_reference.json consistent with current Python models (max drift {drift:.2e} %)")
    if drift > 1e-6:
        print("WARNING: python_reference.json is out of date -> run make_reference.py", file=sys.stderr)

    dA, dumA = read_csv(os.path.join(a.indir, "caseA_results.csv"))
    dB, dumB = read_csv(os.path.join(a.indir, "caseB_results.csv"))
    dC, dumC = read_csv(os.path.join(a.indir, "caseC_summary.csv"))
    dT, dumT = read_csv(os.path.join(a.indir, "caseC_timeseries.csv"))
    dummy = bool(dumA or dumB or dumC or dumT)
    if dA is None and dB is None and dC is None:
        sys.exit(f"no result CSV found in {a.indir}")
    A = compare_AB(dA, ref, "A") if dA is not None else None
    B = compare_AB(dB, ref, "B") if dB is not None else None
    C = compare_C(dC, ref) if dC is not None else None
    p = a.prefix + ("DUMMY_" if dummy and not a.prefix.startswith("DUMMY") else "")
    outdir = a.outdir or os.path.join(HERE, "DUMMY_compare_out" if dummy else "compare_out")
    os.makedirs(outdir, exist_ok=True)
    if A is not None: A.to_csv(os.path.join(outdir, p + "comparison_A.csv"), index=False)
    if B is not None: B.to_csv(os.path.join(outdir, p + "comparison_B.csv"), index=False)
    if C is not None: C.to_csv(os.path.join(outdir, p + "comparison_C.csv"), index=False)
    ser = None
    npz = os.path.join(HERE, "python_caseC_series.npz")
    if os.path.exists(npz):
        ser = dict(np.load(npz))
    figpdf = os.path.join(outdir, p + "validation_fig.pdf")
    make_figure(A, B, C, dT, ref, ser, dummy, figpdf, figpdf.replace(".pdf", ".png"))
    write_tex(os.path.join(outdir, p + "comparison_table.tex"), A, B, C, dummy)

    # ---- markdown summary
    L = []
    if dummy:
        L += ["**DUMMY DATA GENERATED BY PYTHON -- THESE ARE NOT SIMULINK RESULTS**", ""]
    L += ["# Simulink vs Python comparison", "",
          f"Acceptance thresholds (fixed a priori): {json.dumps(TOL)}", ""]
    npass = nall = 0
    for name, T_ in (("A", A), ("B", B), ("C", C)):
        if T_ is None:
            continue
        npass += int(T_.PASS.sum()); nall += len(T_)
        L += [f"## Case {name}: {int(T_.PASS.sum())}/{len(T_)} rows within tolerance", ""]
        if name in "AB":
            cols = ["case_id", "load_model", "IUF_eq7", "IUF_py", "IUF_sim", "dIUF_abs_pp", "VUF_eq8", "VUF_py", "VUF_sim",
                    "dVUF_abs_pp", "dVUF_rel_pct", "dVUF_vs_eq8_rel_pct", "S_err_pct", "PASS"]
        else:
            cols = ["case_id", "method", "Vdc_min_V_sim", "Vdc_min_V_py_cont", "Vdc_max_V_sim", "Vdc_max_V_py_cont",
                    "Ia_max_pu_sim", "Ia_max_pu_py_cont", "Ib_max_pu_sim", "Ib_max_pu_py_cont", "settle_s_sim",
                    "settle_s_py_cont", "d_Vdcmin_V", "d_Vdcmax_V", "d_Ia_rel_pct", "d_Ib_rel_pct", "d_settle_ms",
                    "euler_vs_cont_Vdcmax_V", "PASS"]
        L += [T_[cols].to_markdown(index=False, floatfmt=".4g") if hasattr(T_, "to_markdown") and _has_tabulate() else T_[cols].to_string(index=False), ""]
    L += [f"Overall: {npass}/{nall} rows within tolerance.", ""]
    open(os.path.join(outdir, p + "comparison_summary.md"), "w").write("\n".join(L))
    print("\n".join(L[:6]))
    print(f"wrote results to {outdir} (prefix '{p}'), overall {npass}/{nall} within tolerance")
    if dummy:
        print("NOTE: input was DUMMY data -> outputs are stamped DUMMY")


def _has_tabulate():
    try:
        import tabulate  # noqa
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
