# scott-rpc-sizing

Code and data for the manuscript *Probabilistic sizing of the railway power conditioner in
co-phase traction power supply systems for high-speed trains* (Chu T T, Nguyen T H, Vo T H;
submitted to Railway Engineering Science). Equation and section numbers below refer to that manuscript.

It reproduces section 4 of the paper: the kinematic traction-load model, the multi-week
Monte Carlo sizing procedure (eqs. 7-12), the exact phasor model of the substation,
the averaged dynamic RPC model, the high-speed and suburban case studies and the
corresponding figures and tables.

## Requirements

Python >= 3.10, numpy, scipy, matplotlib; numba for the switching model (`pip install -r requirements.txt`).

## Reproduce

```bash
python pipeline.py           # Monte Carlo ensembles: base (60 weeks), suburban and sensitivity
                             # cases (40 weeks) -> results/, results_sub/, results40/ (~1.5 h, 2 cores)
python dyn_run.py            # averaged RPC model on the worst-case segment -> results/dyn.npz
python validate_network.py 0 20   # exact phasor model vs approximation (4)
python shortterm.py && python shortterm_an.py   # 99th-percentile constraint
python paired.py             # paired weekly comparison of costs
python make_figs.py && python figF.py && python figG.py   # figures -> figs/*.pdf
python collect_numbers.py    # all numbers quoted in the manuscript -> results/numbers.json
```

`pipeline.py` stores the weekly load series of the base and suburban cases in
`results*/…_w*.npz` (about 250 MB, not versioned); they are regenerated from the seeds.

## Random seeds

Week `k` of case `c` uses `numpy.random.default_rng(20261111 + 1000*(c+1) + k)`, with the
case index `c` given by the order of `CASES` in `rpc_sizing/experiment.py`
(base = 0). The grade profile uses `default_rng(20261111)`.

## Files

| File | Content |
|---|---|
| `rpc_sizing/params.py` | all planning assumptions (train, timetable, grid, RPC, costs) |
| `rpc_sizing/train.py` | kinematic train model, eqs. (7)-(8) |
| `rpc_sizing/load.py` | timetable / Poisson / previous segment load models |
| `rpc_sizing/rpc.py` | control law (9), VUF aggregation, losses, bisection for C_min |
| `rpc_sizing/experiment.py` | ensemble procedure, design rule (95 % quantile over weeks) |
| `rpc_sizing/dynamics.py` | averaged dynamic RPC model (DC link, current limit) |
| `rpc_sizing/network.py` | exact phasor model of the Scott substation (check of eq. 4) |
| `analyse.py` | cost function (10) and comparison of methods |

All values are planning assumptions, not data of a specific line or rolling stock.
The models have not been validated against Simulink/PSCAD or measurements; the Simulink script in
`simulink_model/` has not yet been run in MATLAB.

## Licence

MIT (to be confirmed by the authors).

## Extensions added in the revised manuscript
- `exact_sizing.py`, `exact_analyse.py`: sizing with the exact phasor network model inside the loop (section 4.6) and certification on 90 independent weeks; results in `results_exact/`.
- `extensions/task1`: confidence intervals of the design values (Table tCI).
- `extensions/task2`: Pareto front and price sensitivity (Fig. fP).
- `extensions/task3`: analysis of the exact-model sizing and certification (Tables tEx, tCert).
- `extensions/task5`: chance-constrained (SAA) baselines (Table tS, Online Resource 2).
- `extensions/task6`: Python reference values and MATLAB/Simulink scripts for an independent model check.
- `extensions/task7`: window-budget compensation controller (Table tWB, Online Resource 2).
Scripts in `extensions/` read the stored weeks in `results/` (regenerate them with `pipeline.py`; the weekly .npz files are not included because of their size).

## Round-4 additions (final designs, revised manuscript)
- extensions_subtasks4/1: reproduction of all reported tables, dataset manifest (SHA-256) and code checks.
- extensions_subtasks4/2: per-second Scott and RPC leg loading, thermal check (IEC 60076-7 difference equations).
- extensions_subtasks4/3: Python instantaneous-value (averaged-switch) converter model of the DC link.
- extensions_subtasks4/4: load-scenario plausibility, correlated delays, limited regeneration, catenary impedance.
- extensions_subtasks4/5: exact phasor sizing with a consistent current limit for both lines (C solver phasor_c.c),
  locked designs (designs_*_locked.json) and independent verification weeks (manifest_*.json).
- extensions_subtasks4/6: hardware cost items and comparison at equal exceedance.
Paths inside the scripts point to the authors' working directories and must be adapted.

## Converter-level checks of the final design (section 4.4, Online Resource 2 sections S.29-S.30)
- `switching_model/`: Python (numba) instantaneous-value model of the RPC with switched converters
  (two interleaved full bridges per leg, unipolar PWM at 1 kHz, control sampled at 2 kHz with one sample of delay,
  third-harmonic resonant gain 0.05). `python run_sw.py val|main|dt|h8` reproduces `res_*.json`;
  `make_tables.py` and `make_fig_sw.py` produce Table 7 and Fig. S9. See `README_VI.md` (Vietnamese).
- `simulink_model/`: MATLAB scripts that build the same switching model in Simscape Electrical
  (`build_rpc_switching_model.m`) and compare it with `python_reference.csv` (`run_rpc_checks.m`).
  Only the controller (`rpc_ctrl_fcn.m`) has been tested, in GNU Octave against the Python plant
  equations (`test_ctrl_reference_plant.m`); no Simulink result is reported in the manuscript.
