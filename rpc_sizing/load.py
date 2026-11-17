"""Weekly substation load S_L(t) = P_L + jQ_L (1 s resolution).

Two arrival models are available:
  'timetable' - periodic departures (n trains/h/direction) with exponential
                delays (correlated, timetable-based operation; base case);
  'poisson'   - independent Poisson arrivals with the same hourly rates
                (assumption of the previous version of the study).
A third, 'segments', reproduces the previous load model (independent random
power per 60 s segment) for comparison.
"""
import numpy as np
from .params import TRAIN, TIMETABLE
from . import train as tr


def hourly_rate(h, tt, freq_factor=1.0):
    peak = any(a <= h < b for a, b in tt["peak_hours"])
    return (tt["n_peak"] if peak else tt["n_off"]) * freq_factor


def entry_times(rng, tt, model="timetable", freq_factor=1.0):
    """Entry times (s from the start of the week) for one direction."""
    times = []
    for d in range(tt["days"]):
        for h in range(int(tt["t_start_h"]), int(tt["t_end_h"])):
            n = hourly_rate(h, tt, freq_factor)
            t0 = (d * 24 + h) * 3600.0
            if model == "timetable":
                n_int = int(round(n))
                if n_int == 0:
                    continue
                hw = 3600.0 / n_int
                off = rng.uniform(0, hw)
                base = t0 + off + hw * np.arange(n_int)
                delay = np.minimum(rng.exponential(tt["delay_mean_s"], n_int),
                                   tt["delay_max_s"])
                times.extend(base + delay)
            else:  # poisson
                k = rng.poisson(n)
                times.extend(t0 + np.sort(rng.uniform(0, 3600.0, k)))
    return np.sort(np.array(times))


def week_load_pq(rng, lib, model="timetable", freq_factor=1.0, pf=None,
                 power_scale=1.0, tt=None):
    """Return P_L and Q_L (MW, Mvar) at 1 s for one simulated week."""
    tt = dict(TIMETABLE, **(tt or {}))
    pf = TRAIN["pf"] if pf is None else pf
    tanphi = np.tan(np.arccos(pf))
    N = tt["days"] * 24 * 3600
    P = np.zeros(N)
    Q = np.zeros(N)
    for d in range(2):
        for te in entry_times(rng, tt, model, freq_factor):
            run = lib[d][rng.integers(len(lib[d]))] * power_scale
            i0 = int(te)
            if i0 >= N:
                continue
            i1 = min(i0 + len(run), N)
            seg = run[: i1 - i0]
            P[i0:i1] += seg
            Q[i0:i1] += tanphi * np.abs(seg)
    return P, Q


def week_load_segments(rng, pf=0.998, regen_share=0.2):
    """Previous load model: Poisson arrivals, 600 s residence, random power
    per 60 s segment (4-9 MW traction or -2 to -8 MW braking)."""
    tt = TIMETABLE
    tanphi = np.tan(np.arccos(pf))
    N = tt["days"] * 24 * 3600
    P = np.zeros(N)
    Q = np.zeros(N)
    for d in range(2):
        for te in entry_times(rng, tt, "poisson"):
            seg = []
            for _ in range(10):
                if rng.random() < regen_share:
                    seg.append(np.full(60, -rng.uniform(2, 8)))
                else:
                    seg.append(np.full(60, rng.uniform(4, 9)))
            run = np.concatenate(seg)
            i0 = int(te)
            if i0 >= N:
                continue
            i1 = min(i0 + 600, N)
            P[i0:i1] += run[: i1 - i0]
            Q[i0:i1] += tanphi * np.abs(run[: i1 - i0])
    return P, Q
