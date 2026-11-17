import json
D = "/home/claude/subtasks/5/"
S = json.load(open(D + "results_saa_summary.json"))
B, U = S["base"], S["suburban"]
tb = open(D + "table_base.tex").read().rstrip("\n")
ts = open(D + "table_suburban.tex").read().rstrip("\n")
f1 = lambda x: f"{x:.1f}"
f2 = lambda x: f"{x:.2f}"
f0 = lambda x: f"{x:.0f}"
p = lambda x: f"{100*x:.0f}"
b1, b2, b5, bs = B["SAA_1s"]["0.01"], B["SAA_1s"]["0.02"], B["SAA_1s"]["0.05"], B["SAA_1s_alpha_star"]
u1, u2, u5, us = U["SAA_1s"]["0.01"], U["SAA_1s"]["0.02"], U["SAA_1s"]["0.05"], U["SAA_1s_alpha_star"]
bt1, bt2, bt5 = (B["SAA_10min"][k] for k in ["0.01", "0.02", "0.05"])
ut1, ut2, ut5 = (U["SAA_10min"][k] for k in ["0.01", "0.02", "0.05"])
bp, up, bc, uc = B["proposed"], U["proposed"], B["percentile"], U["percentile"]
rb, ru = B["relative_to_proposed"], U["relative_to_proposed"]
pw = B["per_week_C_alpha"]["0.01"]
Nm = B["SAA_1s"]["0.01"]  # placeholder to keep names short

txt = rf"""% =====================================================================
% INSERT 1 -- new subsubsection in the Results subsection of the sizing section, after the
% paragraph that discusses Table~\ref{{tA}} (before Fig.~\ref{{fC}}) or after the Fig.~\ref{{f9}} paragraph.
% Requires the new references q1--q3 (refs.tex); n3 is already in the list.
% =====================================================================
\subsubsection*{{Comparison with chance-constrained (sample-average) sizing}}

Chance-constrained formulations are the established probabilistic tool for sizing railway compensators and storage under uncertain traction load. Chen \textit{{et al}}~\cite{{n3}} size power flow controllers and storage with chance constraints on the power balance, scenarios from a Gaussian mixture model, and a dynamic VUF limit whose confidence level is chosen so that the 95\% value and the daily maximum of the VUF distribution stay within 2\% and 4\%; Liu \textit{{et al}}~\cite{{q1}} configure storage at the point of common coupling with a distributionally robust chance constraint reformulated by the conditional value-at-risk. The sample-average approximation (SAA) replaces the probability by the empirical frequency over a sample and is the standard solution scheme for such problems~\cite{{q2,q3}}. None of these studies sizes a Scott-transformer RPC against the 10-min criterion of the grid code, so no published rule can be applied unchanged. We therefore implemented the rule that these formulations imply when they are applied to the present problem, and evaluated it with the same weeks, cost model (16) and criteria as Table~\ref{{tA}}.

\textit{{SAA-1s (instantaneous chance constraint).}} For the compensation law (15) with $\varepsilon_u=2\%$ an instant is compliant if $\kappa\,C\,U_i\ge r_i$, with $r_i=\max(0,|\underline{{S}}_{{L,i}}|-0.02\,S_\mathrm{{sc}})/2$ the requested transfer. The rating is the smallest $C$ for which the empirical frequency of violation over the pooled 1-s samples of all $N$ stored weeks does not exceed $\alpha$,
\begin{{equation}}
\min_{{C}}\; w_1C+w_2E_\mathrm{{loss}}(C)\quad\text{{s.t.}}\quad\frac{{1}}{{N}}\sum_{{i=1}}^{{N}}\mathbf{{1}}\{{\mathrm{{VUF}}_{{\mathrm{{inst}},i}}(C,\varepsilon_u)>2\%\}}\le\alpha ,
\label{{eq:saa}}
\end{{equation}}
that is, the $(1-\alpha)$ quantile of $r_i/(\kappa U_i)$, with $U_i$ the busbar voltage with the transfer applied. It was computed by bisection on $C$ with the capacity-constrained law (15) itself ($N=36.3\\times10^{{6}}$ samples). The cost increases with $C$ (the capital term, 30.6~kUSD/MVA, outweighs the loss term), so the optimum is the smallest feasible rating; a check with ratings up to 50\% above it confirmed this. A second variant treats $(\varepsilon_u,C)$ as joint decision variables of (\ref{{eq:saa}}). Because the violations occur when the converter saturates, the feasible rating does not depend on $\varepsilon_u$ (changes below 0.01~MVA), the losses increase when $\varepsilon_u$ is reduced, and the joint problem returns $\varepsilon_u=2\%$ and the same rating; it is therefore not listed separately. Finally, \textit{{SAA-10min}} applies the same joint SAA problem to the pooled 10-min values, $\varepsilon_u\in\{{0,0.5,1,1.5,2\}}\%$, with the constraint $\Pr\{{\mathrm{{VUF}}_\mathrm{{10\,min}}>2\%\}}\le\alpha_{{10}}$. This variant is not taken from the literature; it shows what the SAA machinery achieves when it is given the threshold law and the grid-code metric of this paper.

\begin{{table}}[htbp]
\caption{{\label{{tS}}Chance-constrained (SAA) baselines against percentile sizing and the proposed design ($S_\mathrm{{sc}}=750$~MVA, 60 weeks, same cost model and criteria as Table~\ref{{tA}}). SAA-1s: instantaneous chance constraint with level $\alpha$ and $\varepsilon_u=2\%$; $\alpha^\star$ is the largest level for which the P95 criterion holds in at least 95\% of the weeks; SAA-10min: joint $(\varepsilon_u,C)$ chance constraint on the pooled 10-min values.}}
\centering
\begin{{adjustbox}}{{max width=\linewidth}}
\begin{{tabular}}{{@{{}}lrrrrrrr}}
\hline
{tb}
\hline
\end{{tabular}}
\end{{adjustbox}}
\end{{table}}

Table~\ref{{tS}} and Fig.~\ref{{fS}} show that an instantaneous chance constraint does not by itself deliver the grid-code criterion. With the customary level $\alpha=5\%$ the rating is only {f1(b5['C'])}~MVA and none of the 60 weeks meets the 10-min P95 limit (mean P95 {f2(b5['p95_mean'])}\%, {f1(100*b5['share'])}\% of the 10-min values above 2\%, $E_\mathrm{{viol}}={f1(b5['Eviol'])}$~\%$\cdot$h/yr); its capital and loss cost is the lowest in the table ({f0(b5['J_caploss'])}~kUSD/yr), but the exceedance penalty raises $J$ to {f0(b5['J'])}~kUSD/yr. On the levels tested the criterion is met in all weeks for $\alpha\le1\%$ (rating {f1(b1['C'])}~MVA, {f0(rb['SAA_1s_1pct']['dC_pct'])}\% above the proposed design, and $J={f0(b1['J'])}$~kUSD/yr, {f0(rb['SAA_1s_1pct']['dJ_pct'])}\% above the proposed design, essentially the cost of percentile sizing with optimised rating, {f0(B['percentile_Copt']['J'])}~kUSD/yr). The calibrated level $\alpha^\star={100*bs['alpha']:.1f}\%$ gives {f1(bs['C'])}~MVA and $J={f0(bs['J'])}$~kUSD/yr, i.e.\ the SAA rule reproduces percentile sizing (12) ({f1(bc['C'])}~MVA, {f0(bc['J'])}~kUSD/yr) and is {f0(rb['SAA_1s_alpha_star']['dJ_pct'])}\% more expensive than the proposed design. The level is not transferable between systems: on the suburban line (Table~\ref{{tSb}}) $\alpha=5\%$ is again too lax ({p(u5['comply'])}\% of the weeks comply), but $\alpha=2\%$ already complies in all weeks ({f1(u2['C'])}~MVA, $J={f0(u2['J'])}$~kUSD/yr), and $\alpha^\star={100*us['alpha']:.1f}\%$ (versus {100*bs['alpha']:.1f}\% for the high-speed line), so $\alpha$ must itself be calibrated against the 10-min criterion on the simulated weeks. Fig.~\ref{{fS}}(a) shows the sharp transition and Fig.~\ref{{fS}}(b) the cost minimum at the smallest compliant level of the grid (1\% for the high-speed and 2\% for the suburban line). The proposed design leaves {f1(100*bp['inst_share'])}\% of the 1-s values above 2\%, more than any compliant SAA-1s design, because the grid code aggregates the values over 10~min; an instantaneous constraint is therefore conservative where the 10-min rms is the binding quantity and cannot exploit the threshold $\varepsilon_u$, whose effect acts through the rms of the windows (Fig.~\ref{{f9}}(a)).

\begin{{figure}}[htbp]
\centering
\includegraphics[width=\textwidth]{{figS_saa_alpha.pdf}}
\caption{{\label{{fS}}SAA-1s sizing ($\varepsilon_u=2\%$) versus the chance-constraint level $\alpha$: (a) share of the weeks meeting the P95 criterion (stars: calibrated level $\alpha^\star$); (b) expected annual cost $J$ (dashed: proposed design, dotted: percentile sizing (12); blue: high-speed line, orange: suburban line).}}
\end{{figure}}

When the chance constraint is placed on the 10-min values and $\varepsilon_u$ is a decision variable (SAA-10min), the outcome depends on the level. The pooled analogue of the grid-code criterion, $\alpha_{{10}}=5\%$, selects $\varepsilon_u={bt5['eps']:g}\%$ and {f1(bt5['C'])}~MVA but is met in only {p(bt5['comply'])}\% of the weeks, since a pooled quantile gives no margin between weeks. With $\alpha_{{10}}=2\%$ the design ($\varepsilon_u={bt2['eps']:g}\%$, {f1(bt2['C'])}~MVA) complies in all weeks at $J={f0(bt2['J'])}$~kUSD/yr ({rb['SAA_10min_2pct']['dJ_pct']:.1f}\% above the proposed design), and with $\alpha_{{10}}=1\%$ it selects $\varepsilon_u={bt1['eps']:g}\%$ and {f1(bt1['C'])}~MVA at $J={f0(bt1['J'])}$~kUSD/yr, practically the proposed design ({f1(bp['C'])}~MVA, $\varepsilon_u={bp['eps']:g}\%$, {f0(bp['J'])}~kUSD/yr). On the suburban line the same variant is {ru['SAA_10min_1pct']['dJ_pct']:.1f}\% (at $\alpha_{{10}}=1\%$) and {ru['SAA_10min_2pct']['dJ_pct']:.1f}\% (at $\alpha_{{10}}=2\%$) more expensive than the proposed design. This agreement indicates that the saving of the proposed design does not come from the solution technique but from the formulation: the 10-min rms aggregation together with the threshold law, and the cost (16) that prices the residual exceedance. The weekly-quantile rule of the solution procedure reaches this design without tuning a pooled level, because its margin is the criterion itself (95\% of the weeks), whereas $\alpha_{{10}}$ must be chosen between 2\% and 5\% in the SAA formulation. The SAA ratings are also statistically stable: the weekly $\alpha=1\%$ ratings have a standard deviation of {f2(pw['sd'])}~MVA about their mean {f2(pw['mean'])}~MVA, so the pooled sample of $N=36.3\\times10^{{6}}$ strongly autocorrelated 1-s values is large enough, but a single week would not be.

\begin{{table}}[htbp]
\caption{{\label{{tSb}}Chance-constrained (SAA) baselines for the suburban line ($S_\mathrm{{sc}}=750$~MVA, 40 weeks; notation as in Table~\ref{{tS}}).}}
\centering
\begin{{adjustbox}}{{max width=\linewidth}}
\begin{{tabular}}{{@{{}}lrrrrrrr}}
\hline
{ts}
\hline
\end{{tabular}}
\end{{adjustbox}}
\end{{table}}

% =====================================================================
% INSERT 2 -- one sentence for the Introduction / section 2 (end of the paragraph
% that follows Table~\ref{{t0}}):
% =====================================================================
Chance-constrained formulations of storage and power flow controller capacity exist for railway supply systems~\cite{{n3,q1}}, but they constrain instantaneous or dynamic unbalance values (or the power balance); in the Results subsection an SAA sizing rule of this type is implemented as a baseline and compared with the proposed design on the 10-min criterion.

% =====================================================================
% INSERT 3 -- Table t0, replace the content of the n3 row's 4th column:
%   `Chance constraint on dynamic VU'  ->
%   `Chance constraint on power balance; dynamic VU limit at a selected confidence level'
% and (optional) add the row
%   Liu \textit{{et al}}~\cite{{q1}} & Storage at the PCC, mountainous railway & Uncertain renewable and traction load & Imbalance penalty and voltage deviation in the cost & Distributionally robust chance constraint, CVaR (MILP) & Linearised power flow\\
% =====================================================================
"""
txt = txt.replace("36.3\\times10^{{6}}", "36.3\\times10^{6}")
open(D + "section.tex", "w").write(txt)
