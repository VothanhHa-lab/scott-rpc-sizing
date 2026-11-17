"""Weekly exact-model minimum rating C_min^(k)(eps) for the design weeks of one line.
usage: python t2a_stepA.py {hs|sub} [nproc]
hs : results_exact/stepA.json (60 weeks) is reused (no recomputation).
sub: 40 suburban weeks, eps grid EPS, same bisection as exact_sizing.cmin_exact (tol 0.02 MVA).
Per-week results are cached in cache/stepA_<line>_wNNN.json (restartable)."""
import sys
from common5 import *

line = sys.argv[1]
nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
NW = {"hs": 60, "sub": 40}[line]


def one(k):
    f = f"{HERE}/cache/stepA_{line}_w{k:03d}.json"
    if os.path.exists(f):
        return json.load(open(f))["cmin"]
    P, Q = load_week(line, k)
    t = time.time()
    cm = [cmin_exact(P, Q, e) for e in EPS]
    save_json(dict(k=k, eps=EPS, cmin=cm, sec=time.time() - t), f)
    print(f"{line} week {k} done {time.time()-t:.0f}s", flush=True)
    return cm


if __name__ == "__main__":
    if line == "hs":
        d = json.load(open(f"{CODE}/results_exact/stepA.json"))
        cm = d["cmin"]
        assert d["eps"] == EPS
    else:
        if nproc > 1:
            from multiprocessing import Pool
            with Pool(nproc) as p:
                cm = p.map(one, range(NW))
        else:
            cm = [one(k) for k in range(NW)]
    cm = np.array(cm)
    chat = [design_quantile(c) if not np.isnan(c).any() else float("nan") for c in cm.T]
    save_json(dict(line=line, eps=EPS, cmin=cm.tolist(), chat=chat, order_stat=order_k(NW)),
              f"{HERE}/stepA_{line}.json")
    print(line, "Chat(eps):", dict(zip(EPS, np.round(chat, 3))))
