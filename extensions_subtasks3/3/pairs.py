"""Exact old->new replacement pairs for part (a). Verified by check_pairs.py against
/home/claude/urt_v4/manuscript_template.tex (and cover_letter.tex, OR2.tex)."""
T = "manuscript_template.tex"
P = []
def add(pid, where, f, old, new, note=""):
    P.append(dict(id=pid, where=where, file=f, old=old, new=new, note=note))

add("A1", "Abstract", T,
    r"the constraints are the 95th-percentile criterion on 10-min VUF values in 95\% of the simulated weeks, the current rating and the DC-link voltage band.",
    r"the constraints are a reference percentile criterion (95th percentile of the 10-min VUF at most 2\%, a case-study assumption) that must hold in at least 95\% of the simulated weeks (a design confidence level chosen by the authors), the current rating and the DC-link voltage band.")
add("A2", "Abstract", T,
    r"percentile sizing at the limit fails once the VUF is computed",
    r"percentile sizing at the reference limit fails once the VUF is computed")
add("A3", "Abstract", T,
    r"violated the criterion in none of 90 independent certification weeks",
    r"violated the reference criterion in none of 90 independent certification weeks")
add("A4", "Introduction, Table 1 (row 'This paper')", T,
    r"95th percentile of 10-min VUF, met in $\ge95\%$ of weeks; optional 99th-percentile limit",
    r"95th percentile of 10-min VUF $\le2\%$ (reference limit), met in $\ge95\%$ of weeks (design confidence level); optional 99th-percentile limit")
add("A5", "Introduction, gap paragraph", T,
    r"rather than to the statistical criterion of the grid code, or the compensation law",
    r"rather than to a percentile criterion of the kind used in standards and grid codes, or the compensation law")
add("A6", "Introduction, gap paragraph", T,
    r"against the 95th-percentile VUF criterion of EN 50160~\cite{b31}, and the converter limits are checked.",
    r"against a 95th-percentile VUF criterion modelled on EN 50160~\cite{b31} and QCVN 26:2025/BCT~\cite{v2} with a reference limit of 2\%, and the converter limits are checked.")
add("A7", "Nomenclature", T,
    r"& & $\varepsilon_\mathrm{lim}$ & VUF limit (2\%)\\",
    r"& & $\varepsilon_\mathrm{lim}$ & VUF reference limit (2\%, study assumption)\\")
add("A8", "Section 2.3, assumption (iii)", T,
    r"(iii) no background unbalance, otherwise contributions have to be combined, e.g.\ by the summation law of IEC TR 61000-3-13~\cite{b32};",
    r"(iii) no background unbalance, otherwise contributions have to be combined, e.g.\ by the summation law of IEC TR 61000-3-13~\cite{b32} (the effect of a pre-existing PCC unbalance on the design is quantified in section~4.5);")
add("A9", "Section 3.4.1", T,
    r"With the 2\% VUF limit of EN 50160~\cite{b31} (IEC TR 61000-3-13~\cite{b32} recommends lower planning levels), (8) allows",
    r"With the reference limit of 2\% (section~2.3; IEC TR 61000-3-13~\cite{b32} gives lower planning levels for HV and EHV systems), (8) allows")
add("A10", "Section 3.4.3, verification of (11)", T,
    r"yields $\mathrm{VUF}=2.67\%$, above the 2\% limit, whereas",
    r"yields $\mathrm{VUF}=2.67\%$, above the 2\% reference limit, whereas")
add("A11", "Section 3.4.3, last paragraph", T,
    r"is overly conservative, since the VUF limit of EN 50160~\cite{b31} applies to 95\% of the 10-min values over one week. The conventional percentile-based rating is the smallest rating for which this criterion holds",
    r"is overly conservative if the reference criterion applies, as in EN 50160~\cite{b31} and QCVN 26:2025/BCT~\cite{v2}, to 95\% of the 10-min values over one week. The conventional percentile-based rating is the smallest rating for which this criterion holds")
add("A12", "Section 3.4.3, paragraph after (11)", T,
    r"A practical rating also depends on the percentile form of the grid-code criterion, the rated current",
    r"A practical rating also depends on the percentile form of the criterion, the rated current")
add("A13", "Section 4.2, end of paragraph after (18)", T,
    r"The first constraint of (17) requires the grid-code criterion to hold in at least 95\% of the simulated weeks, so that the design does not rely on one random week.",
    r"The first constraint of (17) requires the reference percentile criterion (weekly P95 of the 10-min VUF at most $\varepsilon_\mathrm{lim}=2\%$) to hold in at least 95\% of the simulated weeks. The limit of 2\% is the reference limit of the case study (section~2.3) and the 95\% is a design confidence level chosen by the authors, so that the design does not rely on one random week; neither is prescribed by a standard, which specify the percentile of the 10-min values within a week and not a share of weeks.")
add("A14", "Section 4.3 (Solution procedure)", T,
    r"over the weeks, which enforces the first constraint of (17).",
    r"over the weeks, which enforces the first constraint of (17) at the design confidence level of 95\% of the weeks.")
add("A15", "Section 4.4, Table 'tA' caption", T,
    r"60 simulated weeks, $\varepsilon_\mathrm{lim}=2\%$; VUF values and energies are means over the weeks).",
    r"60 simulated weeks, reference limit $\varepsilon_\mathrm{lim}=2\%$; VUF values and energies are means over the weeks).")
add("A16", "Section 4.4, first results paragraph", T,
    r"the criterion is met with no margin in 5\% of the weeks and {{share_p95}}\% of the 10-min values exceed 2\%.",
    r"the criterion is met with no margin in 5\% of the weeks (the design confidence level) and {{share_p95}}\% of the 10-min values exceed the 2\% reference limit.")
add("A17", "Section 5, Table 'Limited comparison' (row 'Grid balancing')", T,
    r"P95 VUF $\le\varepsilon_\mathrm{lim}$ in $\ge95\%$ of weeks; max.\ 10-min VUF",
    r"P95 VUF $\le\varepsilon_\mathrm{lim}$ (reference limit) in $\ge95\%$ of weeks (design level); max.\ 10-min VUF")
add("A18", "Conclusions (1)", T,
    r"The proposed design meets the criterion in all weeks, roughly halves",
    r"The proposed design meets the reference criterion in all weeks, roughly halves")
add("A19", "Conclusions (2)", T,
    r"so percentile sizing at the limit fails under the exact network model.",
    r"so percentile sizing at the reference limit fails under the exact network model.")
add("A20", "Conclusions (2)", T,
    r"and it violated the criterion in none of 90 independent weeks (violation probability",
    r"and it violated the reference criterion in none of 90 independent weeks (violation probability")
add("A21", "Conclusions (3)", T,
    r"the saving therefore comes from formulating the problem on the grid-code quantity.",
    r"the saving therefore comes from formulating the problem on the percentile quantity of the standards.")
add("A22", "Conclusions, last paragraph (insert as new sentence before 'The phasor model was cross-checked')", T,
    r"The phasor model was cross-checked with OpenDSS, but",
    r"The 2\% limit and the 95\%-of-weeks level are assumptions of the case study: a specific line has to be sized against the emission limit that the network operator allocates to the substation according to IEC TR 61000-3-13, which is in general lower than the planning level, and against the unbalance that is already present at the PCC (section~4.5). The phasor model was cross-checked with OpenDSS, but")
add("A23", "Cover letter", "cover_letter.tex",
    r"against the 95th-percentile voltage-unbalance criterion of EN~50160, the converter current",
    r"against a 95th-percentile voltage-unbalance criterion modelled on EN~50160 (reference limit 2\%, met in at least 95\% of the simulated weeks), the converter current")
add("A24", "Online Resource 2, section on window budget (optional consistency)", "OR2.tex",
    r"The grid-code criterion acts on 10-min rms aggregates",
    r"The reference percentile criterion acts on 10-min rms aggregates")
add("A25", "Bibliography (b31)", T,
    r"\bibitem{b31} EN 50160:2010+A3:2019 \textit{Voltage Characteristics of Electricity Supplied by Public Electricity Networks} (Brussels: CENELEC)",
    r"\bibitem{b31} EN 50160:2022+A1:2025 \textit{Voltage Characteristics of Electricity Supplied by Public Electricity Networks} (Brussels: CENELEC)")
add("A26", "Section 4.9 (Validity of the sizing results), optional", T,
    r"The absolute ratings must be recomputed with line-specific planning data, whereas",
    r"The absolute ratings must be recomputed with line-specific planning data, including the background unbalance at the PCC and the emission limit allocated to the substation (sections~2.3 and 4.5), whereas")
