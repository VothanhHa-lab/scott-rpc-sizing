import sys; sys.path.insert(0,'/home/claude/subtasks4/6/scripts')
from lib6 import *
S = exact_set()
hw = Hw("none", trafo=False)
conv = [c for c in S if c.eps == 1.9 and c.src == "stepA2"]
c0 = conv[0]; copt = min(conv, key=hw.J)
prop = min([c for c in S if ok(c)], key=hw.J)
for n, c in (("conv", c0), ("conv_opt", copt), ("prop", prop)):
    p = hw.parts(c); print(n, {k: round(v, 2) for k, v in p.items()})
