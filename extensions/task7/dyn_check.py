"""DC-link / current check for the window-budget controller on the averaged RPC model
(copy of rpc_sizing.dynamics.simulate with a time-varying threshold)."""
import time
from common import *
from rpc_sizing.params import RPC
from rpc_sizing import dynamics as dy

def simulate_theta(P_L, Q_L, C, TH, Ssc, t_step=None, step_MW=0.0, dt=4e-4, f_meas=50.0, H_ms=None, ff=True):
    H = (RPC["H_dc_ms"] if H_ms is None else H_ms) * 1e-3
    Vref = RPC["Vdc_ref"]
    Cdc = 2.0 * H * C * 1e6 / Vref ** 2
    Wref = 0.5 * Cdc * Vref ** 2
    w = 2 * np.pi * RPC["f_dc"]; Kp, Ki = 2 * 0.7 * w, w ** 2
    tau = RPC["tau_i"]; k0, k1, k2 = RPC["k0"], RPC["k1"], RPC["k2"]
    T = len(P_L) - 1; n = int(T / dt); t = np.arange(n) * dt
    PL = np.interp(t, np.arange(len(P_L)), P_L); QL = np.interp(t, np.arange(len(Q_L)), Q_L)
    if t_step is not None:
        PL = PL + np.where(t >= t_step, step_MW, 0.0)
    a_m = dt / (dt + 1.0 / (2 * np.pi * f_meas))
    W = Wref; pm, qm = PL[0], QL[0]
    S0 = np.hypot(pm, qm)
    sx0 = min(max(0.0, S0 - TH[0] / 100.0 * Ssc) / 2.0, KAPPA * C)
    Pa = sx0 * pm / S0 if S0 > 0 else 0.0; Qa = sx0 * qm / S0 if S0 > 0 else 0.0
    ploss0 = 2 * (k0 * C + k1 * sx0 + k2 * sx0 ** 2 / C)
    Pb, Qb = Pa + ploss0, Qa
    integ = 0.0 if ff else Pa + ploss0
    Vdc = np.empty(n); Ia = np.empty(n); Ib = np.empty(n)
    for i in range(n):
        pm += a_m * (PL[i] - pm); qm += a_m * (QL[i] - qm)
        S = np.hypot(pm, qm)
        th = TH[min(int(i * dt), len(TH) - 1)]
        req = max(0.0, S - th / 100.0 * Ssc) / 2.0
        U = busbar_voltage(PL[i] - Pa, QL[i] - Qa, Ssc)
        lim = C * min(U, 1.0)
        sx = min(req, KAPPA * lim)
        if S > 1e-9: Pref, Qref = sx * pm / S, sx * qm / S
        else: Pref = Qref = 0.0
        ploss = 2 * (k0 * C + k1 * np.hypot(Pa, Qa) + k2 * (Pa ** 2 + Qa ** 2) / C)
        e = (Wref - W) / 1e6
        integ += Ki * e * dt
        Pb_ref = (Pref + ploss if ff else 0.0) + Kp * e + integ
        Pb_ref = float(np.clip(Pb_ref, -lim, lim))
        qmax = np.sqrt(max(lim ** 2 - Pb_ref ** 2, 0.0))
        Qb_ref = float(np.clip(Qref, -qmax, qmax))
        if abs(integ) > lim: integ = np.sign(integ) * lim
        Pa += dt / tau * (Pref - Pa); Qa += dt / tau * (Qref - Qa)
        Pb += dt / tau * (Pb_ref - Pb); Qb += dt / tau * (Qb_ref - Qb)
        W += (Pb - Pa - ploss) * 1e6 * dt
        Vdc[i] = np.sqrt(max(2 * W / Cdc, 0.0))
        Ia[i] = np.hypot(Pa, Qa) / max(U, 1e-3) / C; Ib[i] = np.hypot(Pb, Qb) / C
    return dict(Vdc=Vdc, Ia=Ia, Ib=Ib, t=t, Cdc_mF=Cdc * 1e3)

if __name__ == "__main__":
    name = sys.argv[1]
    D = json.load(open(os.path.join(HERE, f"design_{name}.json")))
    best = min(D["cands"], key=lambda c: c["J"]); C = best["C"]; vs, q = D["vstar"], D["q"]; iq = QS.index(q)
    TAB = fold_tables("A")
    k = 0
    P, Q = load_week(k); W = windows(P, Q); F = Feat(W[2], Ssc)
    G = TAB.get(C, iq)
    sx, v, th = run(*W, C, Ssc, kind="table", vstar=vs, G=G, feat=F, want_theta=True)
    thf = th.reshape(-1)
    # only seconds with load above the threshold matter: largest jump of the requested transfer caused by a threshold change
    S = np.hypot(P, Q)
    dreq = np.abs(np.maximum(0, S[1:] - thf[1:] * Ssc / 100) - np.maximum(0, S[1:] - thf[:-1] * Ssc / 100)) / 2
    i = int(np.argmax(np.where(S[1:] > 15, dreq, 0)))
    a = max(i - 30, 0); seg = slice(a, a + 61)
    res = {}
    for lab, TH in [("budget", thf[seg]), ("eq15", np.full(61, 1.0))]:
        o = simulate_theta(P[seg], Q[seg], C, TH, Ssc, t_step=40.0, step_MW=-10.0)
        res[lab] = dict(Vdc_min=float(o["Vdc"].min()), Vdc_max=float(o["Vdc"].max()), Ia_max=float(o["Ia"].max()),
                        Ib_max=float(o["Ib"].max()), Cdc_mF=o["Cdc_mF"])
        print(lab, res[lab], flush=True)
    res.update(seg_start=a, max_theta_step_effect_MVA=float(dreq.max()), theta_seg=[float(thf[seg].min()), float(thf[seg].max())], C=C,
               Vdc_band=[RPC["Vdc_min"], RPC["Vdc_max"]])
    json.dump(res, open(os.path.join(HERE, "dyn_check.json"), "w"), indent=1)
