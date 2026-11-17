"""Compute the Python reference values and write python_reference.json.

The file is the single source of truth for the MATLAB scripts (case definitions,
parameters, load segment of case C) and for compare.py (reference values).
Run:  nice -n 15 python3 make_reference.py
"""
import json, datetime, time
import numpy as np
import ref_models as R

OUT = "python_reference.json"


def f(x):
    return float(x)


def main():
    t0 = time.time()
    A = R.cases_A()
    B = R.cases_B()
    LM_A = ["CZ", "CP"]
    LM_B = ["CI", "CP", "CZ"]

    rows = []
    for c in A:
        Sa, Sb = R.case_A_loads(c)
        for m in LM_A:
            e = R.EXACT[m](Sa, Sb, c["Ssc_MVA"])
            rows.append(dict(set="A", id=c["id"], load_model=m, Ssc_MVA=c["Ssc_MVA"],
                             IUF_eq7_pct=f(R.iuf_eq7(Sa, Sb)), VUF_eq8_pct=f(R.vuf_eq8(Sa, Sb, c["Ssc_MVA"])),
                             IUF_exact_pct=f(e["IUF_pct"]), VUF_exact_pct=f(e["VUF_pct"]),
                             VUF_network_solve_pct=f(R.vuf_network_solve(Sa, Sb, c["Ssc_MVA"])) if m == "CP" else None,
                             Sa_act_P_MW=f(e["Sa_act_MVA"].real), Sa_act_Q_Mvar=f(e["Sa_act_MVA"].imag),
                             Sb_act_P_MW=f(e["Sb_act_MVA"].real), Sb_act_Q_Mvar=f(e["Sb_act_MVA"].imag)))
    for c in B:
        Sa, Sb = R.case_B_loads(c)
        for m in LM_B:
            e = R.EXACT[m](Sa, Sb, c["Ssc_MVA"])
            rows.append(dict(set="B", id=c["id"], load_model=m, Ssc_MVA=c["Ssc_MVA"],
                             IUF_eq7_pct=f(R.iuf_eq7(Sa, Sb)) if abs(Sa) > 0 else None,
                             VUF_eq8_pct=f(R.vuf_eq8(Sa, Sb, c["Ssc_MVA"])),
                             IUF_exact_pct=f(e["IUF_pct"]), VUF_exact_pct=f(e["VUF_pct"]),
                             VUF_network_solve_pct=f(R.vuf_network_solve(Sa, Sb, c["Ssc_MVA"])) if m == "CP" else None,
                             Sa_act_P_MW=f(e["Sa_act_MVA"].real), Sa_act_Q_Mvar=f(e["Sa_act_MVA"].imag),
                             Sb_act_P_MW=f(e["Sb_act_MVA"].real), Sb_act_Q_Mvar=f(e["Sb_act_MVA"].imag)))

    # ---- case C
    C, eps, Ssc, a, P, Q = R.design_and_segment()
    p = R.dynamic_params(C, eps, Ssc)
    variants = []
    pyC = []
    series = {}
    for ff in (True, False):
        ic = R.initial_state(P, Q, C, eps, Ssc, ff)
        x0 = [p["Wref_MJ"], ic["Pa"], ic["Qa"], ic["Pb"], ic["Qb"], ic["integ"], ic["pm"], ic["qm"]]
        variants.append(dict(case_id=f"C_ff{int(ff)}", ff=int(ff), x0=[f(v) for v in x0]))
        for label, dt in (("euler_dt2e-4", 2e-4), ("euler_dt5e-5", 5e-5)):
            o = R.run_caseC(ff, dt=dt)
            if dt == 2e-4:
                w = (o["t"] >= 38.0) & (o["t"] <= 44.0)
                for k in ("t", "Vdc", "Ia", "Ib", "Pa", "Pb"):
                    series[f"euler_ff{int(ff)}_{k}"] = o[k][w]
            pyC.append(dict(case_id=f"C_ff{int(ff)}", method=label, **{k: f(v) for k, v in o["metrics"].items()}))
        c = R.run_caseC_continuous(ff)
        w = (c["t"] >= 38.0) & (c["t"] <= 44.0)
        for k in ("t", "Vdc", "Ia", "Ib", "Pa", "Pb"):
            series[f"cont_ff{int(ff)}_{k}"] = c[k][w]
        m = R.metrics_from_series(c["t"], c["Vdc"], c["Ia"], c["Ib"])
        pyC.append(dict(case_id=f"C_ff{int(ff)}", method="continuous_rk45", **{k: f(v) for k, v in m.items()}))
        print("C", ff, "done", round(time.time() - t0), "s", flush=True)

    ref = dict(
        meta=dict(generated=datetime.datetime.now().isoformat(timespec="seconds"),
                  description="Python reference values for the Simulink validation package",
                  code="rpc_sizing (network.py exact phasor model, dynamics.py averaged RPC model)",
                  note_CP="CP = constant-power loads (rpc_sizing.network.solve); CZ = constant impedance at 27.5 kV; "
                         "CI = controlled current sources I=conj(S/u0) at the no-load feeder voltage"),
        constants=dict(V_prim_kV=R.V_PRIM_KV, V_sec_kV=R.V_SEC_KV, f_Hz=R.F_HZ, XR_source=R.XR_SRC,
                       XR_leg=R.XR_LEG, leg_MVA=40.0, uk_pu=0.105, vuf_limit_pct=R.LIM_PCT,
                       S_base_MVA=R.S_B),
        load_models_A=LM_A, load_models_B=LM_B,
        caseA=A, caseB=B,
        caseC=dict(params=p, P_MW=[f(v) for v in P], Q_Mvar=[f(v) for v in Q], t_step_s=R.T_STEP,
                   step_MW=R.STEP_MW, band_pct=R.VBAND_PCT, segment_start_index=int(a),
                   design_C_MVA=C, design_eps_pct=eps, variants=variants,
                   note="segment = 61 s of base week 0 with the largest 1-s change of the requested transfer, "
                        "as in dyn_run.py; step of -10 MW added to P_L at t=40 s"),
        paper_values=dict(
            table5=dict(IUF_k0p5_dphi0=dict(analytic=33.33, sim=32.87), IUF_k1_dphi20=dict(analytic=17.63, sim=17.28),
                        VUF_k0_Ssc500=dict(analytic=1.684, sim=1.645)),
            table6=dict(none=dict(analytic=3.69, sim=3.77), Ponly=dict(analytic=2.62, sim=2.67),
                        eq11=dict(analytic=2.00, sim=2.04), full=dict(analytic=0.00, sim=0.00)),
            note="values printed in the manuscript (Python time-domain model), shown for context only"),
        reference_rows=rows,
        python_caseC=pyC,
    )
    np.savez_compressed("python_caseC_series.npz", **series)
    with open(OUT, "w") as fh:
        json.dump(ref, fh, indent=1)
    print("wrote", OUT, len(rows), "rows;", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
