"""ctypes wrapper of phasor_c2.c: as fastsolve.py but also returns |u_alpha|, |u_beta| (feeder-terminal voltage
magnitudes, pu, of the last sweep = second return value of rpc_sizing.network.solve)."""
import ctypes, os
import numpy as np
from rpc_sizing.network import _z, E
from rpc_sizing.params import GRID

_lib = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libphasor2.so"))
_cp = np.ctypeslib.ndpointer(np.complex128, flags="C_CONTIGUOUS")
_dp = np.ctypeslib.ndpointer(np.float64, flags="C_CONTIGUOUS")
_lib.solve_c.argtypes = [ctypes.c_int, _cp, _cp, ctypes.c_double * 2, ctypes.c_double * 2, _cp, ctypes.c_int,
                         ctypes.c_double, _cp, _dp, _dp, _dp]
_lib.solve_c.restype = None


def _c2(z):
    return (ctypes.c_double * 2)(z.real, z.imag)


def solve_fast2(S_alpha, S_beta, Ssc, S_b=100.0, n_iter=10, tol=1e-6):
    Zs = _z(S_b / Ssc, 10.0)
    zT = _z(GRID["uk"] * S_b / GRID["trafo_leg_MVA"], 30.0)
    sa = np.ascontiguousarray(np.asarray(S_alpha, complex) / S_b)
    sb = np.ascontiguousarray(np.asarray(S_beta, complex) / S_b)
    n = sa.size
    ratio = np.empty(n, complex); vuf = np.empty(n); ua = np.empty(n); ub = np.empty(n)
    Ec = np.ascontiguousarray(np.asarray(E, complex))
    _lib.solve_c(n, sa, sb, _c2(zT), _c2(Zs), Ec, n_iter, tol, ratio, vuf, ua, ub)
    return ratio, vuf, ua, ub
