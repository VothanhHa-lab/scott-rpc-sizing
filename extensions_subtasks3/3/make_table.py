"""Builds the summary JSON and the LaTeX table for section 4.5 from the result files."""
import json
R = json.load(open("/home/claude/subtasks3/3/results_background.json"))
X = json.load(open("/home/claude/subtasks3/3/results_background_extra.json"))
LIM, ALPHA = 2.0, 1.4
label = {"none": "No background", "alg": "In phase (algebraic sum)", "worst": "Worst fixed phase",
         "rand": "Uniform random phase", "iec": r"IEC TR 61000-3-13, $\alpha=1.4$"}
rows, summ = [], {}
order = [("none", 0.0)] + [(n, b) for b in (0.5, 1.0) for n in ("alg", "worst", "rand", "iec")]
for n, b in order:
    key = f"{n}_{b}"; s = R["scen"][key]; p = s["proposed"]
    # conventional percentile sizing: eps_u = remaining budget
    if n == "none":
        eps_c, Cc, Jc, comply_c = 2.0, s["conventional"]["C"], s["conventional"]["J"], s["conventional"]["comply"]
    elif n == "iec":
        e = X["iec_conv"][str(b)]; eps_c, Cc, Jc, comply_c = e["eps_u"], e["Chat"], e["J"], e["comply"]
    else:
        eps_c = LIM - b
        # J at factor 1.0 and C_hat for that eps
        Cc = s["Chat"][str(eps_c)]
        Jc = s["J_per_eps_at_Chat_mult"][str(eps_c)]["1.0"]
        comply_c = None
    ig = X["ignore_bg"][key]
    summ[key] = dict(eps_conv=eps_c, C_conv=Cc, J_conv=Jc, C_star=p["C"], eps_star=p["eps_u"], J_star=p["J"],
                     dJ_vs_conv_pct=100 * (p["J"] / Jc - 1), dC_vs_conv_pct=100 * (p["C"] / Cc - 1),
                     C_star_vs_nobg_pct=100 * (p["C"] / R["scen"]["none_0.0"]["proposed"]["C"] - 1),
                     J_star_vs_nobg_pct=100 * (p["J"] / R["scen"]["none_0.0"]["proposed"]["J"] - 1),
                     Chat={k: v for k, v in s["Chat"].items()}, comply_star=p["comply"], p95_star=p["p95_mean"],
                     ignoring_bg=ig)
    def f(x, d=2): return "--" if x is None or x == float("inf") else f"{x:.{d}f}"
    ch = s["Chat"]
    rows.append(" & ".join([label[n], "" if n == "none" else f"{b:.1f}",
        f(ch["0.0"]), f(ch["0.5"]), f(ch["1.0"]), f(ch["1.5"]),
        f(p["C"]), f(p["eps_u"]), f(p["J"], 0), f(Jc, 0),
        f"{summ[key]['dJ_vs_conv_pct']:.0f}".replace("-", "$-$"), f"{100*ig['comply']:.0f}"]) + r"\\")
open("/home/claude/subtasks3/3/table_background_rows.tex", "w").write("\n".join(rows) + "\n")
json.dump(summ, open("/home/claude/subtasks3/3/summary_background.json", "w"), indent=1,
          default=lambda o: None)
for k, v in summ.items():
    print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items() if a not in ("Chat", "ignoring_bg")})
print("\n".join(rows))
