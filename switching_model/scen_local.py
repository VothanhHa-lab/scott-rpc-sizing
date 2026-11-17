"""Test scenarios of the averaged-model study (operating points from the stored design weeks), stored in scenarios.json
so that this package runs without the week files.  P, Q: 1-s knots (MW, Mvar) of the alpha-busbar traction load."""
import json, os
import numpy as np
_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios.json')))
TANPHI = _D['TANPHI']
def scenarios():
    S = {}
    for k, v in _D['scenarios'].items():
        v = dict(v); v['P'] = np.asarray(v['P'], float); v['Q'] = np.asarray(v['Q'], float)
        S[k] = v
    return S
