"""Collect every number quoted in the manuscript from the result files."""
import json, os
import numpy as np
from scipy import stats
from analyse import load, methods, weekly_cmin, ci95, cost_terms
from rpc_sizing.params import RPC, SEED0
from rpc_sizing.experiment import CASES, base_params
from rpc_sizing import train as tr

W = RPC["weeks_per_year"]
N = {}
f1 = lambda x: f"{x:.1f}"
f2 = lambda x: f"{x:.2f}"
f0 = lambda x: f"{x:.0f}"
pct = lambda a, b: f"{100 * (1 - a / b):.0f}"

# ---------------- base case -------------------------------------------------
s = load("base")
wk = s["weeks"]
meanP = np.mean([w["meanP"] for w in wk])
N.update(meanP=f1(meanP), egwh=f1(meanP * 8760 / 1000),
         negshare=f1(100 * np.mean([w["regen_share"] for w in wk])),
         peakS=f1(np.mean([w["peakS"] for w in wk])),
         peakSq=f1(np.quantile([w["peakS"] for w in wk], 0.95, method="inverted_cdf")))
M = methods(s, 750)
mf, mp, mc, mco, mpr = M["full"], M["peak"], M["p95"], M["p95_Copt"], M["proposed"]
N.update(unc750=f2(np.mean([w["p95_unc"]["750"] for w in wk])),
         Cfull=f1(mf["C"]), Cpeak=f1(mp["C"]), Cp95=f1(mc["C"]), Cprop=f1(mpr["C"]),
         Cco=f1(mco["C"]), eps=f"{mpr['eps']:.2f}".rstrip("0").rstrip("."),
         redpk_p95=pct(mc["C"], mp["C"]), redpk_prop=pct(mpr["C"], mp["C"]),
         red_rating=pct(mpr["C"], mc["C"]),
         share_p95=f1(100 * mc["share"]), share_prop=f1(100 * mpr["share"]),
         p95prop=f2(mpr["p95_mean"]), etr_prop=f1(mpr["Etr"] / 1000), etr_p95=f1(mc["Etr"] / 1000),
         lossinc=f0(100 * (mpr["Eloss"] / mc["Eloss"] - 1)), Jred=pct(mpr["J"], mc["J"]),
         viol_ratio=f"{mpr['Eviol'] / mc['Eviol']:.2f}",
         vmax_lo=f1(min(mc["vmax"], mco["vmax"], mpr["vmax"])), vmax_hi=f1(max(mc["vmax"], mco["vmax"], mpr["vmax"])),
         Jco_vs_p95="the same" if abs(mco["J"] - mc["J"]) / mc["J"] < 0.01 else f"a {pct(mco['J'], mc['J'])}\\% lower")
rows = []
def row(lab, key, fmt):
    rows.append(lab + " & " + " & ".join(fmt(M[k][key]) for k in ["full", "peak", "p95", "p95_Copt", "proposed"]) + "\\\\")
row("Rating per leg $C$ (MVA)", "C", f1)
row("Threshold $\\varepsilon_u$ (\\%)", "eps", lambda x: "0" if x == 0 else f1(x))
row("P95 of 10-min VUF (\\%)", "p95_mean", f2)
row("Weeks meeting the P95 criterion (\\%)", "comply", lambda x: f0(100 * x))
row("Maximum 10-min VUF (\\%)", "vmax", f2)
row("10-min values above 2\\% (\\%)", "share", lambda x: f1(100 * x))
row("Exceedance $E_\\mathrm{viol}$ (\\%$\\cdot$h/yr)", "Eviol", lambda x: "0" if x < 0.05 else f1(x))
row("Energy processed per leg (GWh/yr)", "Etr", lambda x: f1(x / 1000))
row("Losses $E_\\mathrm{loss}$ (MWh/yr)", "Eloss", f0)
rows.append("$J$: capital / losses / exceedance (kUSD/yr) & " + " & ".join(
    f"{M[k]['Jcap']:.0f}/{M[k]['Jloss']:.0f}/{M[k]['Jviol']:.0f}" for k in ["full", "peak", "p95", "p95_Copt", "proposed"]) + "\\\\")
row("Expected annual cost $J$ (kUSD/yr)", "J", f0)
N["TABLE_A"] = "\n".join(rows)

fc = json.load(open("results/figC_stats.json"))
N.update(cshare_conv=f1(100 * fc["share_conv"]), cshare_prop=f1(100 * fc["share_prop"]),
         cp95_conv=f2(fc["p95_conv"]))

d750 = s["design"]["750"]; nf = len(s["c_fact"]); eg = s["eps_grid"]
Jb, Cb = [], []
for i, e in enumerate(eg):
    j = min(range(i * nf, i * nf + nf), key=lambda k: cost_terms(d750["evals"], k)[0])
    Jb.append(cost_terms(d750["evals"], j)[0]); Cb.append(d750["cands"][j][1])
Jb = np.array(Jb)
flat = [eg[i] for i in range(len(eg)) if Jb[i] <= 1.01 * Jb.min()]
istar = eg.index(mpr["eps"])
N.update(Chat2=f1(d750["c_design"][eg.index(2.0)]), Chat0=f1(d750["c_design"][0]),
         Chat_red=pct(d750["c_design"][0], d750["c_design"][eg.index(2.0)]),
         flat_lo=f"{min(flat):g}", flat_hi=f"{max(flat):g}", Chat_star=f1(d750["c_design"][istar]))

x2 = weekly_cmin(s, 750, 2.0); xs = weekly_cmin(s, 750, mpr["eps"])
mu, h = ci95(x2)
n = np.arange(1, len(x2) + 1)
def conv(x):
    m = np.cumsum(x) / n; dev = np.abs(m / m[-1] - 1) * 100
    q = np.array([np.quantile(x[:k], 0.95, method="inverted_cdf") for k in n]); dq = np.abs(q / q[-1] - 1) * 100
    return (next(k + 1 for k in range(len(x)) if dev[k:].max() < 0.5),
            next(k + 1 for k in range(len(x)) if dq[k:].max() < 1.0))
c2, cs = conv(x2), conv(xs)
N.update(conv_m2=str(c2[0]), conv_ms=str(cs[0]), conv_q2=str(c2[1]), conv_qs=str(cs[1]),
         c95min=f2(x2.min()), c95max=f2(x2.max()), c95sd=f2(x2.std(ddof=1)), c95mean=f2(mu), c95h=f2(h),
         c95wk1=f2(x2[0]), single_dev=f0(100 * max(abs(x2.min() / mc["C"] - 1), abs(x2.max() / mc["C"] - 1))))
t7 = []
for S in [500, 750, 1000, 1500, 2000]:
    m = methods(s, S); x = weekly_cmin(s, S, 2.0); a, b = ci95(x) if x.std() > 0 else (0.0, 0.0)
    unc = np.mean([w["p95_unc"][str(S)] for w in wk])
    if m["p95"]["C"] > 0:
        t7.append(f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & {x[0]:.2f} & ${a:.2f}\\pm{b:.2f}$ & {m['p95']['C']:.2f} & {m['proposed']['C']:.2f} & {m['proposed']['eps']:.2f} & {m['p95']['J']:.0f} / {m['proposed']['J']:.0f}\\\\")
    else:
        t7.append(f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & 0 & 0 & 0 & 0 & -- & {m['p95']['J']:.0f} / {m['proposed']['J']:.0f}\\\\")
N["TABLE_7"] = "\n".join(t7)
N["ssc_free"] = str(min(S for S in [500, 750, 1000, 1500, 2000] if methods(s, S)["p95"]["C"] == 0))

# cost-weight sensitivity
lab = [("Base", {}), ("No exceedance penalty ($w_3=0$)", dict(viol=0)), ("Penalty 0.5~kUSD/(\\%$\\cdot$h)", dict(viol=0.5)),
       ("Penalty 5~kUSD/(\\%$\\cdot$h)", dict(viol=5)), ("Energy price 40~USD/MWh", dict(price=40)),
       ("Energy price 160~USD/MWh", dict(price=160)), ("Converter cost 75~kUSD/MVA", dict(cost=75)),
       ("Converter cost 225~kUSD/MVA", dict(cost=225))]
t13, reds, Cs, epss = [], [], [], []
for l, w in lab:
    m = methods(s, 750, w); p, c = m["proposed"], m["p95"]
    r = 100 * (1 - p["J"] / c["J"]); reds.append(r); Cs.append(p["C"]); epss.append(p["eps"])
    t13.append(f"{l} & {p['C']:.2f} & {p['eps']:.2f} & {p['J']:.0f} & {c['J']:.0f} & {r:.0f}\\\\")
N.update(TABLE_13="\n".join(t13), w_red_lo=f0(min(reds)), w_red_hi=f0(max(reds)),
         w_C_lo=f1(min(Cs)), w_C_hi=f1(max(Cs)), w_eps_lo=f"{min(epss):g}", w_eps_hi=f"{max(epss):g}")

# sensitivity (40 weeks)
LAB = {"base": "Base (60 weeks)", "freq_x0.5": "Train frequency $\\times0.5$", "freq_x1.5": "Train frequency $\\times1.5$",
       "power_x0.75": "Train power $\\times0.75$", "power_x1.25": "Train power $\\times1.25$",
       "no_regen": "No regenerative braking", "regen_4MW": "Regenerated power limited to 4~MW",
       "speed_250": "Line speed 250~km/h", "speed_350": "Line speed 350~km/h", "stop_0.5": "50\\% of trains stop",
       "poisson": "Poisson arrivals (independent trains)", "segments_prev": "Random power segments, Poisson arrivals",
       "diode": "Diode trains ($\\cos\\varphi=0.77$, no regeneration)", "grade_alt": "Other grade profile"}
t8, sd, dJs = [], {}, []
for c in LAB:
    ss = s if c == "base" else load(c, "results40")
    m = methods(ss, 750); x = weekly_cmin(ss, 750, 2.0); a, b = ci95(x)
    mp_ = np.mean([w["meanP"] for w in ss["weeks"]])
    pk, p95, pr = m["peak"]["C"], m["p95"]["C"], m["proposed"]["C"]
    dJ = 100 * (1 - m["proposed"]["J"] / m["p95"]["J"]); dJs.append(dJ)
    sd[c] = dict(meanP=mp_, p95=p95, pr=pr, neg=np.mean([w["regen_share"] for w in ss["weeks"]]))
    t8.append(f"{LAB[c]} & {mp_:.1f} & {pk:.1f} & ${a:.2f}\\pm{b:.2f}$ & {p95:.2f} & {pr:.2f} & {m['proposed']['eps']:.2f} & "
              f"{100*(1-p95/pk):.0f} / {100*(1-pr/pk):.0f} & {dJ:.0f}\\\\")
N["TABLE_8"] = "\n".join(t8)
N.update(s_f15=f1(sd["freq_x1.5"]["p95"]), s_p125=f1(sd["power_x1.25"]["p95"]), s_v350=f1(sd["speed_350"]["p95"]),
         s_f05=f1(sd["freq_x0.5"]["p95"]), s_v250=f1(sd["speed_250"]["p95"]),
         s_noreg=f1(sd["no_regen"]["p95"]), s_poi=f1(sd["poisson"]["p95"]),
         s_seg=f1(sd["segments_prev"]["p95"]), s_segP=f1(sd["segments_prev"]["meanP"]),
         s_diode=f1(sd["diode"]["p95"]), s_grade=f1(sd["grade_alt"]["p95"]), s_stop=f1(sd["stop_0.5"]["p95"]),
         s_dJlo=f0(min(dJs)), s_dJhi=f0(max(dJs)))

# dynamic check
import re
dl = open("dyn.log").read()
def vd(tag):
    m = re.search(tag + r" Cdc ([\d.]+) mF Vdc (\d+)\.\.(\d+) Ia ([\d.]+) Ib ([\d.]+)", dl)
    return [float(g) for g in m.groups()]
ff, nf_ = vd("True"), vd("False")
hs = {int(a): (float(b), float(c)) for a, b, c in re.findall(r"H (\d+) Vdc (\d+)\.\.(\d+)", dl)}
pctv = lambda v: f"{100 * (v / 3500 - 1):+.1f}"
N.update(dyn_cdc=f1(ff[0]), dyn_ff_lo=f"{ff[1]/1000:.3f}", dyn_ff_hi=f"{ff[2]/1000:.3f}",
         dyn_nf_hi=f"{nf_[2]/1000:.3f}", dyn_nf_pct=pctv(nf_[2]),
         dyn_h15=pctv(hs[15][1]), dyn_h20=pctv(hs[20][1]), dyn_h40=pctv(hs[40][1]),
         dyn_ia=f2(max(ff[3], nf_[3])), dyn_ib=f2(max(ff[4], nf_[4])),
         dyn_dreq=f1(float(re.search(r"max dreq ([\d.]+)", dl).group(1))))
over = nf_[2] / 3500 - 1
if over > 0.10:
    N["dyn_nf_comment"] = ", outside the $\\pm10\\%$ band"
    N["dyn_concl"] = "The design therefore satisfies the current constraint, while the DC-link constraint of (17) requires power feed-forward or $H_\\mathrm{dc}\\ge15$~ms."
elif over > 0.08:
    N["dyn_nf_comment"] = ", at the edge of the $\\pm10\\%$ band, so that the DC-link constraint of (17) is almost active"
    N["dyn_concl"] = "The design therefore satisfies the current constraint, and the DC-link constraint requires either power feed-forward or $H_\\mathrm{dc}\\ge15$~ms for a margin; it would become binding for a faster load change, a smaller $H_\\mathrm{dc}$ or a smaller $\\kappa$."
else:
    N["dyn_nf_comment"] = ", inside the $\\pm10\\%$ band"
    N["dyn_concl"] = "The DC-link and current constraints of (17) are therefore not active for the proposed design; they would become active for a faster load change, a smaller $H_\\mathrm{dc}$ without feed-forward or a smaller $\\kappa$."
# agreement of the dynamic model with (15)
from rpc_sizing import rpc as _rpc
dd = np.load("results/dyn.npz"); a0 = int(dd["a"])
z = np.load("results/base_w000.npz"); Pz = z["P"].astype(float)[a0:a0 + 61]; Qz = z["Q"].astype(float)[a0:a0 + 61]
Pz[40:] -= 10.0
sxq, _ = _rpc.compensate(Pz, Qz, mpr["C"], mpr["eps"], 750.0)
tt = dd["t_True"]; sdyn = np.hypot(dd["Pa_True"], dd["Qa_True"])
ts = np.array([k + f for k in range(60) for f in (0.3, 0.6, 0.9) if not (38.9 < k + f < 40.2)])
idx = [int(np.argmin(np.abs(tt - x))) for x in ts]
Pi = np.interp(tt[idx], np.arange(61), Pz); Qi = np.interp(tt[idx], np.arange(61), Qz)
sxi, _ = _rpc.compensate(Pi, Qi, mpr["C"], mpr["eps"], 750.0)
err = np.abs(sdyn[idx] - sxi)
N["dyn_agree"] = f"{max(err.max(), 0.01):.2f}"

# exact network
r = json.load(open("results/netval_0_20.json"))
g = lambda n, k: np.array([x[n][k] for x in r])
cm = [x["cmin"] for x in r if "cmin" in x]
N.update(nx_inst=f1(100 * np.median(g("none", "relerr_inst"))),
         nx_unc_rel=f1(100 * np.mean(g("none", "p95_ex") / g("none", "p95_apx") - 1)),
         nx_unc_apx=f2(g("none", "p95_apx").mean()), nx_unc_ex=f2(g("none", "p95_ex").mean()),
         nx_p95_ex=f2(g("p95", "p95_ex").mean()), nx_p95_fail=str(int(np.sum(g("p95", "p95_ex") > 2))),
         nx_prop_ex=f2(g("prop", "p95_ex").mean()), nx_prop_ok=str(int(np.sum(g("prop", "p95_ex") <= 2))),
         nx_c19=f2(np.mean([x["ex19"] for x in cm])), nx_c2=f2(np.mean([x["apx2"] for x in cm])),
         nx_c1ex=f2(np.mean([x["ex1"] for x in cm])), nx_c1apx=f2(np.mean([x["apx1"] for x in cm])),
         nx_margin=f1(2 - g("prop", "p95_ex").mean()))

# short-term
st = json.load(open("results/shortterm_summary.json"))
N.update(st_p99c=f2(st["None"]["conv_p99"]), st_p99p=f2(st["None"]["p99"]),
         st_c225=f1(st["2.25"]["conv_C"]), st_c21=f1(st["2.1"]["conv_C"]), st_c20=f1(st["2.0"]["conv_C"]),
         st_p225=f1(st["2.25"]["C"]), st_p21=f1(st["2.1"]["C"]), st_p20=f1(st["2.0"]["C"]),
         st_e225=f"{st['2.25']['eps']:g}", st_e21=f"{st['2.1']['eps']:g}", st_e20=f"{st['2.0']['eps']:g}",
         st_Jp_lo=f0(min(st[k]["J"] for k in ["2.25", "2.1", "2.0"])), st_Jp_hi=f0(max(st[k]["J"] for k in ["2.25", "2.1", "2.0"])),
         st_Jc_lo=f0(min(st[k]["conv_J"] for k in ["2.25", "2.1", "2.0"])), st_Jc_hi=f0(max(st[k]["conv_J"] for k in ["2.25", "2.1", "2.0"])))

# paired
pj = json.load(open("results/paired.json"))
N.update(pair_mean=f1(pj["p95"]["mean"]), pair_ci=f1(pj["p95"]["ci"]), pair_rel=f1(pj["p95"]["rel"]),
         pair_share=f0(100 * pj["p95"]["share_cheaper"]), pair_viol_share=f0(100 * pj["Eviol"]["share_lower"]))

# suburban
sb = load("suburban", "results_sub")
N.update(sb_meanP=f1(np.mean([w["meanP"] for w in sb["weeks"]])), sb_peak=f1(np.mean([w["peakS"] for w in sb["weeks"]])),
         sb_neg=f1(100 * np.mean([w["regen_share"] for w in sb["weeks"]])))
tsb = []
for S in [750, 1000, 1500]:
    m = methods(sb, S); unc = np.mean([w["p95_unc"][str(S)] for w in sb["weeks"]])
    tsb.append(f"{S} & {unc:.2f} & {m['full']['C']:.1f} & {m['peak']['C']:.1f} & {m['p95']['C']:.2f} & {m['proposed']['C']:.2f} & {m['proposed']['eps']:.2f} & "
               f"{m['p95']['Eviol']:.1f} / {m['proposed']['Eviol']:.1f} & {m['p95']['J']:.0f} / {m['proposed']['J']:.0f} & {100*(1-m['proposed']['J']/m['p95']['J']):.0f}\\\\")
    if S == 750:
        N.update(sb_unc=f2(unc), sb_peakC=f1(m["peak"]["C"]), sb_p95=f1(m["p95"]["C"]), sb_prop=f1(m["proposed"]["C"]),
                 sb_eps=f"{m['proposed']['eps']:g}", sb_Jred=pct(m["proposed"]["J"], m["p95"]["J"]),
                 sb_viol_c=f1(m["p95"]["Eviol"]), sb_viol_p=f1(m["proposed"]["Eviol"]),
                 sb_redpk_p95=pct(m["p95"]["C"], m["peak"]["C"]), sb_redpk_prop=pct(m["proposed"]["C"], m["peak"]["C"]))
N["TABLE_SUB"] = "\n".join(tsb)
N["sb_red_lo"] = f0(min(100*(1-methods(sb,S)['proposed']['J']/methods(sb,S)['p95']['J']) for S in [750,1000,1500]))
N["sb_red_hi"] = f0(max(100*(1-methods(sb,S)['proposed']['J']/methods(sb,S)['p95']['J']) for S in [750,1000,1500]))

# MMC comparison
N.update(mmc_stage=f1(float(N["peakSq"])), mmc_tot=f0(2 * float(N["peakSq"])),
         rpc_full2=f1(2 * mf["C"]), rpc_peak2=f1(2 * mp["C"]), rpc_p952=f1(2 * mc["C"]), rpc_prop2=f1(2 * mpr["C"]),
         loss_prop=f2(mpr["Eloss"] / 1000), loss_p95=f2(mc["Eloss"] / 1000), mmc_loss=f1(0.02 * meanP * 8760 / 1000))

# train runs of Fig. B
p = base_params(); rng = np.random.default_rng(7)
P1 = tr.run_train(p, rng, p["_grade_edges"], p["_grades"], stop=False)
P2 = tr.run_train(p, rng, p["_grade_edges"], p["_grades"], stop=True, restriction=(6000.0, 10000.0, 200 / 3.6))
N.update(run_lo=f1(P1.min()), run_hi=f1(P1.max()), run_reg=f1(-P2.min()))

json.dump(N, open("results/numbers.json", "w"), indent=1)
for k, v in N.items():
    if not k.startswith("TABLE"):
        print(k, "=", v)
