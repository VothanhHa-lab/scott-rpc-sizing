import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8})
BLUE, VERM = "#0072B2", "#D55E00"
r = json.load(open("/home/claude/subtasks/1/ci_results.json"))
fig, ax = plt.subplots(1, 2, figsize=(6.85, 2.5), sharey=True)
for a, case, ttl in [(ax[0], "base", "(a) High-speed line, $N=60$"), (ax[1], "suburban", "(b) Suburban line, $N=40$")]:
    for tag, col, lab in [("eps2", BLUE, "percentile sizing ($\\varepsilon_u$=2%)"), ("eps_star", VERM, "proposed ($\\varepsilon_u^*$)")]:
        v = r["convergence"][case][tag]
        n = [x["n"] for x in v["rows"]]
        a.plot(n, [x["sd_pct"] for x in v["rows"]], "o-", color=col, lw=1.0, ms=2.5, label=lab)
    a.set_ylim(0, 4); a.set_xlim(8, None)
    a.set_title(ttl, fontsize=8); a.set_xlabel("Number of simulated weeks $n$")
ax[0].set_ylabel("Std. deviation of the design value (%)")
ax[0].legend(loc="upper right", fontsize=7)
fig.tight_layout(); fig.savefig("/home/claude/subtasks/1/figE2_design_value_spread.pdf"); print("ok")
