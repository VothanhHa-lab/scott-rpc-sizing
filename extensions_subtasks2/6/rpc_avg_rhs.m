function y = rpc_avg_rhs(u, p, ff)
%RPC_AVG_RHS  Right-hand side of the averaged RPC model (case C).
%   Literal translation of rpc_sizing/dynamics.py into continuous time.
%
%   State  x = [W_MJ; Pa; Qa; Pb; Qb; integ; pm; qm]  (MJ and MW / Mvar)
%     W_MJ   DC-link energy
%     Pa,Qa  alpha-leg power injected into feeder alpha
%     Pb,Qb  beta-leg power drawn from feeder beta
%     integ  integrator of the DC-energy PI controller
%     pm,qm  filtered load power (measurement filter, 1/(2*pi*50) s)
%   Input  u = [x(1:8); PL; QL]  (10 x 1)   PL, QL in MW, Mvar
%
%   rpc_avg_rhs('init', p, ff)   stores the parameter struct p (from
%   python_reference.json, caseC.params) and the feed-forward flag ff
%   (1 = with loss/transfer feed-forward, 0 = PI only) in a persistent
%   variable; this is needed by the Simulink "Interpreted MATLAB Function"
%   block, which passes only u.
%   rpc_avg_rhs(u, p, ff)        stateless call.
persistent P FF
if ischar(u)
    P = p; FF = ff; y = [];
    return
end
if nargin >= 3
    pp = p; fl = ff;
else
    pp = P; fl = FF;
end
u = u(:);
W = u(1); Pa = u(2); Qa = u(3); Pb = u(4); Qb = u(5);
integ = u(6); pm = u(7); qm = u(8);
PL = u(9); QL = u(10);

C = pp.C;
S = hypot(pm, qm);
req = max(0, S - pp.eps_pct/100*pp.Ssc_MVA)/2;
U = 1 - (pp.r_pu_per_MVA*(PL - Pa) + pp.x_pu_per_MVA*(QL - Qa));
lim = C*min(U, 1);
sx = min(req, pp.KAPPA*lim);
if S > 1e-9
    Pref = sx*pm/S;  Qref = sx*qm/S;
else
    Pref = 0;        Qref = 0;
end
ploss = 2*(pp.k0*C + pp.k1*hypot(Pa, Qa) + pp.k2*(Pa^2 + Qa^2)/max(C, 1e-6));
e = pp.Wref_MJ - W;                         % MJ
dinteg = pp.Ki*e;
if (integ >= lim && dinteg > 0) || (integ <= -lim && dinteg < 0)
    dinteg = 0;                             % anti-windup
end
if fl ~= 0
    Pb_ref = Pref + ploss + pp.Kp*e + integ;
else
    Pb_ref = pp.Kp*e + integ;
end
Pb_ref = min(max(Pb_ref, -lim), lim);       % active power has priority
qmax = sqrt(max(lim^2 - Pb_ref^2, 0));
Qb_ref = min(max(Qref, -qmax), qmax);
tau = pp.tau_i_s;

y = [Pb - Pa - ploss; ...
     (Pref - Pa)/tau; (Qref - Qa)/tau; ...
     (Pb_ref - Pb)/tau; (Qb_ref - Qb)/tau; ...
     dinteg; ...
     (PL - pm)/pp.tau_m_s; (QL - qm)/pp.tau_m_s];
end
