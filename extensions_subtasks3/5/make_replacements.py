"""Build replacements.md / replacements.json: exact OLD -> NEW pairs (OLD verified to occur exactly once in the target file).
All numbers inserted in NEW strings are taken from decomposition.json via <<path|fmt>> or <<abs:path|fmt>> tokens."""
import json, re, sys
D = json.load(open("/home/claude/subtasks3/5/decomposition.json"))
T = open("/home/claude/urt_v4/manuscript_template.tex").read()
OR2 = open("/home/claude/urt_v4/OR2.tex").read()
CL = open("/home/claude/urt_v4/cover_letter.tex").read()
FILES = {"manuscript_template.tex": T, "OR2.tex": OR2, "cover_letter.tex": CL}


def val(path):
    neg = path.startswith("abs:")
    path = path[4:] if neg else path
    cur = D
    for p in path.split("."):
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return abs(cur) if neg else cur


def fill(s):
    def rep(m):
        p, f = m.group(1).split("|")
        return format(val(p), f)
    return re.sub(r"<<([^<>]+)>>", rep, s)


R = []
def add(file, where, old, new, note=""):
    old = old
    new = fill(new)
    cnt = FILES[file].count(old)
    assert cnt == 1, (where, cnt)
    R.append(dict(id=len(R) + 1, file=file, where=where, old=old, new=new, note=note))


# ---------------------------------------------------------------- abstract
m = re.search(r"\\begin\{abstract\}\n(.*?)\n\\end\{abstract\}", T, re.S)
add("manuscript_template.tex", "Abstract (line 36, whole paragraph)", m.group(1), open("/home/claude/subtasks3/5/abstract_new.txt").read().strip(),
    "248 words (whitespace tokens, ~ counted as space, each {{key}} one token; script wc_abs.py)")

# ---------------------------------------------------------------- introduction
add("manuscript_template.tex", "Introduction, contribution 3 (no 15 % claim exists in the introduction; neutral clause added)",
    r"compared, on the same weeks, with full, peak and percentile sizing and with chance-constrained (sample-average) sizing;",
    r"compared, on the same weeks, with full, peak and percentile sizing and with chance-constrained (sample-average) sizing, reporting the annual objective together with its capital-plus-loss and exceedance parts;")

# ---------------------------------------------------------------- section 4.2 (definition of J)
add("manuscript_template.tex", "Section 4.2, after Eq. (16)",
    r"is a penalty that expresses how the network operator values residual exceedance. The values of $w_1$--$w_3$",
    r"is a penalty that expresses how the network operator values residual exceedance, so that $\bar J$ is a planning objective and not the monetary cost of the converter alone; the comparisons below therefore report $\bar J$ together with its capital-plus-loss part $w_1C+w_2\bar E_\mathrm{loss}$ and with $\bar E_\mathrm{viol}$. The values of $w_1$--$w_3$")

# ---------------------------------------------------------------- Table A caption + results paragraph (section 4.4)
add("manuscript_template.tex", "Table tA caption",
    r"\caption{\label{tA}Comparison of sizing methods ($S_\mathrm{sc}=750$~MVA, 60 simulated weeks, $\varepsilon_\mathrm{lim}=2\%$; VUF values and energies are means over the weeks).}",
    r"\caption{\label{tA}Comparison of sizing methods ($S_\mathrm{sc}=750$~MVA, 60 simulated weeks, $\varepsilon_\mathrm{lim}=2\%$; VUF values and energies are means over the weeks). $J$ is the annual objective (16), the sum of the three terms of the row above it.}")

add("manuscript_template.tex", "Section 4.4 (results), sentences on objective and 'C optimised' row",
    r"roughly halves the exceedance $E_\mathrm{viol}$ (ratio {{viol_ratio}}) and reduces the expected annual cost by {{Jred}}\%. The price is a larger processed energy ({{etr_prop}} instead of {{etr_p95}}~GWh/yr per leg) and {{lossinc}}\% higher losses. The row `percentile, $C$ optimised' keeps $\varepsilon_u=2\%$ and optimises only $C$ ({{Cco}}~MVA); it reaches {{Jco_vs_p95}} cost as (12), which shows that the saving comes from the threshold rather than from a different rating.",
    r"roughly halves the exceedance $E_\mathrm{viol}$ (ratio {{viol_ratio}}) and lowers the annual objective $\bar J$, which includes the priced exceedance, by {{Jred}}\% (<<abs:tA_prop_vs_p95.dJ|.1f>>~kUSD/yr; Table~\ref{tDec}). Capital plus losses fall by <<abs:tA_prop_vs_p95.dcaploss_pct|.1f>>\% (<<tA_prop_vs_p95.caploss_prop|.1f>> instead of <<tA_prop_vs_p95.caploss_base|.1f>>~kUSD/yr: capital $-$<<abs:tA_prop_vs_p95.dcap|.1f>>, losses $+$<<tA_prop_vs_p95.dloss|.1f>>~kUSD/yr), which is <<tA_prop_vs_p95.share_dJ_from_caploss_pct|.0f>>\% of the difference, and the priced exceedance by <<abs:tA_prop_vs_p95.dpen|.1f>>~kUSD/yr (<<tA_prop_vs_p95.share_dJ_from_penalty_pct|.0f>>\%). The price is a larger processed energy ({{etr_prop}} instead of {{etr_p95}}~GWh/yr per leg) and {{lossinc}}\% higher losses. The row `percentile, $C$ optimised' keeps $\varepsilon_u=2\%$ and optimises only $C$ ({{Cco}}~MVA); its objective is practically that of (12) (<<tA_prop_vs_p95_Copt.J_base|.0f>> against <<tA_prop_vs_p95.J_base|.0f>>~kUSD/yr), but it spends <<tA_p95Copt_vs_p95.dcaploss_pct|.1f>>\% more on capital and losses (<<tA_prop_vs_p95_Copt.caploss_base|.1f>> against <<tA_prop_vs_p95.caploss_base|.1f>>~kUSD/yr) to cut the exceedance by <<abs:tA_p95Copt_vs_p95.dEviol_pct|.0f>>\%, which shows that the saving comes from the threshold rather than from a different rating. Against this row the proposed design has a <<abs:tA_prop_vs_p95_Copt.dJ_pct|.1f>>\% lower objective, <<abs:tA_prop_vs_p95_Copt.dcaploss_pct|.1f>>\% lower capital plus losses and <<abs:tA_prop_vs_p95_Copt.dEviol_pct|.0f>>\% less exceedance.")

add("manuscript_template.tex", "Figure f9 caption", r"\caption{\label{f9}(a) Expected annual cost (bars) and ratings",
    r"\caption{\label{f9}(a) Expected annual objective $\bar J$ (bars) and ratings",
    "the bar chart inside fig10_sizing.pdf is an image; if its y-label says 'cost', relabel it 'annual objective J (kUSD/yr)'")

# ---------------------------------------------------------------- section 4.5
add("manuscript_template.tex", "Section 4.5, tCI paragraph",
    r"and the cost reduction of 14.9\% has the interval 14.4--15.4\%. For the suburban line the cost reduction (15.2\%, 13.5--16.6\%) is also significant, but the rating reduction (2.7\%, interval $-1.5$ to $+4.8$\%) is not.",
    r"and the reduction of the annual objective of 14.9\% has the interval 14.4--15.4\%; it combines <<abs:tA_prop_vs_p95.dcaploss_pct|.1f>>\% lower capital plus losses with <<abs:tA_prop_vs_p95.dEviol_pct|.1f>>\% lower exceedance (interval <<abs:tCI_bootstrap_of_split.high_speed_750.dEviol_pct.1|.1f>>--<<abs:tCI_bootstrap_of_split.high_speed_750.dEviol_pct.0|.1f>>\% when the weeks are resampled and the designs are kept). For the suburban line the reduction of the objective (15.2\%, 13.5--16.6\%) is also significant, but it is entirely due to the exceedance, which is <<abs:tSub_750_prop_vs_p95.dEviol_pct|.1f>>\% lower (<<abs:tCI_bootstrap_of_split.suburban_750.dEviol_pct.1|.1f>>--<<abs:tCI_bootstrap_of_split.suburban_750.dEviol_pct.0|.1f>>\%), whereas capital plus losses are <<tSub_750_prop_vs_p95.dcaploss_pct|.1f>>\% higher; the rating reduction (2.7\%, interval $-1.5$ to $+4.8$\%) is not significant.")

add("manuscript_template.tex", "Table tCI caption (start)", r"\caption{\label{tCI}95\% intervals of the design values and of the expected annual cost ($S_\mathrm{sc}=750$~MVA).",
    r"\caption{\label{tCI}95\% intervals of the design values and of the annual objective ($S_\mathrm{sc}=750$~MVA).")
add("manuscript_template.tex", "Table tCI caption (end)", r"design rule repeated in each resample.}",
    r"design rule repeated in each resample. $^\dagger$ Weeks resampled with the designs of the base case kept fixed (10\,000 resamples).}")

def row_pair(key_sign):
    pass

add("manuscript_template.tex", "Table tCI, high-speed block (replace 1 row by 3)",
    "Cost reduction (\\%) & 14.9 & -- & [14.4, 15.4]\\\\",
    "Objective reduction (\\%) & 14.9 & -- & [14.4, 15.4]\\\\\n"
    "Change of capital + loss part (\\%) & $-$<<abs:tA_prop_vs_p95.dcaploss_pct|.1f>> & -- & --\\\\\n"
    "Change of exceedance $E_\\mathrm{viol}$ (\\%) & $-$<<abs:tA_prop_vs_p95.dEviol_pct|.1f>> & -- & [$-$<<abs:tCI_bootstrap_of_split.high_speed_750.dEviol_pct.0|.1f>>, $-$<<abs:tCI_bootstrap_of_split.high_speed_750.dEviol_pct.1|.1f>>]$^\\dagger$\\\\")
add("manuscript_template.tex", "Table tCI, suburban block (replace 1 row by 3)",
    "Cost reduction (\\%) & 15.2 & -- & [13.5, 16.6]\\\\",
    "Objective reduction (\\%) & 15.2 & -- & [13.5, 16.6]\\\\\n"
    "Change of capital + loss part (\\%) & $+$<<tSub_750_prop_vs_p95.dcaploss_pct|.1f>> & -- & --\\\\\n"
    "Change of exceedance $E_\\mathrm{viol}$ (\\%) & $-$<<abs:tSub_750_prop_vs_p95.dEviol_pct|.1f>> & -- & [$-$<<abs:tCI_bootstrap_of_split.suburban_750.dEviol_pct.0|.1f>>, $-$<<abs:tCI_bootstrap_of_split.suburban_750.dEviol_pct.1|.1f>>]$^\\dagger$\\\\")

add("manuscript_template.tex", "Section 4.5, sensitivity paragraph (t8)",
    r"In all cases the proposed design lowers the expected annual cost relative to percentile sizing by {{s_dJlo}}--{{s_dJhi}}\%;",
    r"In all cases the proposed design lowers the annual objective relative to percentile sizing by {{s_dJlo}}--{{s_dJhi}}\%, with lower exceedance in 13 and lower capital plus losses in 11 of the 14 cases (by 1--15\%; in the three lightly loaded cases they are 10--78~kUSD/yr higher);",
    "13 of 14 / 11 of 14 / 10-78 kUSD/yr: counted in decomposition.log (t8_* entries and the base case); freq_x1.5 is the only case with higher exceedance (+20.6 %)")
add("manuscript_template.tex", "Table t8 header (2 lines)", r"Reduction vs & Cost\\", r"Reduction vs & Objective\\")
add("manuscript_template.tex", "Table t13 header", r"$J$ percentile (12) (kUSD/yr) & Cost reduction (\%)\\", r"$J$ percentile (12) (kUSD/yr) & Objective reduction (\%)\\")
add("manuscript_template.tex", "Section 4.5, t13 paragraph",
    r"and that the proposed design is {{w_red_lo}}--{{w_red_hi}}\% cheaper than percentile sizing for all tested weights.",
    r"and that the annual objective of the proposed design is {{w_red_lo}}--{{w_red_hi}}\% lower than that of percentile sizing for all tested weights. The composition of the reduction depends on the weights. Without a penalty, or with 0.5~kUSD/(\%$\cdot$h), the proposed design is much smaller (<<t13_w3_0.C_prop|.2f>>~MVA) and its capital plus losses are <<abs:t13_w3_0.dcaploss_pct|.1f>>\% lower than those of (12), but its exceedance is <<t13_w3_0.Eviol_prop|.1f>> instead of <<t13_w3_0.Eviol_base|.1f>>~\%$\cdot$h/yr, so that at $w_3=0$ the whole reduction is a saving of capital and losses. With 5~kUSD/(\%$\cdot$h) or a converter cost of 75~kUSD/MVA, capital plus losses are <<t13_w3_5.dcaploss_pct|.1f>>\% and <<t13_convcost_75.dcaploss_pct|.1f>>\% higher and the exceedance <<abs:t13_w3_5.dEviol_pct|.0f>>\% and <<abs:t13_convcost_75.dEviol_pct|.0f>>\% lower.")

# ---------------------------------------------------------------- Pareto
add("manuscript_template.tex", "Section 4.5, Pareto paragraph",
    r"the proposed design lies on the front, is 6.8\% cheaper in capital and loss cost than (12) and has 48\% less exceedance.",
    r"the proposed design lies on the front, is <<abs:tA_prop_vs_p95.dcaploss_pct|.1f>>\% cheaper in capital and loss cost than (12) and has <<abs:tA_prop_vs_p95.dEviol_pct|.0f>>\% less exceedance (approximation (8)). With the exact model in the loop (section~4.6) the proposed design lies again on the front of the 72 candidates, has the same capital and loss cost as the corrected percentile design (<<tEx_prop_vs_corrected.caploss_prop|.1f>> against <<tEx_prop_vs_corrected.caploss_base|.1f>>~kUSD/yr) and <<abs:tEx_prop_vs_corrected.dEviol_pct|.0f>>\% less exceedance, and is <<abs:tEx_prop_vs_corrected_Copt.dcaploss_pct|.1f>>\% cheaper in capital and loss cost and has <<abs:tEx_prop_vs_corrected_Copt.dEviol_pct|.0f>>\% less exceedance than the corrected design with optimised rating; both corrected designs are dominated.")

# ---------------------------------------------------------------- SAA
add("manuscript_template.tex", "Table tS, last row label", r"Expected annual cost $J$ (kUSD/yr) & 534 & 828", r"Annual objective $J$ (kUSD/yr) & 534 & 828")
add("manuscript_template.tex", "Section 4.5, SAA paragraph (alpha = 1 %)",
    r"(12.9~MVA, $J$ 17\% above the proposed design)",
    r"(12.9~MVA, $J$ 17\% above the proposed design: capital plus losses <<tS_SAA1s_1pct_vs_prop.base_excess_caploss_pct|.1f>>\% and exceedance <<tS_SAA1s_1pct_vs_prop.base_excess_Eviol_pct|.1f>>\% higher)")
add("manuscript_template.tex", "Section 4.5, SAA paragraph (last sentence)",
    r"The saving of the proposed design therefore comes from the formulation (10-min rms aggregation, threshold law and priced exceedance) rather than from the solution technique;",
    r"The saving of the proposed design therefore comes from the formulation (10-min rms aggregation, threshold law and priced exceedance) rather than from the solution technique (against (12) and the calibrated SAA-1s design, <<tA_prop_vs_p95.share_dJ_from_caploss_pct|.0f>>\% of the difference of $\bar J$ is capital and loss cost and <<tA_prop_vs_p95.share_dJ_from_penalty_pct|.0f>>\% exceedance);")

# ---------------------------------------------------------------- paired comparison
add("manuscript_template.tex", "Section 4.5, paired comparison (short-term/paired paragraph)",
    r"The weekly cost difference between the proposed design and percentile sizing is ${{pair_mean}}\pm{{pair_ci}}$~kUSD/yr (95\% confidence interval, ${{pair_rel}}\%$); the proposed design is cheaper in {{pair_share}}\% and has a lower exceedance in {{pair_viol_share}}\% of the 60 weeks",
    r"The weekly difference of the annual objective between the proposed design and percentile sizing is ${{pair_mean}}\pm{{pair_ci}}$~kUSD/yr (95\% confidence interval, ${{pair_rel}}\%$; mean split: capital $-$<<abs:tA_prop_vs_p95.dcap|.1f>>, losses $+$<<tA_prop_vs_p95.dloss|.1f>>, exceedance $-$<<abs:tA_prop_vs_p95.dpen|.1f>>~kUSD/yr); the objective is lower in {{pair_share}}\% and the exceedance in {{pair_viol_share}}\% of the 60 weeks")

# ---------------------------------------------------------------- Table tEx (whole environment) and text
m = re.search(r"\\begin\{table\}\[htbp\]\n\\caption\{\\label\{tEx\}.*?\\end\{table\}\n", T, re.S)
add("manuscript_template.tex", "Table tEx (whole environment)", m.group(0), open("/home/claude/subtasks3/5/table_tEx.tex").read(),
    "adds the row 'Percentile, corrected, C optimised' and the columns J_cap+J_loss and E_viol; 13 columns fit at 100 % scale in a 160 mm text width (tested)")

add("manuscript_template.tex", "Section 4.6, paragraph after Table tEx",
    r"The proposed design complies in all weeks (mean P95 1.46\%) and costs 489.3 instead of 576.0~kUSD/yr, i.e.\ 15.0\% less with a 4.7\% smaller rating; the saving is the same as with (8), so it does not come from the approximation (12.4\% against the corrected design with optimised rating). The paired weekly difference is $-86.7\pm4.2$~kUSD/yr, negative in all 60 weeks.",
    r"The proposed design complies in all weeks (mean P95 1.46\%), and its annual objective is 489.3 instead of 576.0~kUSD/yr, i.e.\ 15.0\% lower with a 4.7\% smaller rating. The reduction is the same as with (8), so it does not come from the approximation, but its composition differs (Table~\ref{tDec}): capital plus losses are practically equal (<<tEx_prop_vs_corrected.caploss_prop|.1f>> against <<tEx_prop_vs_corrected.caploss_base|.1f>>~kUSD/yr; capital $-$<<abs:tEx_prop_vs_corrected.dcap|.1f>>, losses $+$<<tEx_prop_vs_corrected.dloss|.1f>>~kUSD/yr), and the whole difference of <<abs:tEx_prop_vs_corrected.dJ|.1f>>~kUSD/yr is the priced exceedance (<<tEx_prop_vs_corrected.viol_prop|.1f>> instead of <<tEx_prop_vs_corrected.viol_base|.1f>>~kUSD/yr; $E_\mathrm{viol}$ <<tEx_prop_vs_corrected.Eviol_prop|.1f>> instead of <<tEx_prop_vs_corrected.Eviol_base|.1f>>~\%$\cdot$h/yr, <<abs:tEx_prop_vs_corrected.dEviol_pct|.1f>>\% less). With (8), <<tA_prop_vs_p95.share_dJ_from_caploss_pct|.0f>>\% of the difference was capital and loss cost. The advantage of the proposed design over the corrected percentile design is thus the lower exceedance in the 5\% of the time that the percentile criterion leaves free, and its size depends on the exceedance weight $w_3$ (Table~\ref{t13}). The corrected design with optimised rating (third row of Table~\ref{tEx}; $C=<<tEx_prop_vs_corrected_Copt.C_base|.2f>>$~MVA, $\varepsilon_u=1.9\%$) lowers its own objective to <<tEx_prop_vs_corrected_Copt.J_base|.1f>>~kUSD/yr by spending more on capital and losses (<<tEx_prop_vs_corrected_Copt.caploss_base|.1f>>~kUSD/yr) to reduce the exceedance (<<tEx_prop_vs_corrected_Copt.Eviol_base|.1f>>~\%$\cdot$h/yr); against it the proposed design has a <<abs:tEx_prop_vs_corrected_Copt.dJ_pct|.1f>>\% lower objective, <<abs:tEx_prop_vs_corrected_Copt.dcaploss_pct|.1f>>\% lower capital plus losses and <<abs:tEx_prop_vs_corrected_Copt.dEviol_pct|.0f>>\% less exceedance, and is thus better in both components (the ratings of both rows are the best of the eight grid values; a quadratic interpolation of $\bar J(C)$ suggests that a finer search would lower either objective by about 1~kUSD/yr). The paired weekly difference to the corrected percentile design is $-86.7\pm4.2$~kUSD/yr, negative in all 60 weeks.")

# TABLE tDec: insert before Certification paragraph
add("manuscript_template.tex", "Section 4.6, insert Table tDec before the Certification paragraph",
    r"\paragraph{Certification on independent weeks.}",
    open("/home/claude/subtasks3/5/table_tDec.tex").read().rstrip("\n") + "\n\n" + r"\paragraph{Certification on independent weeks.}",
    "new float; label tDec is referenced from sections 4.4, 4.5, 4.6")

# ---------------------------------------------------------------- window budget (main text)
add("manuscript_template.tex", "Section 4.6/4.7 window-budget paragraph (main text)",
    r"and lowers the expected cost from 454.6 to 433.1~kUSD/yr ($-4.7\%$, cheaper in all 60 weeks, Wilcoxon $p<10^{-10}$);",
    r"and lowers the annual objective from 454.6 to 433.1~kUSD/yr ($-4.7\%$, lower in all 60 weeks, Wilcoxon $p<10^{-10}$), through capital ($-$<<abs:tWB_causal_vs_prop15.dcap|.1f>>) and losses ($-$<<abs:tWB_causal_vs_prop15.dloss|.1f>>~kUSD/yr; capital plus losses $-$<<abs:tWB_causal_vs_prop15.dcaploss_pct|.1f>>\%) while the exceedance rises by <<tWB_causal_vs_prop15.dEviol_pct|.1f>>\%;")

# ---------------------------------------------------------------- suburban
add("manuscript_template.tex", "Section 4.8 (suburban) text",
    r"The proposed design lowers the expected annual cost by {{sb_Jred}}\% and the exceedance from {{sb_viol_c}} to {{sb_viol_p}}~\%$\cdot$h/yr; at 1000~MVA its rating is slightly larger than that of percentile sizing, but its cost is still lower because the exceedance is smaller, and at 1500~MVA no compensation is needed.",
    r"The proposed design lowers the annual objective by {{sb_Jred}}\% and the exceedance from {{sb_viol_c}} to {{sb_viol_p}}~\%$\cdot$h/yr. In contrast to the high-speed line, the reduction of the objective is entirely due to the exceedance term (<<tSub_750_prop_vs_p95.viol_prop|.1f>> instead of <<tSub_750_prop_vs_p95.viol_base|.1f>>~kUSD/yr): capital plus losses are <<tSub_750_prop_vs_p95.dcaploss_pct|.1f>>\% higher (<<tSub_750_prop_vs_p95.caploss_prop|.1f>> instead of <<tSub_750_prop_vs_p95.caploss_base|.1f>>~kUSD/yr; capital $-$<<abs:tSub_750_prop_vs_p95.dcap|.1f>>, losses $+$<<tSub_750_prop_vs_p95.dloss|.1f>>~kUSD/yr; Table~\ref{tDec}). Against percentile sizing with optimised rating (<<tSub_750_prop_vs_p95_Copt.C_base|.1f>>~MVA, <<tSub_750_prop_vs_p95_Copt.J_base|.1f>>~kUSD/yr) the objective is <<abs:tSub_750_prop_vs_p95_Copt.dJ_pct|.1f>>\% lower, with <<abs:tSub_750_prop_vs_p95_Copt.dcaploss_pct|.1f>>\% lower capital plus losses and <<abs:tSub_750_prop_vs_p95_Copt.dEviol_pct|.1f>>\% lower exceedance. At 1000~MVA the rating is slightly larger than that of percentile sizing, so that capital plus losses are <<tSub_1000_prop_vs_p95.dcaploss_pct|.0f>>\% higher (+<<tSub_1000_prop_vs_p95.dcaploss|.1f>>~kUSD/yr), but the objective is still <<abs:tSub_1000_prop_vs_p95.dJ_pct|.0f>>\% lower because the exceedance penalty falls by <<abs:tSub_1000_prop_vs_p95.dpen|.1f>>~kUSD/yr; at 1500~MVA no compensation is needed.")
add("manuscript_template.tex", "Table tSub caption", r"\caption{\label{tSub}Suburban case study (40 weeks): rating per leg and annual cost versus the short-circuit power}",
    r"\caption{\label{tSub}Suburban case study (40 weeks): rating per leg and annual objective versus the short-circuit power}")
add("manuscript_template.tex", "Table tSub header", r"& $J$ (12) / prop.\ (kUSD/yr) & Cost reduction (\%)\\", r"& $J$ (12) / prop.\ (kUSD/yr) & Objective reduction (\%)\\")

# ---------------------------------------------------------------- validity
add("manuscript_template.tex", "Section 4.9 'Validity of the sizing results'",
    r"The absolute ratings must be recomputed with line-specific planning data, whereas the comparison between the methods is made under identical assumptions.",
    r"The absolute ratings must be recomputed with line-specific planning data, whereas the comparison between the methods is made under identical assumptions. The size of the reduction of the annual objective also depends on the exceedance weight $w_3$ (Table~\ref{t13}): with the exact model in the loop the 15\% against corrected percentile sizing is entirely a reduction of the exceedance term, whereas the capital and loss cost of the two designs is equal (Table~\ref{tDec}). If exceedance is not priced, the design with the lowest capital plus losses that meets the criterion in 95\% of the weeks (<<exact_compliance_only.best_caploss_candidate.C|.2f>>~MVA, $\varepsilon_u=<<exact_compliance_only.best_caploss_candidate.eps|.0f>>\%$) costs <<exact_compliance_only.best_caploss_candidate.caploss|.1f>> instead of <<exact_compliance_only.corrected.caploss|.1f>>~kUSD/yr (<<abs:exact_compliance_only.dcaploss_pct_vs_corrected|.0f>>\% less) but leaves an exceedance of <<exact_compliance_only.Eviol_of_that_candidate|.0f>>~\%$\cdot$h/yr.")

# ---------------------------------------------------------------- conclusions
add("manuscript_template.tex", "Conclusions (1)",
    r"roughly halves the residual exceedance and lowers the expected annual cost by {{Jred}}\% (95\% interval 14.4--15.4\%; {{w_red_lo}}--{{w_red_hi}}\% over the tested cost weights), at about {{lossinc}}\% higher losses. For the suburban line the cost reduction is {{sb_Jred}}\%, whereas its rating reduction is not statistically significant with 40 weeks.",
    r"roughly halves the residual exceedance and lowers the annual objective, which includes the priced exceedance, by {{Jred}}\% (95\% interval 14.4--15.4\%; {{w_red_lo}}--{{w_red_hi}}\% over the tested cost weights): capital plus losses are <<abs:tA_prop_vs_p95.dcaploss_pct|.1f>>\% lower and the exceedance <<abs:tA_prop_vs_p95.dEviol_pct|.0f>>\% lower, at about {{lossinc}}\% higher losses. For the suburban line the objective is {{sb_Jred}}\% lower through a <<abs:tSub_750_prop_vs_p95.dEviol_pct|.0f>>\% lower exceedance, at <<tSub_750_prop_vs_p95.dcaploss_pct|.1f>>\% higher capital plus losses, whereas its rating reduction is not statistically significant with 40 weeks.")
add("manuscript_template.tex", "Conclusions (2)",
    r"the proposed rating is 11.27~MVA, still 15\% cheaper than corrected percentile sizing, and it violated the criterion",
    r"the proposed rating is 11.27~MVA and its annual objective is still 15\% lower than that of corrected percentile sizing under the assumed exceedance penalty (equal capital plus losses, <<abs:tEx_prop_vs_corrected.dEviol_pct|.0f>>\% lower exceedance; <<abs:tEx_prop_vs_corrected_Copt.dJ_pct|.0f>>\% lower than for the corrected design with optimised rating, with <<abs:tEx_prop_vs_corrected_Copt.dcaploss_pct|.1f>>\% lower capital plus losses), and it violated the criterion")
add("manuscript_template.tex", "Conclusions (3)",
    r"A causal window-budget controller lowers the cost by a further 4.7\% but hardly reduces the rating",
    r"A causal window-budget controller lowers the annual objective by a further 4.7\% (capital plus losses <<abs:tWB_causal_vs_prop15.dcaploss_pct|.1f>>\% lower, exceedance <<tWB_causal_vs_prop15.dEviol_pct|.1f>>\% higher) but hardly reduces the rating")

# ---------------------------------------------------------------- Online Resource 2
add("OR2.tex", "OR2, Table tSb last row label", r"Expected annual cost $J$ (kUSD/yr) & 426 & 471", r"Annual objective $J$ (kUSD/yr) & 426 & 471")
add("OR2.tex", "OR2, window budget, Results paragraph",
    r"The saving against conventional percentile sizing (12) is 19.0\%.",
    r"The reduction of the objective against conventional percentile sizing (12) is <<abs:tWB_causal_vs_p95.dJ_pct|.1f>>\% (capital plus losses <<abs:tWB_causal_vs_p95.dcaploss_pct|.1f>>\% lower, exceedance <<abs:tWB_causal_vs_p95.dEviol_pct|.0f>>\% lower); against the proposed design (15) it is made of capital and losses ($-$<<abs:tWB_causal_vs_prop15.dcaploss|.1f>>~kUSD/yr, <<abs:tWB_causal_vs_prop15.dcaploss_pct|.1f>>\%), the exceedance term being <<tWB_causal_vs_prop15.dpen|.1f>>~kUSD/yr higher.")

# ---------------------------------------------------------------- cover letter
add("cover_letter.tex", "Cover letter, paragraph 2",
    r"The joint choice lowers the expected annual cost by about 15\% relative to conventional percentile sizing in every simulated week.",
    r"The joint choice lowers the annual objective, which prices the residual unbalance exceedance, by about 15\% relative to conventional percentile sizing in every simulated week; with the exact network model in the loop the capital and loss cost of the two designs is equal and the reduction comes from a <<abs:tEx_prop_vs_corrected.dEviol_pct|.0f>>\% lower exceedance.")

json.dump(R, open("/home/claude/subtasks3/5/replacements.json", "w"), indent=1)
