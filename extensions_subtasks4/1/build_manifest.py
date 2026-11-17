"""Merge data/hashes.jsonl (all 190 stored week files) with the regeneration checks (data/manifest_*.jsonl)
-> MANIFEST.csv, MANIFEST.json, SHA256SUMS.txt (sha256sum -c compatible, absolute paths), dataset digests."""
import sys, json, csv, hashlib
sys.path.insert(0, "/home/claude/subtasks4/1")
from common import *

H = [json.loads(l) for l in open(f"{OUT}/data/hashes.jsonl")]
regen = {}
for n in ("base", "cert", "sub"):
    for l in open(f"{OUT}/data/manifest_{n}.jsonl"):
        r = json.loads(l)
        regen[(r["set"], r["k"])] = r

rows = []
for h in H:
    r = regen.get((h["set"], h["k"]))
    row = dict(h)
    if r is None:
        row.update(regenerated="no (hash only)", bitexact_P="", bitexact_Q="", maxabsdiff_f64_vs_f32_P="", maxabsdiff_f64_vs_f32_Q="",
                   sha256_matches_regeneration="")
    else:
        assert r["file_sha256"] == h["sha256_file"] and r["content_sha256_f32_PQ"] == h["sha256_content_f32_PQ"]
        row.update(regenerated="yes", bitexact_P=r["bitexact_P"], bitexact_Q=r["bitexact_Q"],
                   maxabsdiff_f64_vs_f32_P=r["maxabsdiff_P"], maxabsdiff_f64_vs_f32_Q=r["maxabsdiff_Q"], sha256_matches_regeneration="file hash re-read = stored")
    rows.append(row)

cols = ["set", "k", "role", "case", "generator", "seed_base", "rng_seed", "file", "bytes", "sha256_file", "sha256_content_f32_PQ",
        "n_samples", "dtype", "regenerated", "bitexact_P", "bitexact_Q", "maxabsdiff_f64_vs_f32_P", "maxabsdiff_f64_vs_f32_Q"]
with open(f"{OUT}/MANIFEST.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
with open(f"{OUT}/SHA256SUMS.txt", "w") as f:
    for r in rows:
        f.write(f"{r['sha256_file']}  {r['file']}\n")

summary = {}
for n in ("base", "cert", "sub"):
    rs = [r for r in rows if r["set"] == n]
    rg = [r for r in rs if r["regenerated"] == "yes"]
    digest = hashlib.sha256("".join(r["sha256_content_f32_PQ"] for r in sorted(rs, key=lambda r: r["k"])).encode()).hexdigest()
    summary[n] = dict(n_files=len(rs), role=rs[0]["role"], generator=rs[0]["generator"], seed_base=rs[0]["seed_base"],
                      seed_range=[rs[0]["rng_seed"], rs[-1]["rng_seed"]], regenerated_weeks=sorted(r["k"] for r in rg),
                      n_regenerated=len(rg), all_regenerated_bitexact=bool(all(r["bitexact_P"] and r["bitexact_Q"] for r in rg)),
                      dataset_digest_sha256_of_content_hashes=digest,
                      total_bytes=int(sum(r["bytes"] for r in rs)), samples_per_week=sorted({r["n_samples"] for r in rs}))
json.dump(dict(summary=summary, files=rows), open(f"{OUT}/MANIFEST.json", "w"), indent=1, default=str)
print(json.dumps(summary, indent=1))
