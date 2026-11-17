import os, time, subprocess
from rpc_sizing.experiment import run_case, CASES
t = time.time()
def log(m): print(m, round(time.time()-t), flush=True)
if not os.path.exists('results/base.json'):
    run_case('base', 60, [500, 750, 1000, 1500, 2000], 'results', procs=2, store=True); log('base')
if not os.path.exists('results_sub/suburban.json'):
    run_case('suburban', 40, [200, 300, 400], 'results_sub', procs=2, store=True); log('suburban')
for c in CASES:
    if c in ('base', 'suburban') or os.path.exists(f'results40/{c}.json'):
        continue
    run_case(c, 40, [750], 'results40', procs=2, store=False); log(c)
log('all done')
