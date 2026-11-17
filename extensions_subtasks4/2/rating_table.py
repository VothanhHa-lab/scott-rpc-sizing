"""Loading statistics of the alpha leg for alternative Scott ratings, obtained by scaling the stored
current of the 40 MVA run (K = I_pu40 * 40/S_N; the small change of the leg voltage with the impedance is neglected)."""
import json, numpy as np
D = "/home/claude/subtasks4/2/data"; R = "/home/claude/subtasks4/2/results"
RAT = [20.0, 25.0, 31.5, 40.0, 50.0, 63.0]
THR = [1.0, 1.3, 1.5, 1.8, 2.0]
acc = {s: dict(h={t: 0 for t in THR}, mx=0, r10=0, r60=0, ep={t: 0 for t in THR}) for s in RAT}
def roll(x, w):
    c = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2))); return np.sqrt((c[w:] - c[:-w]) / w)
def runs(b):
    if not b.any(): return 0
    return int((np.diff(np.concatenate(([0], b.view(np.int8), [0]))) == 1).sum())
for k in range(60):
    I = np.load(f"{D}/legs_w{k:03d}.npz")["I_alpha_pu40"].astype(float)
    r10 = roll(I, 600).max(); r60 = roll(I, 3600).max()
    for s in RAT:
        K = I * 40.0 / s; a = acc[s]
        a["mx"] = max(a["mx"], float(K.max())); a["r10"] = max(a["r10"], r10 * 40 / s); a["r60"] = max(a["r60"], r60 * 40 / s)
        for t in THR:
            a["h"][t] += int((K > t).sum()); a["ep"][t] += runs(K > t)
out = {str(s): dict(max=a["mx"], rms10=a["r10"], rms60=a["r60"], hours={str(t): a["h"][t] / 3600 for t in THR},
                    seconds={str(t): a["h"][t] for t in THR}, episodes={str(t): a["ep"][t] for t in THR}) for s, a in acc.items()}
json.dump(out, open(f"{R}/rating_scaling.json", "w"), indent=1)
for s in out: print(s, round(out[s]["max"], 3), round(out[s]["rms10"], 3), round(out[s]["rms60"], 3), {t: round(h, 2) for t, h in out[s]["hours"].items()})
