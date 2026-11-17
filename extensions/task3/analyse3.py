"""Analysis of exact-model sizing (step A/A2) and certification (step B). Writes only to this folder."""
import sys, json
sys.path.insert(0, "/home/claude/code"); import os
os.chdir("/home/claude/code")
import numpy as np
from scipy import stats
from exact_sizing import EPS, C_FACT, LIM, J_of
sys.path.insert(0, "/home/claude/code")
from analyse import load, methods
OUT = "/home/claude/subtasks/3/"
R = "/home/claude/code/results_exact/"
A = json.load(open(R + "stepA.json")); A2 = json.load(open(R + "stepA2.json")); B = json.load(open(R + "stepB.json"))
cm = np.array(A["cmin"]); cands = A2["cands"]; ev = A2["evals"]; nW = cm.shape[0]; nf = len(C_FACT)
W = 52.14

def summ(i):
    w = [e[i] for e in ev]; J, cap, loss, viol = J_of(w)
    return dict(eps=cands[i][0], C=cands[i][1], J=J, Jcap=cap, Jloss=loss, Jviol=viol,
                p95=float(np.mean([x["p95"] for x in w])), p95max=float(np.max([x["p95"] for x in w])),
                p99=float(np.mean([x["p99"] for x in w])),
                comply=float(np.mean([x["p95"] <= LIM + 1e-9 for x in w])),
                share=100 * float(np.mean([x["share"] for x in w])),
                vmax=float(np.mean([x["vmax"] for x in w])),
                Eviol=float(np.mean([x["E_viol"] for x in w]) * W),
                Eloss=float(np.mean([x["E_loss"] for x in w]) * W),
                Etr=float(np.mean([x["E_tr"] for x in w]) * W / 1000),
                Jw=[J_of([x])[0] for x in w])
S = [summ(i) for i in range(len(cands))]
ok = [s["comply"] >= 0.95 for s in S]
ib = min((i for i in range(len(S)) if ok[i]), key=lambda i: S[i]["J"])
ic = EPS.index(1.9) * nf
# best-C per eps (line search)
per_eps = []
for j, e in enumerate(EPS):
    idx = [i for i in range(len(S)) if S[i]["eps"] == e and ok[i]]
    if idx:
        i = min(idx, key=lambda i: S[i]["J"])
        per_eps.append(dict(eps=e, Chat=cands[j * nf][1], Cbest=S[i]["C"], J=S[i]["J"], Jcap=S[i]["Jcap"], Jloss=S[i]["Jloss"], Jviol=S[i]["Jviol"]))
# also best conv: eps=1.9 with C optimised
idx19 = [i for i in range(len(S)) if S[i]["eps"] == 1.9 and ok[i]]
ic_opt = min(idx19, key=lambda i: S[i]["J"])
prop, conv, conv_opt = S[ib], S[ic], S[ic_opt]
# approximate-model designs (results/base.json)
ap = methods(load("base"), 750)
apx = {k: {kk: float(vv) for kk, vv in v.items()} for k, v in ap.items()}
# sanity: exact vs approx weekly cmin
b = load("base"); eg = b["eps_grid"]
san = []
for j, e in enumerate(EPS):
    if e in eg:
        a = np.array([wk["cmin"]["750"][eg.index(e)] for wk in b["weeks"]])
        x = cm[:, j]
        san.append(dict(eps=e, apx_mean=float(np.nanmean(a)), ex_mean=float(np.nanmean(x)),
                        apx_q95=float(np.quantile(a, .95, method="inverted_cdf")),
                        ex_q95=float(np.quantile(x, .95, method="inverted_cdf")),
                        rel_mean=float(np.nanmean(x) / np.nanmean(a) - 1),
                        nnan=int(np.isnan(x).sum())))
    else:
        san.append(dict(eps=e, ex_mean=float(np.nanmean(cm[:, j])), ex_q95=float(np.quantile(cm[:, j], .95, method="inverted_cdf"))))
# approx-design evaluated exactly? the approx designs (C=10.44, eps=1.0; C=11.87, eps=2.0) are in cands only if C equals; compute separately in cert_direct.py
d = np.array(prop["Jw"]) - np.array(conv["Jw"])
wil = stats.wilcoxon(prop["Jw"], conv["Jw"])
pair = dict(mean=float(d.mean()), ci=float(stats.t.ppf(.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))),
            share=float(np.mean(d < 0)), p=float(wil.pvalue))
# certification
cb = np.array(B["cmin"]); N = cb.shape[0]
beta = lambda eps, N, k: float(stats.binom.cdf(k, N, eps))
cert = {}
for j, e in enumerate(B["eps"]):
    x = np.sort(cb[:, j])[::-1]
    rows = [dict(k=k, C=float(x[k]), b10=beta(.10, N, k), b05=beta(.05, N, k)) for k in range(0, 7)]
    Cdes = prop["C"] if j == 0 else conv["C"]
    nv = int(np.sum(cb[:, j] > Cdes + 1e-9))
    cert[str(e)] = dict(rows=rows, Cdes=Cdes, nviol=nv, emp=nv / N,
                        cp_up95=float(stats.beta.ppf(.95, nv + 1, N - nv)),
                        cp_up975=float(stats.beta.ppf(.975, nv + 1, N - nv)),
                        b05=beta(.05, N, nv), b10=beta(.10, N, nv),
                        mean=float(cb[:, j].mean()), sd=float(cb[:, j].std(ddof=1)), q95=float(np.quantile(cb[:, j], .95, method="inverted_cdf")),
                        maxC=float(cb[:, j].max()), nan=int(np.isnan(cb[:, j]).sum()))
    # smallest N-sample k for which beta<=0.05 / .10 at eps .05 -> confidence statement; and min N for k=0
    cert[str(e)]["N_k0_eps05_95"] = int(np.ceil(np.log(0.05) / np.log(0.95)))
# train (60 weeks) vs fresh (90 weeks) comparison of cmin at eps*: two-sample KS
j0 = 0
ks = stats.ks_2samp(cm[:, EPS.index(B["eps"][0])] if B["eps"][0] in EPS else cm[:, 0], cb[:, 0])
out = dict(nW=nW, N=N, eps_star=B["eps"][0], prop={k: v for k, v in prop.items() if k != "Jw"},
           conv={k: v for k, v in conv.items() if k != "Jw"}, conv_opt={k: v for k, v in conv_opt.items() if k != "Jw"},
           approx=apx, sanity=san, per_eps=per_eps, pair=pair, cert=cert,
           ks_train_vs_fresh=dict(stat=float(ks.statistic), p=float(ks.pvalue)))
json.dump(out, open(OUT + "analysis3.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k not in ("cert",)}, indent=1, default=float))
for e, c in cert.items():
    print("eps", e, {k: v for k, v in c.items() if k != "rows"})
    for r in c["rows"]: print("   ", r)
