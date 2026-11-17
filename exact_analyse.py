"""Summaries of exact-model sizing (step A) and certification (step B)."""
import json
import numpy as np
from scipy import stats
from exact_sizing import EPS, C_FACT, LIM, J_of

A = json.load(open("results_exact/stepA.json"))
A2 = json.load(open("results_exact/stepA2.json"))
B = json.load(open("results_exact/stepB.json"))
cm = np.array(A["cmin"]); cands = A2["cands"]; ev = A2["evals"]
nW = cm.shape[0]


def summ(i):
    w = [e[i] for e in ev]
    J, cap, loss, viol = J_of(w)
    return dict(eps=cands[i][0], C=cands[i][1], J=J, Jcap=cap, Jloss=loss, Jviol=viol,
                p95=np.mean([x["p95"] for x in w]), p99=np.mean([x["p99"] for x in w]),
                comply=np.mean([x["p95"] <= LIM + 1e-9 for x in w]),
                share=100 * np.mean([x["share"] for x in w]),
                vmax=np.mean([x["vmax"] for x in w]),
                Eviol=np.mean([x["E_viol"] for x in w]) * 52.14,
                Etr=np.mean([x["E_tr"] for x in w]) * 52.14 / 1000,
                Jw=[J_of([x])[0] for x in w])


S = [summ(i) for i in range(len(cands))]
ok = [s["comply"] >= 0.95 for s in S]
ib = min((i for i in range(len(S)) if ok[i]), key=lambda i: S[i]["J"])
nf = len(C_FACT)
ic = EPS.index(1.9) * nf
# best C for each eps (for a table of the line search)
per_eps = []
for j, e in enumerate(EPS):
    idx = [i for i in range(len(S)) if S[i]["eps"] == e and ok[i]]
    if idx:
        i = min(idx, key=lambda i: S[i]["J"])
        per_eps.append(dict(eps=e, Chat=cands[j * nf][1], Cbest=S[i]["C"], J=S[i]["J"]))
prop, conv = S[ib], S[ic]
d = np.array(prop["Jw"]) - np.array(conv["Jw"])
wil = stats.wilcoxon(prop["Jw"], conv["Jw"])

# ---- certification ----
cb = np.array(B["cmin"]); N = cb.shape[0]


def beta(eps, N, k):
    return float(stats.binom.cdf(k, N, eps))


cert = {}
for j, e in enumerate(B["eps"]):
    x = np.sort(cb[:, j])[::-1]          # descending
    rows = []
    for k in range(0, 6):
        rows.append(dict(k=k, C=float(x[k]), b10=beta(0.10, N, k), b05=beta(0.05, N, k)))
    Cdes = prop["C"] if j == 0 else conv["C"]
    nviol = int(np.sum(cb[:, j] > Cdes + 1e-9))
    cert[str(e)] = dict(rows=rows, Cdes=Cdes, nviol=nviol, b05=beta(0.05, N, nviol),
                        b10=beta(0.10, N, nviol),
                        emp=nviol / N, cp_up=float(stats.beta.ppf(0.95, nviol + 1, N - nviol)))

out = dict(nW=nW, N=N, prop={k: v for k, v in prop.items() if k != "Jw"},
           conv={k: v for k, v in conv.items() if k != "Jw"}, per_eps=per_eps,
           pair=dict(mean=float(d.mean()), ci=float(1.96 * d.std(ddof=1) / np.sqrt(len(d))),
                     share=float(np.mean(d < 0)), p=float(wil.pvalue)),
           cmin_mean={str(e): float(np.nanmean(cm[:, j])) for j, e in enumerate(EPS)},
           cert=cert)
json.dump(out, open("results_exact/summary.json", "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
