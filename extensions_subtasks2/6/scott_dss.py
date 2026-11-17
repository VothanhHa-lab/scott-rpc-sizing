"""Scott substation in OpenDSS (opendssdirect.py), independent check of the
Python phasor model (rpc_sizing/network.py) and of eq. (7)-(8).

Topology (all elements are standard OpenDSS objects, no custom maths):
  Vsource 110 kV, MVAsc3 = MVAsc1 = Ssc, X1R1 = 10, 50 Hz   (A-B-C, positive sequence)
  bus 'pcc'  nodes 1,2,3 = A,B,C ; node 4 = centre tap of the main-transformer primary
  T_main : single-phase 3-winding transformer
              W1  pcc.2.4  55 kV  (half of the primary, phase B -> tap)
              W2  pcc.4.3  55 kV  (other half,          tap -> phase C)
              W3  fa.1.0   27.5 kV  = feeder alpha
  T_tsr  : single-phase 2-winding transformer (teaser)
              W1  pcc.1.4  95.263 kV (= sqrt(3)/2 * 110 kV, phase A -> tap)
              W2  fb.1.0   27.5 kV  = feeder beta
  Leakage: uk = 10.5 %, X/R = 30 on 40 MVA, 27.5 kV side per leg (set via %R/X% in the
  transformer objects; verified by an explicit short-circuit test, see sc_test()).
Loads: model 1 (constant P,Q), model 2 (constant Z at 27.5 kV), or 'Isource' (fixed
current phasor, ideal current source).  RPC: load S_L at alpha + generator s_x at alpha
+ load s_x at beta (constant power, ideal lossless transfer).
"""
import numpy as np
import opendssdirect as dss

KV_P, KV_S = 110.0, 27.5
XR_SRC, XR_LEG = 10.0, 30.0
LEG_MVA, UK = 40.0, 0.105
A = np.exp(2j * np.pi / 3)


def _run(cmd):
    dss.Text.Command(cmd)


def leg_rx_percent():
    """Series R and X of a leg in % on the 40 MVA base (uk=10.5 %, X/R=30)."""
    z = UK * 100.0
    r = z / np.sqrt(1 + XR_LEG ** 2)
    x = z * XR_LEG / np.sqrt(1 + XR_LEG ** 2)
    return r, x


def build(Ssc, loads, mode="xfmr"):
    """loads: list of dicts(bus, node, kW, kvar, kind in {'PQ','Z','I','GEN'}).
    mode 'xfmr': leakage inside the transformers; 'series': ideal transformers + explicit
    series R-L lines on the secondary side."""
    dss.Basic.ClearAll()
    _run("set DefaultBaseFrequency=50")
    _run("new circuit.scott basekv=110 pu=1.0 phases=3 bus1=pcc "
         f"MVAsc3={Ssc} MVAsc1={Ssc} x1r1={XR_SRC} x0r0={XR_SRC} angle=0")
    r, x = leg_rx_percent()
    if mode == "xfmr":
        # Winding-pair reactances referred to W1 kVA; the two primary halves carry the same current,
        # the leakage is put entirely in the secondary winding: z1 = z2 = 0 (tiny), z3 = uk.
        # All three windings are given kVA = 40000 so that the per-unit bases of %R and X are unambiguous
        # (OpenDSS takes the impedance base from the winding kVA; the value is checked by sc_test()).
        eps = 1e-4
        _run(f"new transformer.tmain phases=1 windings=3 "
             f"buses=[pcc.2.4, pcc.4.3, fa.1.0] conns=[wye,wye,wye] kVs=[55,55,27.5] "
             f"kVAs=[40000,40000,40000] %Rs=[{eps},{eps},{r}] "
             f"xhl={eps} xht={x} xlt={x} %noloadloss=0 %imag=0")
        _run(f"new transformer.ttsr phases=1 windings=2 "
             f"buses=[pcc.1.4, fb.1.0] conns=[wye,wye] kVs=[95.2628,27.5] "
             f"kVAs=[40000,40000] %Rs=[{eps},{r}] xhl={x} %noloadloss=0 %imag=0")
        fa, fb = "fa", "fb"
    else:
        eps = 1e-4
        zb = KV_S ** 2 / LEG_MVA                      # ohm, 27.5 kV / 40 MVA
        R_leg, X_leg = r / 100 * zb, x / 100 * zb
        _run(f"new transformer.tmain phases=1 windings=3 "
             f"buses=[pcc.2.4, pcc.4.3, fa0.1.0] conns=[wye,wye,wye] kVs=[55,55,27.5] "
             f"kVAs=[20000,20000,40000] %Rs=[{eps},{eps},{eps}] "
             f"xhl={eps} xht={eps} xlt={eps} %noloadloss=0 %imag=0")
        _run(f"new transformer.ttsr phases=1 windings=2 "
             f"buses=[pcc.1.4, fb0.1.0] conns=[wye,wye] kVs=[95.2628,27.5] "
             f"kVAs=[40000,40000] %Rs=[{eps},{eps}] xhl={eps} %noloadloss=0 %imag=0")
        _run(f"new line.za phases=1 bus1=fa0.1 bus2=fa.1 r1={R_leg} x1={X_leg} r0={R_leg} x0={X_leg} length=1 units=none")
        _run(f"new line.zb phases=1 bus1=fb0.1 bus2=fb.1 r1={R_leg} x1={X_leg} r0={R_leg} x0={X_leg} length=1 units=none")
        fa, fb = "fa", "fb"
    _run(f"set voltagebases=[110, 27.5]")
    # loads / sources
    for i, L in enumerate(loads):
        bus = fa if L["bus"] == "a" else fb
        kind = L["kind"]
        P, Q = L["kW"], L["kvar"]
        if kind in ("PQ", "Z"):
            model = 1 if kind == "PQ" else 2
            if abs(P) + abs(Q) == 0:
                continue
            _run(f"new load.l{i} phases=1 bus1={bus}.1 kV={KV_S} kW={P} kvar={Q} model={model} "
                 f"vminpu=0.2 vmaxpu=3 status=fixed")
        elif kind == "GEN":
            if abs(P) + abs(Q) == 0:
                continue
            _run(f"new generator.g{i} phases=1 bus1={bus}.1 kV={KV_S} kW={P} kvar={Q} model=1 "
                 f"vminpu=0.2 vmaxpu=3")
        elif kind == "I":
            # fixed current phasor drawn from the node: i = conj(S / u0) (kA, kV, MW -> kA).
            u0 = L["u0_kV"]                          # complex no-load feeder voltage (kV)
            S = complex(P, Q) / 1000.0               # MVA
            I = np.conj(S / u0) * (1.0 if L.get("sign", 1) > 0 else -1.0)  # kA, drawn from node
            amps = -I * 1000.0                       # Isource injects into the node: -drawn
            if abs(amps) == 0:
                continue
            _run(f"new isource.i{i} bus1={bus}.1 amps={abs(amps)} angle={np.degrees(np.angle(amps))} "
                 f"phases=1 frequency=50")
    _run("set controlmode=off")
    _run("set maxiter=200")
    _run("set tolerance=1e-10")
    _run("solve mode=snap")


def seq(v):
    v = np.asarray(v)
    return ((v[0] + A * v[1] + A ** 2 * v[2]) / 3, (v[0] + A ** 2 * v[1] + A * v[2]) / 3)


def results(Ssc):
    dss.Circuit.SetActiveBus("pcc")
    v = np.array(dss.Bus.Voltages(), float).reshape(-1, 2)
    nodes = dss.Bus.Nodes()
    vp = {n: complex(*vv) for n, vv in zip(nodes, v)}
    U = np.array([vp[1], vp[2], vp[3]])
    # primary phase currents = source element currents (into the circuit)
    dss.Circuit.SetActiveElement("vsource.source")
    cur = np.array(dss.CktElement.Currents(), float).reshape(-1, 2)
    Iph = np.array([complex(*cur[0]), complex(*cur[1]), complex(*cur[2])])  # leaving source into pcc
    U1, U2 = seq(U)
    I1, I2 = seq(Iph)
    out = dict(VUF_pct=abs(U2) / abs(U1) * 100.0, IUF_pct=(abs(I2) / abs(I1) * 100.0 if abs(I1) > 0 else float("nan")),
               V1_pcc_kVll=abs(U1) * np.sqrt(3) / 1000.0)
    # feeder terminal powers
    for tag, bus in (("a", "fa"), ("b", "fb")):
        dss.Circuit.SetActiveBus(bus)
        vv = np.array(dss.Bus.Voltages(), float).reshape(-1, 2)
        vn = {n: complex(*x) for n, x in zip(dss.Bus.Nodes(), vv)}
        out[f"U{tag}_kV"] = vn[1] / 1000.0
    out["converged"] = bool(dss.Solution.Converged())
    out["iterations"] = int(dss.Solution.Iterations())
    # feeder power from the transformer secondary terminal (winding at the feeder bus)
    return out, U, Iph


def sc_test(mode="xfmr", Ssc=1e7):
    """Leg-impedance test on a stiff source: inject a known current into each feeder in turn and
    compare the voltage drop with z_T = uk*(1+j*30)/sqrt(1+900) * 27.5^2/40 ohm."""
    out = {}
    zref = UK * KV_S ** 2 / LEG_MVA * (1 + 1j * XR_LEG) / np.sqrt(1 + XR_LEG ** 2)
    for leg in ("a", "b"):
        loads = [dict(bus=leg, kW=0, kvar=0, kind="PQ")]
        build(Ssc, loads, mode)
        res0, _, _ = results(Ssc)
        u0 = res0["U%s_kV" % leg] * 1000.0
        I = 1000.0                                    # A drawn from the feeder node (angle 0)
        _run(f"new isource.itest bus1={'fa' if leg=='a' else 'fb'}.1 amps={I} angle=180 phases=1 frequency=50")
        _run("solve mode=snap")
        res1, _, _ = results(Ssc)
        u1 = res1["U%s_kV" % leg] * 1000.0
        z = (u0 - u1) / I
        out[leg] = dict(z_meas_ohm=complex(z), z_ref_ohm=complex(zref), rel_err=abs(z - zref) / abs(zref))
    return out


def feeder_powers():
    """Complex power (MVA) drawn from each feeder terminal, from the transformer winding currents."""
    out = {}
    for tag, tr, idx in (("a", "tmain", 4), ("b", "ttsr", 2)):
        dss.Circuit.SetActiveElement(f"transformer.{tr}")
        cur = np.array(dss.CktElement.Currents(), float).reshape(-1, 2)
        I_tr = complex(*cur[idx])                    # current INTO the transformer at the feeder terminal (A)
        dss.Circuit.SetActiveBus("fa" if tag == "a" else "fb")
        vv = np.array(dss.Bus.Voltages(), float).reshape(-1, 2)
        vn = {n: complex(*x) for n, x in zip(dss.Bus.Nodes(), vv)}
        V = vn[1]
        out[tag] = V * np.conj(-I_tr) / 1e6          # VA -> MVA, drawn from the node by the load
    return out
