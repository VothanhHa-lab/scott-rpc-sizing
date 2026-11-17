"""LaTeX table of the hardware cost items (functions of C, annualised with CRF), with unit costs and sources."""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import costmodel as cm

C = cm.C_REF
crf = cm.CRF
rows = []
def ann(x): return crf * x
tr = [cm.hardware("none", lv, C)["transformers"] for lv in ("low", "central", "high")]
fc = [cm.hardware("filter", lv, C)["filter_C"] for lv in ("low", "central", "high")]
fl = [cm.hardware("filter", lv, C)["filter_L"] for lv in ("low", "central", "high")]
dc = [cm.hardware("dc", lv, C)["dc_link_extra"] for lv in ("low", "central", "high")]
base = 300 * C
def f1(x): return f"{x:.0f}"
def rng(v): return f"{v[1]:.0f} ({v[0]:.0f}--{v[2]:.0f})"
tex = r"""\begin{table}[htbp]
\caption{\label{tHW}Hardware items added to the installed cost of the RPC legs (unit price 150~kUSD per MVA of leg rating, two legs, i.e.\ $300\,C$~kUSD) and their annualisation with the capital recovery factor $\mathrm{CRF}=0.10185$ (8\%, 20~yr). The unit price is taken to cover the two converter legs with semiconductors, cooling, control, protection, installation and the DC link at $H_\mathrm{dc}=8$~ms; the items below are added to it. Values in kUSD at $C=11.27$~MVA (central; low--high from the unit-cost ranges). The filter items scale with $C$ because the ripple current and power are proportional to $C$; losses 109~kW at full transfer ($\propto s_x^2/C$). The DC-link alternative to the filter is $H_\mathrm{dc}=26.2$~ms, the smallest value for which the 100~Hz ripple alone keeps $V_\mathrm{dc}\ge3.28$~kV.}
\centering
\begin{adjustbox}{max width=\linewidth}
\begin{tabular}{@{}p{3.3cm}p{4.4cm}p{3.0cm}rr@{}}
\hline
Item & Size as a function of $C$ & Unit cost (central; range) & Capital at 11.27~MVA & Annualised\\
\hline
RPC legs (reference) & $2C$~MVA & 150~kUSD/MVA & """ + f1(base) + r""" & """ + f1(ann(base)) + r"""\\
Coupling transformers 27.5/2.0~kV (one per leg) & $2C$~MVA & 30 (10--100)~kUSD/MVA & """ + rng(tr) + r""" & """ + f"{ann(tr[1]):.0f}" + r"""\\
Filter capacitor & $C_f=10\,C/11.27$~mF at $V_r=5$~kV: $\tfrac12C_fV_r^2=125\,C/11.27$~kJ & 0.7 (0.15--3)~USD/J & """ + rng(fc) + r""" & """ + f"{ann(fc[1]):.0f}" + r"""\\
Filter reactor 0.253~mH $\cdot$ 11.27/$C$ & $Q_f=I_f^2\omega L_f=3.28\,C/11.27$~Mvar (100~Hz, 4.54~kA rms) & 20 (10--40)~kUSD/Mvar & """ + rng(fl) + r""" & """ + f"{ann(fl[1]):.0f}" + r"""\\
Filter loss & $0.00967\,s_x^2/C$~MW (109~kW at $s_x=C=11.27$~MVA) & 80~USD/MWh & \multicolumn{2}{r}{counted in $J_\mathrm{loss}$}\\
Extra DC-link energy (alternative to filter) & $(H_\mathrm{dc}-8\,\mathrm{ms})\,C\,(V_r/V_0)^2$, $V_r=3.85$~kV, $V_0=3.5$~kV & 0.7 (0.15--3)~USD/J & """ + rng(dc) + r""" & """ + f"{ann(dc[1]):.0f}" + r"""\\
Scott up-rating (not required at 40~MVA per leg; 20~MVA more in total for 50~MVA per leg) & $\Delta S_\mathrm{Scott}$~MVA (independent of $C$) & 30 (10--100)~kUSD/MVA & $30\,\Delta S$ & $3.1\,\Delta S$\\
\hline
\end{tabular}
\end{adjustbox}
\end{table}
"""
open("/home/claude/subtasks4/6/deliver/table_cost_items.tex", "w").write(tex)
print(tex)
