function p = rpc_params(caseName, varargin)
%RPC_PARAMS  Parameters of the switching RPC model (same values as the Python model sw_rpc.py).
%   p = rpc_params('S1_sustained')                       final design, 2 bridges/leg, fc = 1 kHz
%   p = rpc_params('S6_step+20_pf90', 'Nb', 1)           one bridge per leg
%   options: 'Nb' (1|2), 'fc' (Hz), 'dt' (s), 'C_MVA', 'H_ms', 'mode' (test modes, see rpc_ctrl_fcn.m)
%   The test cases are read from scenarios.json (same file as the Python package).

opt = struct('Nb', 2, 'fc', 1000, 'dt', 1e-6, 'C_MVA', 11.5, 'H_ms', 26.2, 'mode', 0, ...
             'f_bw', 150, 'tau_r', 0.010, 'kh3', 0.05, 'kh5', 0.0, 'v_pred', 1.0, 'T_pre', 0.6, 'T_ramp', 0.4);
for k = 1:2:numel(varargin), opt.(varargin{k}) = varargin{k + 1}; end

here = fileparts(mfilename('fullpath'));
J = jsondecode(fileread(fullfile(here, 'scenarios.json')));
fn = matlab.lang.makeValidName(caseName);
S = J.scenarios.(fn);

% ---- constants (as in sw_rpc.py)
p.F0 = 50; p.W0 = 2*pi*50; p.VBUS_N = 27.5e3; p.N_TR = 27.5/2.0; p.VS0 = 2000;
p.K0 = 0.003; p.K1 = 0.006; p.K2 = 0.006; p.KAPPA = 0.96; p.VREF = 3500;
ZB = p.VBUS_N^2/1e6;

% ---- design
p.C = opt.C_MVA*1e6; p.Ssc = 750; p.eps_u = 1.0;
p.Cdc = 2*opt.H_ms*1e-3*p.C/p.VREF^2;
p.g = getf(S, 'g', 1.0);
Ssc_thev = getf(S, 'Ssc_thev', p.Ssc); leg_MVA = getf(S, 'leg_MVA', 40);
% Thevenin impedance seen from a 27.5 kV busbar (grid on 1 MVA base + Scott leg uk = 10.5 %, X/R 10 / 30)
zg = 1/(Ssc_thev/2); rg = zg/sqrt(1 + 10^2); xg = zg*10/sqrt(1 + 10^2);
zt = 0.105/leg_MVA; rt = zt/sqrt(1 + 30^2); xt = zt*30/sqrt(1 + 30^2);
p.Rth = (rg + rt)*ZB; p.Lth = (xg + xt)*ZB/p.W0;
% coupling transformer per bridge: rating C/Nb, uk 10 %, X/R 30 (referred to the 2 kV side)
p.uk_t = 0.10; p.xr_t = 30;
p.Xt = p.uk_t*p.VS0^2/p.C;  p.Lt = p.Xt/p.W0;  p.Rt = p.Xt/p.xr_t;   % leg equivalent
p.Nb = opt.Nb; p.fc = opt.fc; p.dt = opt.dt;
p.Ts = 1/(2*p.fc); p.Ts_n = round(p.Ts/p.dt);
assert(abs(p.Ts_n*p.dt - p.Ts) < 1e-9*p.Ts, 'dt must divide the sampling period');
p.Em = sqrt(2)*p.VBUS_N*p.g;
p.Imax = sqrt(2)*p.C/p.VS0;
p.rt_pu = p.Rt*p.C/p.VS0^2;
p.ff = 1; p.kff = 1; p.mlim = 0.95; p.ploss_scale = 1; p.v_pred = opt.v_pred;

% ---- current control (equivalent leg inductance), PR + 3rd harmonic with delay compensation
Leq = p.Lt + p.Lth/p.N_TR^2;
p.Kp = 2*pi*opt.f_bw*Leq;
p.Kr = 2*p.Kp/opt.tau_r;
phi_d = p.W0*2*p.Ts;
hh = [1 3 5];
p.krh = [1 opt.kh3 opt.kh5]*p.Kr;
p.cwT = cos(hh*p.W0*p.Ts); p.cphi = cos(hh*phi_d); p.cphi1 = cos(hh*phi_d - hh*p.W0*p.Ts);
% ---- DC-energy PI, notch 100 Hz, 50 Hz measurement filter
wn = 2*pi*15; p.Kpw = 2*0.7*wn; p.Kiw = wn^2; p.Kb = p.Kiw/p.Kpw;
p.Wref = 0.5*p.Cdc*p.VREF^2;
p.a50 = p.Ts/(p.Ts + 1/(2*pi*50));
w2 = 2*p.W0; Kbl = w2/tan(w2*p.Ts/2);
a0 = Kbl^2 + Kbl*w2 + w2^2;
p.nb0 = (Kbl^2 + w2^2)/a0; p.nb1 = 2*(w2^2 - Kbl^2)/a0; p.na1 = p.nb1; p.na2 = (Kbl^2 - Kbl*w2 + w2^2)/a0;
% ---- SOGI on period averages, exact ZOH discretisation and calibration to the phasor at t_k
k = sqrt(2);
A = p.W0*[-k -1; 1 0]; B = p.W0*[k; 0];
p.Ad = expm(A*p.Ts); p.Bd = A\((p.Ad - eye(2))*B);
x = [0; 0]; n = round(0.4/p.Ts); est = zeros(1, n);
for m = 1:n
    t1 = m*p.Ts; u = (sin(p.W0*t1) - sin(p.W0*(t1 - p.Ts)))/(p.W0*p.Ts);
    x = p.Ad*x + p.Bd*u; est(m) = (x(1) + 1i*x(2))*exp(-1i*p.W0*t1);
end
z = mean(est(end - round(0.04/p.Ts) + 1:end));
p.cal_g = abs(z); p.cal_ph = -angle(z);
p.nq = round(0.005/p.dt);           % T/4 delay of the plant-side SOGI (load-current model)

% ---- load schedule (alpha busbar), step event
p.Pk = S.P(:)'*1e6; p.Qk = S.Q(:)'*1e6;
p.T_pre = opt.T_pre; p.T_ramp = opt.T_ramp; p.T_end = opt.T_pre + S.T;
if isfield(S, 'step') && ~isempty(S.step)
    p.t_ev = S.t_ev + p.T_pre; p.dPs = S.step*1e6;
    if isfield(S, 'stepQ') && ~isempty(S.stepQ), p.dQs = S.stepQ*1e6; else, p.dQs = S.step*J.TANPHI*1e6; end
else
    p.t_ev = 1e9; p.dPs = 0; p.dQs = 0;
end
p.Tr = 2e-3;
p.mode = opt.mode;
% sign corrections found by the self-tests of run_rpc_checks.m (+1 = as built)
p.sgn_tr = 1;        % -1: swap the gate signals of the two arms and invert the measured bridge current
p.sgn_ib = 1;        % -1: invert the measured bridge currents (gain block in the model)
p.sgn_vdc = 1;       % -1: invert the measured DC voltage (gain block in the model)
p.ph_a = 90;         % phase (deg) of the alpha source, sine convention: Em*sin(wt+90) = Em*cos(wt)
p.ph_b = 180;        % phase (deg) of the beta source: Em*sin(wt+180) = -Em*sin(wt) = Em*cos(wt+90)
p.sgn_load = 1;      % -1: invert the load-current command
p.sgn_sink = 1;      % -1: invert the DC loss-sink command
p.Iload_test = 2000; % A peak, used in test mode 3
p.caseName = caseName;
end

function v = getf(S, f, d)
if isfield(S, f) && ~isempty(S.(f)), v = S.(f); else, v = d; end
end
