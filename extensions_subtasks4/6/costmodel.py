"""Hardware cost model for the RPC (round 4, agent 6).  All money in kUSD, C = leg rating in MVA.

Unit price of the paper (150 kUSD per MVA of leg rating, 2 legs) is taken to cover: the two single-phase converter
legs (semiconductors, gate drives, cooling, control/protection, installation and commissioning) and their DC link at
the baseline energy constant H_dc = 8 ms.  NOT covered (added here): (i) the two coupling transformers 27.5/2.0 kV
rated C each, (ii) DC-link energy beyond 8 ms, (iii) the optional 100 Hz series LC filter, (iv) any Scott up-rating.
Case 'II' (transformers already in the unit price) is a sensitivity.
"""
import json, os, math

CRF = 0.10185
W_YEAR = 52.14
W1_BASE = 2 * 150.0 * CRF            # 30.555 kUSD/(MVA yr)   (two legs)
PRICE_E = 80.0                       # USD/MWh
W3 = 2.0                             # kUSD per %.h
V0 = 3.5                             # kV nominal DC voltage
C_REF = 11.27                        # MVA, design the filter was sized for (subtasks3/2)

# ---- unit costs: (low, central, high); see UNIT_SOURCES --------------------------------------------------------
UNIT = dict(
    c_T=(10.0, 30.0, 100.0),         # kUSD/MVA of coupling transformer (27.5/2.0 kV, rating C each)
    c_W=(0.15, 0.7, 3.0),            # USD/J of rated capacitor energy (kUSD per kJ)
    c_L=(10.0, 20.0, 40.0),          # kUSD/MVAr of reactor (reactive rating at 100 Hz)   [low/high = x0.5 / x2 sensitivity]
)

# ---- filter / DC-link geometry (subtasks3/2: ripple_results.json, derivation.md) ----------------------------------
CF_mF_REF = 10.0                     # mF at C_REF, scales with C (ripple current ~ C, same relative ripple)
I_F_kA_REF = 4.54                    # filter current kA rms at full transfer, C_REF
LF_mH_REF = 0.253
P_FILTER_MW_REF = 0.109              # filter loss at full transfer, C_REF (Q = 30)
VR_FILTER_kV = 5.0                   # filter-capacitor voltage rating (DC 3.85 kV + 1.02 kV ac peak = 4.87 kV)
VR_DC_kV = 3.85                      # DC-link capacitor rating (upper band edge)
H_BASE_ms = 8.0
H_MOD_ms = 26.2                      # H_dc such that Vdc,min >= 3.28 kV (modulation limit) with ripple only, see hdc_required()
H_BAND_ms = 16.8                     # H_dc such that ripple alone stays within +-10 % (no modulation margin)


def filter_capacitor_kJ(C):
    return 0.5 * CF_mF_REF * C / C_REF * 1e-3 * (VR_FILTER_kV * 1e3) ** 2 / 1e3     # kJ (rated)


def filter_reactive_Mvar(C):
    w = 2 * math.pi * 100.0
    return (I_F_kA_REF * 1e3 * C / C_REF) ** 2 * w * (LF_mH_REF * 1e-3 * C_REF / C) / 1e6


def hdc_required(vmin_kV=3.28, C=1.0):
    """H_dc (ms) for which the 100 Hz ripple alone keeps Vdc >= vmin (energy ripple amplitude A/(2*w), A = 2C)."""
    w = 2 * math.pi * 50.0
    ripple_kJ_per_MVA = 2.0 / (2 * w) * 1e3                      # MVA*s -> kJ per MVA (35.9 kJ at 11.27 MVA / 11.27)
    ratio = 1 - (vmin_kV / V0) ** 2
    return ripple_kJ_per_MVA / ratio                              # ms (kJ/MVA == ms)


def hardware(opt, level="central", C=1.0, trafo=True, scott_extra_MVA=0.0, H_ms=None):
    """Capital cost (kUSD installed) of the added items per C; opt in {'none','filter','dc'}; returns dict of items for rating C."""
    k = {"low": 0, "central": 1, "high": 2}[level]
    cT, cW, cL = UNIT["c_T"][k], UNIT["c_W"][k], UNIT["c_L"][k]
    items = {}
    items["transformers"] = (2 * C * cT if trafo else 0.0)
    items["scott_uprating"] = scott_extra_MVA * cT
    if opt == "filter":
        items["filter_C"] = filter_capacitor_kJ(C) * cW
        items["filter_L"] = filter_reactive_Mvar(C) * cL
    elif opt == "dc":
        H = H_MOD_ms if H_ms is None else H_ms
        dW = (H - H_BASE_ms) * C                                   # kJ
        items["dc_link_extra"] = dW * (VR_DC_kV / V0) ** 2 * cW
    return items


def a_hw(opt, level="central", trafo=True, H_ms=None):
    """Annualised hardware cost per MVA of C (kUSD/(MVA yr)) (Scott up-rating excluded: constant, see scott_const)."""
    it = hardware(opt, level, 1.0, trafo, 0.0, H_ms)
    return CRF * sum(it.values())


def scott_const(level="central", extra_MVA=0.0):
    return CRF * extra_MVA * UNIT["c_T"][{"low": 0, "central": 1, "high": 2}[level]]


def filter_loss_coeff():
    return P_FILTER_MW_REF / C_REF                                # MW per (MVA^2/MVA): P = coeff * sx^2 / C


def load_decision():
    f = "/home/claude/subtasks4/2/decision.json"
    return json.load(open(f)) if os.path.exists(f) else None


if __name__ == "__main__":
    print("W1", W1_BASE, "Hdc for 3.28 kV", hdc_required(3.28), "for 3.15", hdc_required(3.15), "for +-10%: ", hdc_required(3.15))
    for o in ("none", "filter", "dc"):
        for lv in ("low", "central", "high"):
            it = hardware(o, lv, C_REF)
            print(o, lv, {k: round(v, 1) for k, v in it.items()}, "total", round(sum(it.values()), 1), "annual", round(CRF * sum(it.values()), 1),
                  "a_hw", round(a_hw(o, lv), 3))
    print("filter cap kJ", filter_capacitor_kJ(C_REF), "Mvar", filter_reactive_Mvar(C_REF), "loss coeff", filter_loss_coeff())
