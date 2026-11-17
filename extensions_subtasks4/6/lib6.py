"""Candidate sets (exact / approximate model) with per-candidate means and the hardware-extended objective."""
import sys, json, os
sys.dont_write_bytecode = True
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import costmodel as cm

CODE = "/home/claude/code"
RES = "/home/claude/subtasks4/6/results"
W = cm.W_YEAR
LIM = 2.0


class Cand:
    __slots__ = ("eps", "C", "comply", "Ev", "El", "F", "src", "n")

    def __init__(self, eps, C, comply, Ev, El, F, src, n=60):
        self.eps, self.C, self.comply, self.Ev, self.El, self.F, self.src, self.n = eps, C, comply, Ev, El, F, src, n


def _key(e, C):
    return (round(float(e), 4), round(float(C), 4))


def load_sx(name):
    f = f"{RES}/sx_{name}.json"
    if not os.path.exists(f):
        return {}
    d = json.load(open(f))
    return {_key(e, C): float(np.mean(d["F"][i])) for i, (e, C) in enumerate(d["cands"])}


def exact_approx_designs():
    """The two approximation-(8) designs of v7 Table tEx evaluated with the exact model (subtasks3/4/exact_refine.json)."""
    r = json.load(open("/home/claude/subtasks3/4/exact_refine.json"))["new"]
    sx2 = load_sx("exact_refine")
    out = {}
    for x in r:
        if x["eps"] == 2.0 or abs(x["C"] - 10.4387) < 1e-6:
            out["pct12" if x["eps"] == 2.0 else "prop8"] = Cand(x["eps"], x["C"], x["n_comply"] / 60.0, x["Jviol"] / (2.0 * W),
                                                               x["Jloss"] / (0.08 * W), sx2.get(_key(x["eps"], x["C"]), np.nan), "exact_refine")
    return out


def exact_set(extra_files=()):
    d = json.load(open(f"{CODE}/results_exact/stepA2.json"))
    sx = load_sx("exact_stored")
    out = []
    for i, (e, C) in enumerate(d["cands"]):
        w = [x[i] for x in d["evals"]]
        out.append(Cand(e, C, float(np.mean([x["p95"] <= LIM + 1e-9 for x in w])), float(np.mean([x["E_viol"] for x in w])),
                        float(np.mean([x["E_loss"] for x in w])), sx.get(_key(e, C), np.nan), "stepA2"))
    r = json.load(open("/home/claude/subtasks3/4/exact_refine.json"))["new"]
    sx2 = load_sx("exact_refine")
    for x in r:
        if x["eps"] == 2.0 or abs(x["C"] - 10.4387) < 1e-6:
            continue                         # approximation-(8) designs, not part of the exact grid
        out.append(Cand(x["eps"], x["C"], x["n_comply"] / 60.0, x["Jviol"] / (2.0 * W), x["Jloss"] / (0.08 * W),
                        sx2.get(_key(x["eps"], x["C"]), np.nan), "exact_refine"))
    for f in extra_files:                     # extra exact evaluations of this agent
        if os.path.exists(f):
            j = json.load(open(f))
            sx3 = load_sx(os.path.basename(f).replace(".json", "").replace("exact_", "sx_exact_").replace("sx_", "")) if False else {}
            for x in j["records"]:
                out.append(Cand(x["eps"], x["C"], x["comply"], x["Ev"], x["El"], x["F"], os.path.basename(f), x.get("n", 60)))
    return out


def approx_set(case="base", Ssc="750", extra_files=(), sxname="approx_stored"):
    base = f"{CODE}/results/base.json" if case == "base" else f"{CODE}/results_sub/suburban.json"
    d = json.load(open(base))["design"][Ssc]
    sx = load_sx(sxname)
    out = []
    for i, (e, C) in enumerate(d["cands"]):
        w = [x[i] for x in d["evals"]]
        out.append(Cand(e, C, float(np.mean([x["p95"] <= LIM + 1e-9 for x in w])), float(np.mean([x["E_viol"] for x in w])),
                        float(np.mean([x["E_loss"] for x in w])), sx.get(_key(e, C), np.nan), "stored", len(w)))
    for f in extra_files:
        if os.path.exists(f):
            j = json.load(open(f))
            for x in j["records"]:
                out.append(Cand(x["eps"], x["C"], x["comply"], x["Ev"], x["El"], x["F"], os.path.basename(f), x.get("n", 60)))
    return out


class Hw:
    """Hardware scenario: opt in none/filter/dc, unit-cost level low/central/high, trafo included in addition to the 150 kUSD/MVA?"""

    def __init__(self, opt="none", level="central", trafo=True, scott_MVA=0.0, H_ms=None, name=None):
        self.opt, self.level, self.trafo, self.scott, self.H = opt, level, trafo, scott_MVA, H_ms
        self.name = name or f"{opt}/{level}/{'T' if trafo else 'noT'}"

    def parts(self, c):
        """Annual kUSD terms of a candidate: dict(cap, hw, loss, filt, viol, capw=cap+hw, caploss= cap+hw+loss+filt, J)."""
        cap = cm.W1_BASE * c.C
        hw = cm.a_hw(self.opt, self.level, self.trafo, self.H) * c.C + cm.scott_const(self.level, self.scott)
        loss = cm.PRICE_E / 1000.0 * c.El * W
        filt = 0.0
        if self.opt == "filter":
            filt = cm.PRICE_E / 1000.0 * cm.filter_loss_coeff() * c.F * W
        viol = cm.W3 * c.Ev * W
        return dict(C=c.C, eps=c.eps, cap=cap, hw=hw, loss=loss, filt=filt, viol=viol, Eviol=c.Ev * W,
                    caploss=cap + hw + loss + filt, J=cap + hw + loss + filt + viol, comply=c.comply)

    def J(self, c):
        return self.parts(c)["J"]

    def CL(self, c):
        return self.parts(c)["caploss"]


def ok(c, thr=0.95):
    return c.comply >= thr - 1e-9
