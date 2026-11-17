"""Step 1a: regenerate every stored week from its seed with rpc_sizing.experiment.week_case
and compare bit-for-bit (float32 cast, as stored) with the stored npz; write the manifest.
Usage: python3 -I verify_weeks.py <set> [k0 k1]   set in {base, cert, sub}
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

