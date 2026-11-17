"""Shared helpers: stored data windows, defaults (read-only access to /home/claude/code results)."""
import sys, json
sys.path.insert(0, '/home/claude/code')
import numpy as np
from rpc_sizing import rpc as R
from rpc_sizing.params import RPC, GRID

C_STAR = 11.270562480978487   # MVA per leg, exact-phasor design (v7)
EPS_STAR = 1.0
SSC = 750.0
TANPHI = float(np.tan(np.arccos(0.998)))


def week(k, kind='base'):
    if kind == 'base':
        d = np.load(f'/home/claude/code/results/base_w{k:03d}.npz')
    else:
        d = np.load(f'/home/claude/code/results_exact/cert_w{k:03d}.npz')
    return d['P'].astype(float), d['Q'].astype(float)


def window(k, i0, n, kind='base'):
    """n+1 knots (1-s samples) starting at sample i0 of week k (0-based)."""
    P, Q = week(k, kind)
    return P[i0:i0 + n + 1].copy(), Q[i0:i0 + n + 1].copy()


def const(P0, n):
    return np.full(n + 1, float(P0)), np.full(n + 1, float(P0) * TANPHI)
