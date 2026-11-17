"""Task 1: is P95[VUF10](C) monotone in C for the exact phasor model?  (validity of bisection)
5 weeks per line (ranks of the weekly C_min at eps = 1 %: max, design order statistic, median, 25 %, min),
eps in {0, 1, 1.9} %, 25 grid points C = 0 .. 1.2*Chat(eps) (Chat = exact design value X_(ceil .95N) from step A).
Scenarios: no background; background b = 1 % constant phasor per week (added to the complex exact
negative-sequence ratio U2/U1 of the substation), worst phase over 72 angles (5 deg step) -- P95 is taken
for each angle and the maximum over the angles is used (worst fixed phase of the week).
usage: python t1_monotone.py {hs|sub}"""
import sys
from common5 import *

line = sys.argv[1]
NG = 25
B = 1.0
PSIS = np.arange(72) * 2 * np.pi / 72
EPS_T = [0.0, 1.0, 1.9]
stepA = json.load(open(f"{HERE}/stepA_{line}.json"))
cm = np.array(stepA["cmin"])
N = cm.shape[0]
m = order_k(N)
j1 = EPS.index(1.0)
order = np.argsort(cm[:, j1])
pos = [N - 1, m - 1, N // 2, N // 4, 0]
weeks = [int(order[p]) for p in pos]
print(line, "weeks", weeks, "cmin(eps=1):", [round(cm[k, j1], 3) for k in weeks], flush=True)


def eval_pt(P, Q, C, eps):
    u2, vm, _ = u2_exact(P, Q, C, eps)
    v10 = rpc.vuf10(vm)
    mom = window_moments(u2)
    pb = [rpc.p95(v10_bg(mom, B, psi)) for psi in PSIS]
    return rpc.p95(v10), float(np.max(pb)), float(PSIS[int(np.argmax(pb))]), float(np.min(pb))


out = dict(line=line, weeks=weeks, eps=EPS_T, ng=NG, b=B, psis_deg=np.degrees(PSIS).tolist(), cases=[])
f = f"{HERE}/results_t1_{line}.json"
if os.path.exists(f):
    out = json.load(open(f))
done = {(c["week"], c["eps"]) for c in out["cases"]}
t0 = time.time()
for k in weeks:
    P, Q = load_week(line, k)
    for eps in EPS_T:
        if (k, eps) in done:
            continue
        chat = stepA["chat"][EPS.index(eps)]
        Cg = np.linspace(0.0, 1.2 * chat, NG)
        r = [eval_pt(P, Q, float(C), eps) for C in Cg]
        out["cases"].append(dict(week=k, eps=eps, chat=chat, C=Cg.tolist(), p95=[x[0] for x in r],
                                 p95_bg_worst=[x[1] for x in r], psi_worst=[x[2] for x in r],
                                 p95_bg_best=[x[3] for x in r], cmin_bisect=float(cm[k, EPS.index(eps)])))
        save_json(out, f)
        print(f"week {k} eps {eps} done {time.time()-t0:.0f}s", flush=True)
