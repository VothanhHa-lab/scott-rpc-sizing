"""Regeneration scenarios (item c).

1. clip_variants(): lumped substation, no return to the 110 kV grid (net negative substation power clipped, the
   excess is burned in brake resistors) -- two variants of the reactive power.
2. catenary_week(): position-dependent catenary: radial feeder with the substation at x_s, two arms, resistive
   equivalent z (ohm/km) for the double-track line with tied tracks, constant-power trains, pantograph voltage
   limited to U_max (regeneration is reduced until U_p <= U_max), optional common curtailment so that the
   substation does not return power to the grid.  Fixed-point load flow, vectorised over the active seconds.
Simplifications (stated in the manuscript text): purely resistive equivalent line impedance, no voltage-dependent
traction power derating, trains draw constant power at the pantograph, reactive power of the trains only.
"""
import sys
import numpy as np
sys.path.insert(0, "/home/claude/code")
from rpc_sizing.params import feeder_rx

UNOM_SUB = 27.5          # kV, no-load voltage of the substation busbar (EN 50163 highest permanent voltage)
UMAX = 29.0              # kV, highest non-permanent voltage (EN 50163), limit used for regeneration
KMAX = 24


def clip_variants(P, Q, Sp, Sn, tanphi):
    """Return dict name -> (P, Q, energy accounting in MWh) for the weekly record."""
    P = P.astype(float); Q = Q.astype(float); Sp = Sp.astype(float); Sn = Sn.astype(float)
    absorbed = np.minimum(Sp, Sn)
    ret = np.maximum(Sn - Sp, 0.0)
    h = 3600.0
    acc = dict(regen_avail=Sn.sum() / h, absorbed_trains=absorbed.sum() / h, returned=ret.sum() / h,
               traction=Sp.sum() / h)
    out = {}
    out["v7"] = (P, Q, dict(acc, curtailed=0.0))
    Pc = np.maximum(P, 0.0)
    Qon = tanphi * (Sp + absorbed)                # regenerating trains reduce their current: Q follows
    out["noreturn_onboard"] = (Pc, Qon, dict(acc, returned=0.0, curtailed=ret.sum() / h))
    out["noreturn_wayside"] = (Pc, Q, dict(acc, returned=0.0, curtailed=ret.sum() / h))
    return out


def catenary_flow(P0, d, arm, act, Ssc, tanphi, z=0.2, umax=UMAX, no_return=False, n_iter=40, tol=1e-4):
    """P0, d, arm, act: arrays [T, K] (MW nominal pantograph power, + traction; km from the substation;
    arm in {0,1}; active mask).  Returns dict of per-second vectors."""
    T, K = P0.shape
    r, x = feeder_rx(Ssc)
    Pn = np.where(act, P0, 0.0)
    reg = (Pn < 0)
    alpha = np.ones((T, K))
    beta = np.ones(T)
    Us = np.full(T, UNOM_SUB)
    # sorted structure per arm
    order = []
    for a in (0, 1):
        m = act & (arm == a)
        dd = np.where(m, d, 1e3)
        o = np.argsort(dd, axis=1)
        order.append((o, np.take_along_axis(dd, o, 1), np.take_along_axis(m, o, 1)))
    for it in range(n_iter):
        Pt = np.where(reg, Pn * alpha * beta[:, None], Pn)
        U = np.zeros((T, K)); Isub = np.zeros(T); loss = np.zeros(T)
        Uarm = []
        for a in (0, 1):
            o, ds, m = order[a]
            Ps = np.take_along_axis(Pt, o, 1) * m
            # fixed point for the voltages of this arm
            Uj = np.full((T, K), 0.0) + Us[:, None]
            for _ in range(4):
                I = Ps / np.maximum(Uj, 5.0)                       # kA (MW/kV)
                Icum = np.cumsum(I[:, ::-1], axis=1)[:, ::-1]
                dlt = np.diff(ds, axis=1, prepend=0.0)
                drop = z * dlt * Icum * (ds < 999)
                Uj = Us[:, None] - np.cumsum(drop, axis=1)
            Uarm.append((Uj, I, Icum, dlt))
            Isub += Icum[:, 0]
            loss += (z * dlt * Icum ** 2 * (ds < 999)).sum(axis=1)
        Psub = Us * Isub                                            # MW (includes the line losses)
        Qsub = tanphi * np.abs(Pt).sum(axis=1)
        Us_new = UNOM_SUB * (1.0 - (r * Psub + x * Qsub))
        # regeneration: pantograph voltage limit (Newton step on the regeneration factor)
        dmax = 0.0
        alpha_new = alpha.copy()
        for a in (0, 1):
            o, ds, m = order[a]
            Uj, I, Icum, dlt = Uarm[a]
            al = np.take_along_axis(alpha, o, 1)
            rg = np.take_along_axis(reg, o, 1) & m
            I0 = np.abs(np.take_along_axis(Pn, o, 1)) / np.maximum(Uj, 5.0)
            sens = np.maximum(z * ds * I0 * np.take_along_axis(beta[:, None] * np.ones((T, K)), o, 1), 1e-6)
            step = np.where(rg & (ds > 1e-6), 0.8 * (Uj - umax) / sens, 0.0)
            an = np.clip(al - step, 0.0, 1.0)
            dmax = max(dmax, float(np.abs(an - al)[rg].max()) if rg.any() else 0.0)
            # scatter back
            tmp = np.take_along_axis(alpha_new, o, 1)
            tmp = np.where(rg, an, tmp)
            np.put_along_axis(alpha_new, o, tmp, 1)
        alpha = alpha_new
        if no_return:
            R = np.where(reg, np.abs(Pn) * alpha, 0.0).sum(axis=1)
            beta_new = np.clip(beta + np.where(R > 1e-9, Psub / np.maximum(R, 1e-9), 0.0), 0.0, 1.0)
            dmax = max(dmax, float(np.abs(beta_new - beta).max()))
            beta = beta_new
        dU = float(np.abs(Us_new - Us).max())
        Us = 0.5 * Us + 0.5 * Us_new
        if dmax < tol and dU < 1e-4 and it > 3:
            break
    # final consistent evaluation of per-train voltages
    Pt = np.where(reg, Pn * alpha * beta[:, None], Pn)
    Pdel_reg = np.where(reg, -Pt, 0.0).sum(axis=1)
    Pnom_reg = np.where(reg, -Pn, 0.0).sum(axis=1)
    Ptrac = np.where(~reg, Pt, 0.0).sum(axis=1)
    umaxseen = np.zeros(T)
    for a in (0, 1):
        o, ds, m = order[a]
        Uj = Uarm[a][0]
        umaxseen = np.maximum(umaxseen, np.where(m, Uj, 0).max(axis=1))
    Uminseen = np.full(T, 99.0)
    for a in (0, 1):
        o, ds, m = order[a]
        Uminseen = np.minimum(Uminseen, np.where(m, Uarm[a][0], 99.0).min(axis=1))
    return dict(Psub=Psub, Qsub=Qsub, loss=loss, Ptrac=Ptrac, reg_del=Pdel_reg, reg_nom=Pnom_reg, Us=Us,
                Umax=umaxseen, Umin=Uminseen, iters=it + 1, resid=dict(alpha=dmax))


def build_slots(lib, trains, L_m, N=7 * 24 * 3600, K=KMAX):
    P0 = np.zeros((N, K), np.float32); X = np.zeros((N, K), np.float32); act = np.zeros((N, K), bool)
    cnt = np.zeros(N, np.int16)
    for (d, i0, ri) in trains:
        run, xr = lib[d][ri]
        i1 = min(i0 + len(run), N); n = i1 - i0
        idx = np.arange(i0, i1)
        sl = cnt[i0:i1].astype(int)
        if sl.max() >= K:
            raise RuntimeError("KMAX exceeded")
        P0[idx, sl] = run[:n]
        X[idx, sl] = (xr[:n] if d == 0 else L_m - xr[:n])
        act[idx, sl] = True
        cnt[i0:i1] += 1
    return P0, X / 1000.0, act, int(cnt.max())


def catenary_week(P0, X, act, kmax, x_s_km, Ssc, tanphi, z=0.2, umax=UMAX, no_return=False, chunk=60000, **kw):
    N = P0.shape[0]
    keys = ["Psub", "Qsub", "loss", "Ptrac", "reg_del", "reg_nom", "Us", "Umax", "Umin"]
    out = {k: np.zeros(N) for k in keys}
    out["Umin"][:] = np.nan; out["Umax"][:] = np.nan
    used = act[:, :kmax].any(axis=1)
    idx = np.where(used)[0]
    its = []
    for s in range(0, len(idx), chunk):
        ii = idx[s:s + chunk]
        p = P0[ii, :kmax].astype(float); xx = X[ii, :kmax].astype(float); ac = act[ii, :kmax]
        d = np.abs(xx - x_s_km); arm = (xx >= x_s_km).astype(int)
        r = catenary_flow(p, d, arm, ac, Ssc, tanphi, z=z, umax=umax, no_return=no_return, **kw)
        for k in keys:
            out[k][ii] = r[k]
        its.append(r["iters"])
    out["iters"] = its
    return out
