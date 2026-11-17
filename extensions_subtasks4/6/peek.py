import json, numpy as np
d=json.load(open('/home/claude/code/results_exact/stepA2.json'))
c, ev = d['cands'], d['evals']
W=52.14
for i,(e,C) in enumerate(c):
    w=[x[i] for x in ev]
    comp=np.mean([x['p95']<=2+1e-9 for x in w])
    Ev=np.mean([x['E_viol'] for x in w])*W
    El=np.mean([x['E_loss'] for x in w])
    J=30.555*C+0.08*El*W+2*Ev
    print(f"{i:2d} eps={e:4.2f} C={C:6.2f} comp={comp:.2f} Eviol={Ev:7.1f} cap+loss={30.555*C+0.08*El*W:6.1f} J={J:6.1f}")
