"""Kinematic traction-load model of a high-speed EMU.

Each train run through the zone fed by one co-phase substation is simulated
with a 1 s step from the longitudinal equation of motion

    m_eff dv/dt = F_t - F_roll(v) - F_aero(v) - F_grade(x),
    F_roll + F_aero = A + B v + C v^2   (Davis form, v in km/h, F in kN),
    F_grade = m g i(x),

and a simple driving strategy with four states: maximum traction,
speed holding (cruise), coasting and service braking. The electrical power
exchanged with the catenary is

    P_el = F_t v / eta_t + P_aux               (traction, F_t >= 0)
    P_el = -min(|F_t| v, P_reg,wheel) eta_r + P_aux (braking, regenerative)

with the regenerated electrical power limited to P_reg,max; the remaining
braking force is provided by the friction brake. All numbers are planning
assumptions (see params.py) and are not data of a specific rolling stock.
"""
import numpy as np

G = 9.81


def grade_profile(rng, length_m, seg_min=2000.0, seg_max=5000.0, g_max=8.0):
    """Piecewise-constant grade profile (per mille) along the zone."""
    edges = [0.0]
    while edges[-1] < length_m:
        edges.append(edges[-1] + rng.uniform(seg_min, seg_max))
    edges[-1] = length_m
    grades = rng.uniform(-g_max, g_max, len(edges) - 1)
    return np.array(edges), grades


def grade_at(x, edges, grades):
    k = np.searchsorted(edges, x, side="right") - 1
    k = np.clip(k, 0, len(grades) - 1)
    return grades[k]


def speed_limit_profile(dx, length_m, v_line, restriction=None, stop_at=None):
    """Static speed limit (m/s) on a grid with spacing dx.

    restriction: (x1, x2, v_r) temporary speed restriction (m, m, m/s)
    stop_at: x of the station (m) or None
    """
    xg = np.arange(0.0, length_m + dx, dx)
    vlim = np.full_like(xg, v_line)
    if restriction is not None:
        x1, x2, vr = restriction
        vlim[(xg >= x1) & (xg <= x2)] = vr
    if stop_at is not None:
        vlim[np.argmin(np.abs(xg - stop_at))] = 0.0
    return xg, vlim


def braking_curve(xg, vlim, b):
    """Allowed speed taking future limits into account (backward pass)."""
    va = vlim.copy()
    dx = xg[1] - xg[0]
    for k in range(len(xg) - 2, -1, -1):
        va[k] = min(va[k], np.sqrt(va[k + 1] ** 2 + 2.0 * b * dx))
    return va


def run_train(p, rng, edges, grades, stop=False, restriction=None,
              mass_factor=1.0, dt=1.0, regen=True, details=False):
    """Simulate one train run; returns arrays P_el (MW) per time step."""
    m = p["mass_t"] * 1e3 * mass_factor
    m_eff = m * p["rot_factor"]
    L = p["zone_length_m"]
    v_line = p["v_line_kmh"] / 3.6
    b = p["b_service"]
    dxg = 10.0
    stations = list(p.get("stations_x_m", [p["station_x_m"]])) if stop else []
    xg, vlim = speed_limit_profile(dxg, L, v_line, restriction,
                                   stations[0] if stations else None)
    va = braking_curve(xg, vlim, 0.85 * b)
    # coasting is used when the braking curve of a lower limit lies within
    # the coasting look-ahead distance
    coast_la = p["coast_lookahead_m"]
    look = int(coast_la / dxg)
    vmin_ahead = np.array([vlim[k:k + look + 1].min() for k in range(len(xg))])

    x, v = 0.0, v_line
    F_prev = 0.0
    dwell_left = None
    out = []
    log = []
    t = 0.0
    while x < L and t < 4 * 3600:
        k = min(int(x / dxg), len(xg) - 1)
        vk_kmh = v * 3.6
        R = (p["davis_A"] + p["davis_B"] * vk_kmh + p["davis_C"] * vk_kmh ** 2) * 1e3
        Fg = m * G * grade_at(x, edges, grades) * 1e-3
        if dwell_left is not None:
            # standing at the station
            out.append(p["P_aux_MW"])
            log.append((x, 0.0, 0.0))
            dwell_left -= dt
            t += dt
            if dwell_left <= 0:
                dwell_left = None
                stations.pop(0)
                stop = bool(stations)
                xg, vlim = speed_limit_profile(dxg, L, v_line, restriction,
                                               stations[0] if stations else None)
                va = braking_curve(xg, vlim, 0.85 * b)
                vmin_ahead = np.array([vlim[j:j + look + 1].min()
                                       for j in range(len(xg))])
            continue
        Fmax_tr = min(p["F_max_kN"] * 1e3,
                      p["P_wheel_max_MW"] * 1e6 / max(v, 0.1))
        curve_active = va[k] < vlim[k] - 0.5
        if v > va[k] + 0.5 or (curve_active and v > va[k] - 2.0):
            # service braking along the braking curve, with a proportional
            # correction when the train is above the curve (jerk-limited
            # brake build-up), limited to the maximum deceleration
            b_cmd = min(p["b_max"], max(0.0, b + 0.5 * (v - va[k])))
            F_cmd = -m_eff * b_cmd + R + Fg
        elif vmin_ahead[k] < vlim[k] - 0.1 and v > vmin_ahead[k] + 1.0:
            F_cmd = 0.0                         # coast before a lower limit
        elif v < vlim[k] - 1.0:
            F_cmd = Fmax_tr                     # accelerate
        else:
            # hold speed (proportional speed control around the limit)
            F_cmd = R + Fg + m_eff * (vlim[k] - 0.3 - v) / 10.0
        F_cmd = float(np.clip(F_cmd, -m_eff * p["b_max"], Fmax_tr))
        # jerk / power-rate limit of the traction control
        # first-order smoothing of the command (traction control dynamics)
        F_cmd = F_prev + 0.4 * (F_cmd - F_prev)
        dF = p["dF_max_kN_s"] * 1e3 * dt
        F = float(np.clip(F_cmd, F_prev - dF, F_prev + dF))
        F_prev = F
        a = (F - R - Fg) / m_eff
        v_new = max(v + a * dt, 0.0)
        x += 0.5 * (v + v_new) * dt
        v = v_new
        Pw = F * v  # W at wheel
        if Pw >= 0:
            Pel = Pw / p["eta_t"] / 1e6 + p["P_aux_MW"]
        else:
            if regen:
                Preg = min(-Pw, p["P_reg_wheel_max_MW"] * 1e6) * p["eta_r"] / 1e6
                Preg = min(Preg, p["P_reg_el_max_MW"])
            else:
                Preg = 0.0
            Pel = -Preg + p["P_aux_MW"]
        out.append(Pel)
        log.append((x, v, F))
        t += dt
        # station stop: the 1 s step can pass the stopping point with a small
        # residual speed, so the stop is triggered when the train reaches the
        # station or is almost at rest just before it
        if stop and (x >= stations[0] - 1.0 or
                     (v < 0.5 and stations[0] - x < 100.0)):
            x = min(x, stations[0])
            v = 0.0
            F_prev = 0.0
            dwell_left = rng.uniform(*p["dwell_s"])
    if details:
        return np.array(out), np.array(log)
    return np.array(out)


def build_library(p, rng, n_per_dir, regen=True, speed_kmh=None):
    """Library of train runs for both directions (independent samples)."""
    pp = dict(p)
    if speed_kmh is not None:
        pp["v_line_kmh"] = speed_kmh
    edges, grades = p["_grade_edges"], p["_grades"]
    # the opposite direction sees the reversed, negated profile
    L = p["zone_length_m"]
    edges_r = (L - edges[::-1])
    grades_r = -grades[::-1]
    lib = []
    for d, (e, g) in enumerate([(edges, grades), (edges_r, grades_r)]):
        runs = []
        for _ in range(n_per_dir):
            stop = rng.random() < p["p_stop"]
            restr = None
            if rng.random() < p["p_restriction"]:
                x1 = rng.uniform(3000.0, L - 8000.0)
                x2 = x1 + rng.uniform(*p["restriction_len_m"])
                restr = (x1, x2, rng.uniform(*p["restriction_v_kmh"]) / 3.6)
            mf = rng.uniform(*p["mass_factor"])
            runs.append(run_train(pp, rng, e, g, stop, restr, mf, regen=regen))
        lib.append(runs)
    return lib
