"""Final metrics table (P95, P99, max, shares, J) for the headline designs + paired statistics."""
from common import *
from scipy import stats
from rpc_sizing.params import RPC
Wk = RPC["weeks_per_year"]
cmp_ = json.load(open(os.path.join(HERE, "compare.json")))
rows = {}
def collect(label, C, runner):
    v10s, evs = [], []
    for k in range(60):
        sx, v = runner(k, C)
        evs.append(evaluate_run(sx, v, C)); v10s.append(rpc.vuf10(np.asarray(v).reshape(-1)))
    v10 = np.concatenate(v10s)
    J = [annual_J(e) for e in evs]
    rows[label] = dict(C=float(C), J=float(np.mean([j[0] for j in J])), Jcap=float(J[0][1]), Jloss=float(np.mean([j[2] for j in J])),
        Jviol=float(np.mean([j[3] for j in J])), comply=float(np.mean([e["p95"] <= 2 + 1e-6 for e in evs])),
        p95_mean=float(np.mean([e["p95"] for e in evs])), p99_pooled=float(np.quantile(v10, 0.99)), p99_weekly_mean=float(np.mean([np.quantile(x, 0.99) for x in v10s])),
        vmax_mean=float(np.mean([e["vmax10"] for e in evs])), vmax_all=float(max(e["vmax10"] for e in evs)),
        share_above=float(np.mean(v10 > 2 + 1e-9) * 100), Eviol=float(np.mean([e["E_viol"] for e in evs]) * Wk),
        Eloss=float(np.mean([e["E_loss"] for e in evs]) * Wk), Etr=float(np.mean([e["E_transfer"] for e in evs]) * Wk),
        sx_over_kappaC=float(max(e["sx_max"] for e in evs) / (KAPPA * C)))
    print(label, {a: round(b, 3) for a, b in rows[label].items()}, flush=True)
raw = {}
def getraw(k):
    if k not in raw:
        raw.clear(); raw[k] = load_week(k)
    return raw[k]
ref = cmp_["ref"]
collect("pct12", ref["p95"]["C"], lambda k, C: (lambda s, v: (s, v))(*rpc.compensate(*getraw(k), C, 2.0, Ssc)))
collect("prop15", ref["proposed"]["C"], lambda k, C: rpc.compensate(*getraw(k), C, 1.0, Ssc))
TAB = {n: fold_tables(n) for n in FOLDS}
fold_of = {k: n for n in FOLDS for k in FOLDS[n][0]}
cache_w = {}
def W_of(k):
    if k not in cache_w:
        cache_w.clear(); P, Q = load_week(k); W = windows(P, Q); cache_w[k] = (W, Feat(W[2], Ssc))
    return cache_w[k]
def mk(des, tmax=None):
    D = json.load(open(os.path.join(HERE, f"design_{des}.json"))); iq = QS.index(D["q"])
    def f(k, C):
        W, F = W_of(k)
        return run(*W, C, Ssc, kind="table", vstar=D["vstar"], G=TAB[fold_of[k]].get(C, iq), feat=F, theta_max=tmax)
    return f, min(D["cands"], key=lambda c: c["J"])["C"]
f, C = mk("tab_v1.9_q0.99"); collect("wb_causal", C, f)
f, C = mk("tab_v1.9_q0.99_cap2", 2.0); collect("wb_cap2", C, f)
Do = json.load(open(os.path.join(HERE, "design_oracle_v2.0.json"))); Co = min(Do["cands"], key=lambda c: c["J"])["C"]
collect("wb_oracle", Co, lambda k, C: oracle(*W_of(k)[0], C, Ssc, vstar=2.0))
# paired weekly C_min: causal vs (15) eps=1 and greedy eps=0
D = json.load(open(os.path.join(HERE, "design_tab_v1.9_q0.99.json"))); cm = np.array(D["cmin_wk"])
pair = {}
for lab, ref_c in [("eps1", CMIN[1.0]), ("eps0", CMIN0), ("eps2", CMIN[2.0])]:
    x = cm - ref_c
    pair[lab] = dict(mean_diff=float(x.mean()), rel_pct=float(x.mean() / ref_c.mean() * 100),
                     p_wilcoxon=float(stats.wilcoxon(x).pvalue) if np.any(x != 0) else None, share_lower=float(np.mean(x < -1e-9)))
cd = {k: float(np.quantile(v, 0.95, method="inverted_cdf")) for k, v in [("eps0", CMIN0), ("eps1", CMIN[1.0]), ("eps2", CMIN[2.0]), ("wb_causal", cm)]}
for nm in ["tab_v1.9_q0.99_cap2", "oracle_v2.0", "uniform_v1.5", "tab_v1.8_q0.98", "tab_v2.0_q0.99"]:
    cd[nm] = float(json.load(open(os.path.join(HERE, f"design_{nm}.json")))["cdes"])
json.dump(dict(rows=rows, cmin_pair=pair, cdes=cd), open(os.path.join(HERE, "metrics.json"), "w"), indent=1)
print(pair, cd)
