"""Run validation cases A and B in OpenDSS and compare with python_reference.json."""
import json, sys, datetime
import numpy as np
sys.path.insert(0, "/home/claude/subtasks2/6")
import scott_dss as S
import opendssdirect as dss

ref = json.load(open("/home/claude/subtasks2/6/python_reference.json"))
rows_ref = {(r["set"], r["id"], r["load_model"]): r for r in ref["reference_rows"]}
U0A, U0B = -1j * S.KV_S, 1.0 * S.KV_S          # no-load feeder voltages (kV), ideal Scott, beta leads alpha


def solve_case(Ssc, loads, mode="xfmr"):
    S.build(Ssc, loads, mode)
    res, U, I = S.results(Ssc)
    fp = S.feeder_powers()
    res["Sa_act"], res["Sb_act"] = fp["a"], fp["b"]
    return res


def kw(s):
    return s.real * 1e3, s.imag * 1e3


def loads_A(c, model):
    Sa = complex(c["Sa_MVA"] * np.cos(np.radians(c["phia_deg"])), c["Sa_MVA"] * np.sin(np.radians(c["phia_deg"])))
    Sb = complex(c["Sb_MVA"] * np.cos(np.radians(c["phib_deg"])), c["Sb_MVA"] * np.sin(np.radians(c["phib_deg"])))
    kind = {"CP": "PQ", "CZ": "Z"}[model]
    return [dict(bus="a", kind=kind, kW=kw(Sa)[0], kvar=kw(Sa)[1]),
            dict(bus="b", kind=kind, kW=kw(Sb)[0], kvar=kw(Sb)[1])]


def loads_B(c, model):
    SL = complex(c["SL_P_MW"], c["SL_Q_Mvar"]); sx = complex(c["sx_P_MW"], c["sx_Q_Mvar"])
    Sa, Sb = SL - sx, sx
    if model == "CZ":      # net feeder powers as constant impedance (definition of the reference model CZ)
        return [dict(bus="a", kind="Z", kW=kw(Sa)[0], kvar=kw(Sa)[1]),
                dict(bus="b", kind="Z", kW=kw(Sb)[0], kvar=kw(Sb)[1])]
    if model == "CP":      # load S_L + ideal RPC pair (generator s_x at alpha, load s_x at beta), all constant power
        return [dict(bus="a", kind="PQ", kW=kw(SL)[0], kvar=kw(SL)[1]),
                dict(bus="a", kind="GEN", kW=kw(sx)[0], kvar=kw(sx)[1]),
                dict(bus="b", kind="PQ", kW=kw(sx)[0], kvar=kw(sx)[1])]
    if model == "CI":      # same pair as ideal current sources (fixed phasors at the no-load feeder voltage)
        return [dict(bus="a", kind="I", kW=kw(SL)[0], kvar=kw(SL)[1], u0_kV=U0A),
                dict(bus="a", kind="I", kW=kw(sx)[0], kvar=kw(sx)[1], u0_kV=U0A, sign=-1),
                dict(bus="b", kind="I", kW=kw(sx)[0], kvar=kw(sx)[1], u0_kV=U0B)]


def _ser(x):
    if isinstance(x, (complex, np.complexfloating)):
        return dict(re=float(x.real), im=float(x.imag))
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    return str(x)


def rel(a, b):
    return (a - b) / b * 100.0 if abs(b) > 1e-9 else float("nan")


def main():
    out = []
    for c in ref["caseA"]:
        for m in ("CZ", "CP"):
            r = rows_ref[("A", c["id"], m)]
            res = solve_case(c["Ssc_MVA"], loads_A(c, m))
            resS = solve_case(c["Ssc_MVA"], loads_A(c, m), mode="series")
            out.append(dict(set="A", id=c["id"], load_model=m, Ssc_MVA=c["Ssc_MVA"], k=c["k"], dphi_deg=c["dphi_deg"],
                            VUF_dss=res["VUF_pct"], VUF_dss_series=resS["VUF_pct"], IUF_dss=res["IUF_pct"],
                            VUF_py=r["VUF_exact_pct"], IUF_py=r["IUF_exact_pct"], VUF_eq8=r["VUF_eq8_pct"], IUF_eq7=r["IUF_eq7_pct"],
                            Sa_dss=[res["Sa_act"].real, res["Sa_act"].imag], Sb_dss=[res["Sb_act"].real, res["Sb_act"].imag],
                            Sa_py=[r["Sa_act_P_MW"], r["Sa_act_Q_Mvar"]], Sb_py=[r["Sb_act_P_MW"], r["Sb_act_Q_Mvar"]],
                            V1_pcc_kVll=res["V1_pcc_kVll"], converged=res["converged"], iterations=res["iterations"]))
    for c in ref["caseB"]:
        for m in ("CI", "CP", "CZ"):
            r = rows_ref[("B", c["id"], m)]
            res = solve_case(c["Ssc_MVA"], loads_B(c, m))
            resS = solve_case(c["Ssc_MVA"], loads_B(c, m), mode="series")
            out.append(dict(set="B", id=c["id"], load_model=m, Ssc_MVA=c["Ssc_MVA"], rating_MVA=c["rating_MVA"],
                            VUF_dss=res["VUF_pct"], VUF_dss_series=resS["VUF_pct"], IUF_dss=res["IUF_pct"],
                            VUF_py=r["VUF_exact_pct"], IUF_py=r["IUF_exact_pct"], VUF_eq8=r["VUF_eq8_pct"], IUF_eq7=r["IUF_eq7_pct"],
                            Sa_dss=[res["Sa_act"].real, res["Sa_act"].imag], Sb_dss=[res["Sb_act"].real, res["Sb_act"].imag],
                            Sa_py=[r["Sa_act_P_MW"], r["Sa_act_Q_Mvar"]], Sb_py=[r["Sb_act_P_MW"], r["Sb_act_Q_Mvar"]],
                            V1_pcc_kVll=res["V1_pcc_kVll"], converged=res["converged"], iterations=res["iterations"]))
    for o in out:
        o["VUF_rel_err_vs_py_pct"] = rel(o["VUF_dss"], o["VUF_py"])
        o["VUF_abs_err_vs_py_pp"] = o["VUF_dss"] - o["VUF_py"]
        o["VUF_rel_err_vs_eq8_pct"] = rel(o["VUF_dss"], o["VUF_eq8"])
        o["IUF_abs_err_vs_py_pp"] = o["IUF_dss"] - o["IUF_py"]
        o["IUF_abs_err_vs_eq7_pp"] = o["IUF_dss"] - o["IUF_eq7"] if o["IUF_eq7"] is not None else None
        o["Sa_rel_err_pct"] = abs(complex(*o["Sa_dss"]) - complex(*o["Sa_py"])) / max(abs(complex(*o["Sa_py"])), 1e-9) * 100
        o["Sb_rel_err_pct"] = (abs(complex(*o["Sb_dss"]) - complex(*o["Sb_py"])) / abs(complex(*o["Sb_py"])) * 100) if abs(complex(*o["Sb_py"])) > 1e-9 else abs(complex(*o["Sb_dss"]))
    json.dump(dict(meta=dict(generated=datetime.datetime.now().isoformat(timespec="seconds"),
                             tool=dss.Basic.Version().splitlines()[0],
                             opendssdirect=dss.__version__ if hasattr(dss, "__version__") else "0.9.4",
                             sc_test_xfmr=S.sc_test("xfmr"), sc_test_series=S.sc_test("series")),
                   rows=out), open("/home/claude/subtasks2/6/dss_results.json", "w"), indent=1, default=_ser)
    return out


if __name__ == "__main__":
    out = main()
    print(f"{'id':26s} {'lm':3s} {'VUF_dss':>8s} {'VUF_py':>8s} {'rel%':>7s} {'abs pp':>8s} {'ser rel%':>8s} {'IUF_dss':>8s} {'IUF_py':>8s} {'S rel%':>7s}")
    for o in out:
        print(f"{o['id']:26s} {o['load_model']:3s} {o['VUF_dss']:8.4f} {o['VUF_py']:8.4f} {o['VUF_rel_err_vs_py_pct']:7.3f} {o['VUF_abs_err_vs_py_pp']:8.5f} {rel(o['VUF_dss_series'],o['VUF_py']):8.3f} {o['IUF_dss']:8.3f} {o['IUF_py']:8.3f} {max(o['Sa_rel_err_pct'],o['Sb_rel_err_pct']):7.3f}")
