"""Verify that the C re-implementation of the phasor solver reproduces the original numpy code
(rpc_sizing.network.solve via exact_sizing.p95_exact) and the stored exact-model results."""
import sys
from common5 import *
import exact_sizing as ex
rng = np.random.default_rng(1)
mx = 0.0
for line, k in (("hs", 3), ("hs", 41), ("sub", 5), ("sub", 30)):
    P, Q = load_week(line, k)
    for C, e in ((0.0, 0.0), (6.0, 0.0), (8.35, 1.0), (11.27, 1.0), (4.0, 1.9)):
        a = p95_exact(P, Q, C, e); b = ex.p95_exact(P, Q, C, e)
        va = vuf_exact(P, Q, C, e)[0]
        sx = rpc.compensate(P, Q, C, e, SSC)[0] if C > 0 else np.zeros(len(P))
        S = P + 1j * Q; mag = np.abs(S)
        sxv = np.where(mag > 0, sx * S / np.maximum(mag, 1e-9), 0) if C > 0 else np.zeros_like(S)
        vb = np.zeros(len(S)); m = mag > 0
        vb[m], _ = net.solve(S[m] - sxv[m], sxv[m], SSC, n_iter=10, tol=1e-6)
        d = np.abs(va - vb).max()
        mx = max(mx, d)
        print(line, k, C, e, "p95 C-solver %.12f numpy %.12f  max|dVUF| %.2e" % (a, b, d), flush=True)
# stored exact evaluations (stepA2): week 7, a few candidates
A2 = json.load(open(f"{CODE}/results_exact/stepA2.json"))
P, Q = load_week("hs", 7)
for i in (0, 12, 35, 70):
    e, C = A2["cands"][i]
    ev = evaluate_exact(P, Q, C, e); st = A2["evals"][7][i]
    print("stored stepA2 cand", i, "p95", ev["p95"], st["p95"], "E_viol", ev["E_viol"], st["E_viol"], "E_loss", ev["E_loss"], st["E_loss"])
print("max |dVUF| over all checks:", mx)
