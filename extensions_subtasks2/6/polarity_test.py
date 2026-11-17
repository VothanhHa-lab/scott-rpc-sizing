"""Effect of reversing the teaser winding (OpenDSS): power-defined loads vs fixed-phasor current sources."""
import sys, json
import numpy as np
sys.path.insert(0, "/home/claude/subtasks2/6")
import scott_dss as S, run_cases as R, opendssdirect as dss

def flipped(loads, Ssc=500):
    S.build(Ssc, loads)
    a = S.results(Ssc)[0]
    dss.Text.Command("edit transformer.ttsr buses=[pcc.4.1, fb.1.0]")
    dss.Text.Command("solve mode=snap")
    b = S.results(Ssc)[0]
    return a, b

out = {}
eq = [dict(bus="a", kW=8000, kvar=2629.6, kind="PQ"), dict(bus="b", kW=8000, kvar=2629.6, kind="PQ")]
a, b = flipped(eq)
out["PQ_equal_loads"] = {k: dict(VUF=float(r["VUF_pct"]), IUF=float(r["IUF_pct"]),
                                 arg_Ub_over_Ua_deg=float(np.degrees(np.angle(r["Ub_kV"] / r["Ua_kV"]))))
                         for k, r in (("ok", a), ("flipped_teaser", b))}
c = [c for c in R.ref["caseB"] if c["id"] == "B3_eq11"][0]
a, b = flipped(R.loads_B(c, "CI"))
out["CI_B3_eq11_fixed_phasor_currents"] = dict(VUF_ok=float(a["VUF_pct"]), VUF_flipped_teaser=float(b["VUF_pct"]))
a, b = flipped(R.loads_B(c, "CP"))
out["CP_B3_eq11"] = dict(VUF_ok=float(a["VUF_pct"]), VUF_flipped_teaser=float(b["VUF_pct"]))
json.dump(out, open("/home/claude/subtasks2/6/polarity_test.json", "w"), indent=1)
print(json.dumps(out, indent=1))
