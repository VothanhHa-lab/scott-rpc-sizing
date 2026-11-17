"""IEC 60076-7 (2005) difference-equation thermal model (clause 8.2.3 / Annex C, equations C.6-C.11,
parameters of Table E.1 as reproduced in IS 2026 (Part 7):2009) driven by the per-second current of the
Scott alpha leg (K = I/I_rated). Generic ONAN/ONAF defaults, NOT heat-run data of a real transformer.
Relative ageing rate V (non-upgraded paper, 98 C), IEC 60076-7 eq. (2)."""
import sys, json, os
import numpy as np
from scipy.signal import lfilter, lfiltic
D = "/home/claude/subtasks4/2/data"; R_ = "/home/claude/subtasks4/2/results"
PAR = {
    "ONAN": dict(R=6.0, x=0.8, y=1.3, k11=0.5, k21=2.0, k22=2.0, tau_o=210 * 60.0, tau_w=10 * 60.0, d_or=52.0, d_hr=26.0),
    "ONAF": dict(R=6.0, x=0.8, y=1.3, k11=0.5, k21=2.0, k22=2.0, tau_o=150 * 60.0, tau_w=7 * 60.0, d_or=52.0, d_hr=26.0),
}


def thermal(K, p, theta_a=20.0, dt=1.0):
    a_o = dt / (p["k11"] * p["tau_o"]); a1 = dt / (p["k22"] * p["tau_w"]); a2 = dt * p["k22"] / p["tau_o"]
    Ky = K ** p["y"]
    u_o = ((1 + K ** 2 * p["R"]) / (1 + p["R"])) ** p["x"] * p["d_or"]
    y0 = ((1 + p["R"] * 0.0) / (1 + p["R"])) ** p["x"] * p["d_or"]      # no load at the start of the week
    flt = lambda u, a, z0: lfilter([a], [1, -(1 - a)], u, zi=lfiltic([a], [1, -(1 - a)], [z0]))[0]
    do = flt(u_o, a_o, y0)
    h1 = flt(p["k21"] * Ky * p["d_hr"], a1, 0.0)
    h2 = flt((p["k21"] - 1) * Ky * p["d_hr"], a2, 0.0)
    return theta_a + do, theta_a + do + h1 - h2      # top-oil, hot-spot (deg C)


def ageing(th_h, ref=98.0):
    return np.exp(15000.0 / (ref + 273.0) - 15000.0 / (th_h + 273.0))


def run(ratings=(25.0, 30.0, 31.5, 35.0, 40.0), cooling=("ONAN", "ONAF"), amb=(20.0, 40.0), weeks=range(60)):
    res = {}
    for k in weeks:
        d = np.load(f"{D}/legs_w{k:03d}.npz")
        I40 = d["I_alpha_pu40"].astype(float)
        for Sr in ratings:
            K = I40 * 40.0 / Sr
            for c in cooling:
                for ta in amb:
                    to, th = thermal(K, PAR[c], ta)
                    V = ageing(th)
                    dayV = V.reshape(7, -1).mean(axis=1)
                    key = f"{c}|{Sr}|{ta}"
                    res.setdefault(key, []).append(dict(week=k, th_max=float(th.max()), to_max=float(to.max()),
                                                        V_week=float(V.mean()), V_day_max=float(dayV.max()),
                                                        t_above_120=int((th > 120).sum()), t_above_140=int((th > 140).sum())))
        if k % 10 == 0: print("thermal week", k, flush=True)
    return res


if __name__ == "__main__":
    r = run()
    json.dump(r, open(f"{R_}/thermal.json", "w"))
