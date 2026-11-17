"""Writes results/paper_loading.tex (tables + paragraph, literal numbers taken from the JSON results)."""
import json
R = "/home/claude/subtasks4/2/results"
p = json.load(open(f"{R}/pooled_summary.json")); rs = json.load(open(f"{R}/rating_sens.json"))
sc = json.load(open(f"{R}/rating_scaling.json")); th = json.load(open(f"{R}/thermal.json")); tl = json.load(open(f"{R}/thermal_low.json"))
ex = json.load(open(f"{R}/exact_limit_check.json"))
aS, aI, aI20, bI = p["alpha_S_40"], p["alpha_I_40"], p["alpha_I_20"], p["beta_I_40"]
ra, rb, rbo = p["rpc_a"], p["rpc_b"], p["rpc_bo"]
f3 = lambda x: f"{x:.3f}"; f2 = lambda x: f"{x:.2f}"; f1 = lambda x: f"{x:.1f}"
def hh(d): return f"{d['hours']:.2f}" if d["hours"] >= 0.005 else ("0" if d["seconds"] == 0 else f"{d['seconds']}~s")
def dur(d):
    if d["seconds"] == 0: return "0"
    return f"{d['hours']:.2f}~h ({d['share_pct']:.3f}\\%)" if d["hours"] >= 0.05 else f"{d['seconds']}~s"
def mx(key, sr, amb, cool="ONAN", f="th_max"):
    src = th if f"{cool}|{sr}|{amb}" in th else tl
    return max(x[f] for x in src[f"{cool}|{sr}|{amb}"])
T = []
T.append(r"""\begin{table}[htbp]
\caption{\label{tleg}Loading of the Scott legs in the 60 high-speed design weeks (exact phasor model, $C=11.27$~MVA per leg, $\varepsilon_u=1\%$, $S_\mathrm{sc}=750$~MVA, 36.3 million 1-s values; $I_N$ is the rated current of the leg at 27.5~kV). Leg $\beta$ carries only the transferred power.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}lcccc@{}}
\hline
 & \multicolumn{3}{c}{Leg $\alpha$} & Leg $\beta$\\
Quantity & $S/40$~MVA & $I/I_N$, 40~MVA & $I/I_N$, 20~MVA & $I/I_N$, 40~MVA\\
\hline""")
T.append(f"Maximum (pu) & {f3(aS['max'])} & {f3(aI['max'])} & {f3(aI20['max'])} & {f3(bI['max'])}\\\\")
T.append(f"P99 / P99.9 of all 1-s values (pu) & {f3(aS['p99'])} / {f3(aS['p999'])} & {f3(aI['p99'])} / {f3(aI['p999'])} & {f3(aI20['p99'])} / {f3(aI20['p999'])} & {f3(bI['p99'])} / {f3(bI['p999'])}\\\\")
for t in ("1.0", "1.2", "1.5", "2.0"):
    T.append(f"Time above {t}~pu & {dur(aS['thr'+t])} & {dur(aI['thr'+t])} & {dur(aI20['thr'+t])} & {dur(bI['thr'+t])}\\\\")
T.append(f"Episodes above 1.0~pu (longest, s) & {aS['thr1.0']['episodes']} ({aS['thr1.0']['longest_s']}) & {aI['thr1.0']['episodes']} ({aI['thr1.0']['longest_s']}) & {aI20['thr1.0']['episodes']} ({aI20['thr1.0']['longest_s']}) & 0\\\\")
T.append(f"Maximum 10-min rms (pu) & {f3(aS['rms10_max'])} & {f3(aI['rms10_max'])} & {f3(aI20['rms10_max'])} & {f3(bI['rms10_max'])}\\\\")
T.append(f"Maximum 1-h rms (pu) & {f3(aS['rms60_max'])} & {f3(aI['rms60_max'])} & {f3(aI20['rms60_max'])} & {f3(bI['rms60_max'])}\\\\")
T.append(r"""\hline
\end{tabular}
\end{adjustbox}
\end{table}
""")
T.append(r"""\begin{table}[htbp]
\caption{\label{trpcI}Current of the RPC legs relative to the rated current $C/27.5$~kV in the same 60 weeks and the same model. The $\alpha$ converter carries $|\underline{s}_x|/U_\alpha$; the $\beta$ converter carries the transfer plus the losses of both legs (loss model of Table~\ref{t11}), or of its own leg only. The power for the DC-voltage control is not part of the phasor model.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}lccc@{}}
\hline
Quantity & Leg $\alpha$ & Leg $\beta$ (losses of both legs) & Leg $\beta$ (own losses)\\
\hline""")
T.append(f"Maximum (pu) & {f3(ra['max'])} & {f3(rb['max'])} & {f3(rbo['max'])}\\\\")
T.append(f"P99.9 of all 1-s values (pu) & {f3(ra['p999'])} & {f3(rb['p999'])} & {f3(rbo['p999'])}\\\\")
T.append(f"Seconds above 1.00~pu (episodes, longest s) & {ra['gt1.0']['seconds']} ({ra['gt1.0']['episodes']}, {ra['gt1.0']['longest_s']}) & 0 & 0\\\\")
T.append(f"Seconds above 1.02~pu (episodes, longest s) & {ra['gt1.02']['seconds']} ({ra['gt1.02']['episodes']}, {ra['gt1.02']['longest_s']}) & 0 & 0\\\\")
T.append(f"Maximum 10-min rms (pu) & {f3(ra['rms10_max'])} & {f3(rb['rms10_max'])} & {f3(rbo['rms10_max'])}\\\\")
T.append(f"Maximum 1-h rms (pu) & {f3(ra['rms60_max'])} & {f3(rb['rms60_max'])} & {f3(rbo['rms60_max'])}\\\\")
T.append(r"""\hline
\end{tabular}
\end{adjustbox}
\end{table}
""")
T.append(r"""\begin{table}[htbp]
\caption{\label{trat}Influence of the rating $S_N$ of the Scott legs ($u_k=10.5\%$ of $S_N$, $X/R=30$) at the fixed RPC design $C=11.27$~MVA, $\varepsilon_u=1\%$. Last two columns: exact-model P95 of the 10-min VUF over the 60 weeks (the full network solution was repeated with the impedance of each rating). Loading of leg $\alpha$ obtained by scaling the 40~MVA currents.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}rccccccc@{}}
\hline
$S_N$ (MVA) & $u_k$ on 40~MVA (\%) & $\max I/I_N$ & max 10-min rms & max 1-h rms & hours $>1.5$~pu & mean / max weekly P95 (\%) & weeks $>2\%$\\
\hline""")
for s in ("20.0", "25.0", "31.5", "40.0", "50.0", "63.0"):
    a = sc[s]; r = rs[s]; S = float(s)
    T.append(f"{S:g} & {10.5*40/S:.1f} & {f2(a['max'])} & {f2(a['rms10'])} & {f2(a['rms60'])} & {a['hours']['1.5']:.2f} & {r['p95_mean']:.2f} / {r['p95_max']:.2f} & {r['weeks_viol']}\\\\")
T.append(r"""\hline
\end{tabular}
\end{adjustbox}
\end{table}
""")
open(f"{R}/paper_tables.tex", "w").write("\n".join(T))

tx = rf"""% ---- insert at the end of section 4.6 (before \subsection{{Second case study: suburban 25~kV line}}) ----
\paragraph{{Loading of the Scott transformer and of the RPC legs.}} The Scott transformer has two ratings in this paper: $2\times20$~MVA (20~MVA per leg) in the time-domain model of section~3 (Table~\ref{{t1}}), which simulates single trains (3 and 8~MW traction power), and 40~MVA per leg in the sizing model (Table~\ref{{t11}}), where it sets the leakage impedance of the feeders. The sizing case is a substation whose load reaches 68.3~MVA, so the first value is not its rating. To check the 40~MVA, the exact phasor model of section~4.6 was evaluated for every second of the 60 design weeks at the final design ($C=11.27$~MVA, $\varepsilon_u=1\%$, $S_\mathrm{{sc}}=750$~MVA; Table~\ref{{tleg}}). Leg $\beta$ carries only the transferred power ($\le{bI['max']:.2f}$~pu), and leg $\alpha$ carries $\underline{{S}}_L-\underline{{s}}_x$: up to {aS['max']*40:.1f}~MVA ({aS['max']:.2f}~pu), or {aI['max']:.2f}~$I_N$ in current because the feeder voltage falls to {p['Ua_min']:.3f}~pu. At the 65.8~MVA load of Table~\ref{{t10}} (the 57th of the 60 weekly peaks, week 15) leg $\alpha$ carries 55.4~MVA ($1.38$~pu, $1.53\,I_N$), because the RPC takes $|\underline{{s}}_x|=10.4$~MVA, in agreement with $S_L-C\approx55$~MVA from (15). The current exceeds $I_N$ for {aI['thr1.0']['hours']:.1f}~h in the 60 weeks ({aI['thr1.0']['share_pct']:.2f}\% of the time; {aI['thr1.0']['episodes']} episodes, the longest {aI['thr1.0']['longest_s']}~s), exceeds $1.5\,I_N$ for {aI['thr1.5']['seconds']}~s in {aI['thr1.5']['episodes']} episodes (longest {aI['thr1.5']['longest_s']}~s) and never reaches $2\,I_N$; the 10-min and 1-h rms values are at most {aI['rms10_max']:.2f} and {aI['rms60_max']:.2f}~$I_N$. A leg of 20~MVA would reach {aI20['max']:.1f}~$I_N$ and exceed $I_N$ for {aI20['thr1.0']['share_pct']:.1f}\% of the time.

The thermal margin was checked with the difference equations of the loading guide IEC 60076-7~\cite{{iec60076-7}} and its generic ONAN parameters (annex~E; not heat-run data of a transformer), driven by the one-second current: the hot-spot temperature reaches at most {mx('', '40.0', '20.0'):.0f}~$^\circ$C at 20~$^\circ$C and {mx('', '40.0', '40.0'):.0f}~$^\circ$C at 40~$^\circ$C ambient, against 120~$^\circ$C for normal cyclic loading in that guide, and the same model stays below 120~$^\circ$C down to about 21~MVA per leg at 40~$^\circ$C ({mx('', '22.5', '40.0'):.0f}~$^\circ$C at 22.5~MVA, {mx('', '20.0', '40.0'):.0f}~$^\circ$C at 20~MVA). Only the current peaks are close to the limits of the guide: the current limits of 1.5~pu (medium power) and 1.3~pu (large power transformers) would need $40\cdot{aI['max']:.2f}/1.5=43$ and 50~MVA if applied strictly to one-second peaks. The standard for fixed traction transformers, EN~50329~\cite{{en50329}}, specifies the loading by a duty class or load cycle and limits the occasional hot-spot temperature of oil-immersed transformers to below 140~$^\circ$C, so the duty class for peaks of this kind has to be agreed with the manufacturer. The 40~MVA is adequate as the continuous rating and as the impedance base of the sizing case. The RPC legs (Table~\ref{{trpcI}}) stay below their rated current on the $\beta$ side ({rb['max']:.3f}~pu including the losses of both legs). The $\alpha$ current exceeds it by at most {100*(ra['max']-1):.1f}\% in {ra['gt1.0']['seconds']}~s ({100*ra['gt1.0']['seconds']/p['n_seconds']:.3f}\% of the time), because the current limit of (15) uses an approximate busbar voltage; limiting $|\underline{{s}}_x|$ to $C\,U_\alpha$ with the exact voltage changes no weekly P95 by more than $3\times10^{{-5}}$ percentage points. The power for the DC-voltage control and the 100~Hz pulsation are not in the phasor model (they are treated in the DC-link analysis above). The design is not sensitive to the Scott rating: for 20 to 63~MVA at $u_k=10.5\%$ the weekly exact P95 at $C=11.27$~MVA stays between {rs['63.0']['p95_max']:.2f} and {rs['20.0']['p95_max']:.2f}\% and all 60 weeks comply (Table~\ref{{trat}}). The sizing is therefore not repeated for the 40~MVA leg, but it has to be repeated if a transformer of different impedance is specified.

% ---- bibliography entries (to be added; the edition read is IEC 60076-7:2005, check the current edition) ----
% \bibitem{{iec60076-7}} IEC 2005 \textit{{IEC 60076-7:2005 Power transformers -- Part 7: Loading guide for oil-immersed power transformers}} (Geneva: International Electrotechnical Commission)
% \bibitem{{en50329}} CENELEC 2010 \textit{{EN 50329:2003/A1:2010 Railway applications -- Fixed installations -- Traction transformers}} (Brussels: CENELEC)
% ---- Table 2 (label t1), row 'Scott transformer': append "; single-train scenarios, the substation of the sizing study (section 4) has 40~MVA per leg" ----
% ---- Table 11 (label t11), row 'Feeder alpha source': append " (loading: Tables~\\ref{{tleg}}--\\ref{{trat}})" ----
"""
open(f"{R}/paper_paragraph.tex", "w").write(tx)
print(tx[:200]); print(len(tx.split()))
