"""Step 1a: regenerate every stored week from its seed with rpc_sizing.experiment.week_case
and compare bit-for-bit (float32 cast, as stored) with the stored npz; write the manifest.
Usage: python3 -I verify_weeks.py <set> [k1,k2,...]   set in {base, cert, sub}
Resumable: rows are appended to data/manifest_<set>.jsonl."""
import sys, os, json, hashlib, time
sys.path.insert(0, "/home/claude/code")
import numpy as np
from rpc_sizing.experiment import week_case, seed_of, SEED0
from rpc_sizing.params import SEED0 as S0

CODE = "/home/claude/code"
OUT = "/home/claude/subtasks4/1/data"
SETS = {
    "base": dict(case="base", seed_base=seed_of("base"), n=60,
                 path=CODE + "/results/base_w%03d.npz", role="high-speed design weeks (selection of C*, eps*)"),
    "cert": dict(case="base", seed_base=SEED0 + 900000, n=90,
                 path=CODE + "/results_exact/cert_w%03d.npz", role="high-speed independent certification weeks"),
    "sub": dict(case="suburban", seed_base=seed_of("suburban"), n=40,
                path=CODE + "/results_sub/suburban_w%03d.npz", role="suburban design weeks"),
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    name = sys.argv[1]
    s = SETS[name]
    ks = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(range(s["n"]))
    fn = f"{OUT}/manifest_{name}.jsonl"
    done = set()
    if os.path.exists(fn):
        done = {json.loads(l)["k"] for l in open(fn)}
    for k in ks:
        if k in done:
            continue
        t = time.time()
        P, Q = week_case(s["case"], k, s["seed_base"])
        path = s["path"] % k
        d = np.load(path)
        Ps, Qs = d["P"], d["Q"]
        P32, Q32 = P.astype(np.float32), Q.astype(np.float32)
        eqP = bool(np.array_equal(P32, Ps)); eqQ = bool(np.array_equal(Q32, Qs))
        # content hash of the float32 arrays (independent of zip/compression container)
        ch = hashlib.sha256(Ps.tobytes() + Qs.tobytes()).hexdigest()
        row = dict(set=name, k=k, case=s["case"], generator="rpc_sizing.experiment.week_case(%r, k, %d)" % (s["case"], s["seed_base"]),
                   rng_seed=int(s["seed_base"] + k), file=path,
                   file_sha256=sha256(path), content_sha256_f32_PQ=ch, bytes=os.path.getsize(path),
                   n_samples=int(len(Ps)), dtype=str(Ps.dtype),
                   bitexact_P=eqP, bitexact_Q=eqQ,
                   maxabsdiff_P=float(np.max(np.abs(P - Ps.astype(float)))), maxabsdiff_Q=float(np.max(np.abs(Q - Qs.astype(float)))),
                   exact_f64_vs_f32_P=bool(np.array_equal(P, Ps.astype(float))),
                   sec=round(time.time() - t, 1))
        with open(fn, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(name, k, eqP, eqQ, flush=True)

main()
