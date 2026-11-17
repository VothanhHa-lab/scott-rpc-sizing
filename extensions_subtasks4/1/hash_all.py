"""SHA-256 of every stored week file (no regeneration) -> data/hashes.jsonl"""
import sys, json, hashlib, os
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *
from verify_weeks_lib import SETS, sha256
rows = []
for name, s in SETS.items():
    for k in range(s["n"]):
        path = s["path"] % k
        d = np.load(path)
        Ps, Qs = d["P"], d["Q"]
        rows.append(dict(set=name, k=k, case=s["case"], role=s["role"],
                         generator="rpc_sizing.experiment.week_case(%r, k, seed_base=%d)" % (s["case"], s["seed_base"]),
                         seed_base=int(s["seed_base"]), rng_seed=int(s["seed_base"] + k), file=path,
                         bytes=os.path.getsize(path), sha256_file=sha256(path),
                         sha256_content_f32_PQ=hashlib.sha256(Ps.tobytes() + Qs.tobytes()).hexdigest(),
                         n_samples=int(len(Ps)), dtype=str(Ps.dtype)))
        print(name, k, flush=True)
with open(f"{OUT}/data/hashes.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
