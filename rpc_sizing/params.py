"""Planning assumptions of the case study (all values are assumptions,
not data of a specific line or rolling stock)."""
import numpy as np

TRAIN = dict(
    mass_t=450.0,            # 8-car EMU incl. average passenger load
    rot_factor=1.06,         # rotating-mass factor
    davis_A=4.0,             # kN
    davis_B=0.030,           # kN/(km/h)
    davis_C=0.00075,         # kN/(km/h)^2
    F_max_kN=280.0,          # maximum tractive effort
    P_wheel_max_MW=8.8,      # maximum traction power at the wheel
    P_reg_wheel_max_MW=9.0,  # maximum electric-brake power at the wheel
    P_reg_el_max_MW=8.0,     # limit of power returned to the catenary
    eta_t=0.85,              # catenary-to-wheel efficiency in traction
    eta_r=0.85,              # wheel-to-catenary efficiency in braking
    P_aux_MW=0.30,           # auxiliary load
    b_service=0.50,          # service deceleration (m/s^2)
    b_max=0.90,              # maximum braking deceleration (m/s^2)
    dF_max_kN_s=60.0,        # tractive-effort rate limit (jerk limitation)
    pf=0.998,                # 4QC displacement factor (section 3.3)
    zone_length_m=50000.0,   # double-track zone fed by the substation
    v_line_kmh=300.0,
    station_x_m=25000.0,     # station in the middle of the zone
    p_stop=0.25,             # share of trains stopping at the station
    dwell_s=(90.0, 180.0),
    p_restriction=0.15,      # share of runs with a temporary speed restriction
    restriction_len_m=(2000.0, 5000.0),
    restriction_v_kmh=(160.0, 230.0),
    mass_factor=(0.95, 1.05),
    coast_lookahead_m=4000.0,
)

TIMETABLE = dict(
    t_start_h=6.0, t_end_h=24.0,
    peak_hours=[(7, 9), (17, 20)],
    n_peak=8, n_off=4,        # trains per hour and direction
    delay_mean_s=180.0,       # exponential delay
    delay_max_s=1200.0,
    days=7,
)

GRID = dict(
    Ssc_MVA=750.0,            # base case short-circuit power at the PCC
    vuf_lim=2.0,              # %
    # Thevenin resistance/reactance of feeder alpha (pu on 1 MVA, at the
    # 27.5 kV busbar): grid (Ssc/2 per feeder, X/R=10) + Scott leg 40 MVA,
    # uk=10.5 %, X/R=30. Used only for the busbar-voltage / current limit.
    trafo_leg_MVA=40.0, uk=0.105,
)

RPC = dict(
    k0=0.003, k1=0.006, k2=0.006,   # per-leg loss model (pu of rating)
    cost_kUSD_per_MVA=150.0,        # installed cost per MVA of leg rating
    crf=0.10185,                    # capital recovery factor (8 %, 20 yr)
    energy_price_USD_MWh=80.0,
    viol_price_kUSD_per_pct_h=2.0,  # penalty on VUF exceedance above limit
    weeks_per_year=52.14,
    Vdc_ref=3500.0, Vdc_min=3150.0, Vdc_max=3850.0,   # +/-10 %
    H_dc_ms=8.0,                    # DC-link energy constant at rated power
    tau_i=2e-3,                     # closed-loop current time constant (s)
    f_dc=15.0,                      # DC-energy loop bandwidth (Hz)
)

SEED0 = 20261111


def feeder_rx(Ssc):
    """Return r, x of feeder alpha in pu per MVA (voltage drop dU ~ rP+xQ)."""
    zg = 1.0 / (Ssc / 2.0)
    rg, xg = zg / np.sqrt(1 + 10 ** 2), zg * 10 / np.sqrt(1 + 10 ** 2)
    zt = GRID["uk"] / GRID["trafo_leg_MVA"]
    rt, xt = zt / np.sqrt(1 + 30 ** 2), zt * 30 / np.sqrt(1 + 30 ** 2)
    return rg + rt, xg + xt
