function run_validation(varargin)
% FIXED COPY (round 2): see CHANGES at the end of NOTES.md; changes are marked FIX-n in the code.
%RUN_VALIDATION  Run validation cases A, B, C and write CSV files for compare.py.
%
%   run_validation                 all cases (A, B, C)
%   run_validation('cases','C')    only case C (averaged RPC step)
%   run_validation('cases','AB')   only the network cases
%
%   Output folder  <package>/simulink_out/  :
%     caseA_results.csv    Scott substation with linear loads (eqs. (7)-(8))
%     caseB_results.csv    ideal RPC transfer, rating per eq. (11)
%     caseC_summary.csv    averaged RPC step: metrics
%     caseC_timeseries.csv averaged RPC step: time series 38-44 s
%     run_info.txt         MATLAB / toolbox versions, options
%
%   Method (cases A, B): the model rpc_val_net is simulated in discrete mode (Ts = 50 us,
%   2 s); the last 5 cycles of the PCC voltages/currents and of the feeder voltages/currents are
%   analysed with a DFT at 50 Hz; VUF = |U2|/|U1| (PCC voltage), IUF = |I2|/|I1| (PCC current).
%   Load models  CZ  constant impedance (Series RLC Load, power given at 27.5 kV)
%                CP  constant power (impedance iterated until the power at the feeder terminals
%                    equals the set value)
%                CI  constant current (ideal controlled current source, as the converter model of
%                    Table 6)
%   Case C: the equations of rpc_sizing/dynamics.py in continuous time (rpc_avg_rhs.m) integrated
%   (i) with ode45 in MATLAB and (ii) in Simulink (Integrator + Interpreted MATLAB Function).

p = inputParser;
addParameter(p, 'cases', 'ABC');
addParameter(p, 'T_stop', 2.0);
addParameter(p, 'Ts', 50e-6);
addParameter(p, 'ncyc', 5);
addParameter(p, 'cp_tol', 2e-5);
addParameter(p, 'cp_maxit', 12);
addParameter(p, 'skip_sim_C', false);
addParameter(p, 'outdir', '');
parse(p, varargin{:});
o = p.Results;

here = fileparts(mfilename('fullpath'));
root = fileparts(here);
addpath(here);
outdir = o.outdir;
if isempty(outdir), outdir = fullfile(root, 'simulink_out'); end
if ~exist(outdir, 'dir'), mkdir(outdir); end
fref = fullfile(root, 'python_reference.json');
if ~exist(fref, 'file'), fref = fullfile(here, 'python_reference.json'); end
ref = jsondecode(fileread(fref));
K = ref.constants;

write_info(outdir, o);
t0 = tic;

if any(o.cases == 'A') || any(o.cases == 'B')
    try
        st = init_net(K, o, ref, root);
        if any(o.cases == 'A'), run_set(K, o, ref, st, outdir, 'A'); end
        if any(o.cases == 'B'), run_set(K, o, ref, st, outdir, 'B'); end
    catch ME
        fprintf(2, '\n*** Cases A/B failed: %s\n', ME.message);
        fprintf(2, '%s\n', getReport(ME));
    end
end
if any(o.cases == 'C')
    try
        run_caseC(ref, o, outdir, root);
    catch ME
        fprintf(2, '\n*** Case C failed: %s\n', ME.message);
        fprintf(2, '%s\n', getReport(ME));
    end
end
fprintf('\nrun_validation finished in %.0f s. Send back the folder:\n  %s\n', toc(t0), outdir);
end

%% ===================================================================== network cases A and B
function st = init_net(K, o, ref, root)
% build the model, check the Scott connection, calibrate the current sources
% FIX-5: the original "polarity self-test" (k = 1, equal loads, IUF ~ 0) cannot detect a reversed
% teaser, because every load is defined relative to its own terminal voltage and the circuit with a
% reversed teaser is then electrically identical (checked with an independent OpenDSS model,
% polarity_test.json: IUF/VUF unchanged, only the sign of the beta phase shift changes). It is replaced
% by a no-load phasor check (|Ua| = |Ub| = 27.5 kV*sqrt(2) and Ub leads Ua by +90 deg, as in network.py),
% which does detect series-opposing windings (|Ua| ~ 0) and the wrong phase shift; the old test is kept
% as a warning-only sanity check and still provides the measurement-sign calibration.
moddir = fullfile(root, 'simulink_models');
st = struct('flip', false);
Vpk = K.V_sec_kV*1e3*sqrt(2);
for attempt = 1:2
    build_validation_model('which', 'net', 'flip_teaser', st.flip);
    load_system(fullfile(moddir, 'rpc_val_net.slx'));
    m0 = net_once(K, o, 500, spec_Z(0, K), spec_Z(0, K), ci_zero(), ci_zero());
    dev = [abs(m0.Va), abs(m0.Vb)]/Vpk - 1;
    dang = angle(m0.Vb/m0.Va)*180/pi;
    fprintf('No-load check: |Ua| = %.3f kV, |Ub| = %.3f kV (peak), arg(Ub/Ua) = %+.2f deg  (flip_teaser = %d)\n', ...
        abs(m0.Va)/1e3, abs(m0.Vb)/1e3, dang, st.flip);
    if max(abs(dev)) > 0.01
        error(['Scott no-load voltages differ from 27.5 kV by more than 1 %% (%.2f %%, %.2f %%). ' ...
               'Check that the two half windings of the main transformer are connected series-aiding on both sides.'], ...
               100*dev(1), 100*dev(2));
    end
    if abs(dang - 90) < 1
        break
    end
    if attempt == 2
        error('Beta voltage does not lead alpha by 90 deg for either teaser polarity (arg = %+.1f deg).', dang);
    end
    fprintf('  beta lags alpha -> rebuilding with reversed teaser polarity\n');
    st.flip = true;
end
c = ref.caseA(arrayfun(@(x) strcmp(x.id, 'A_Ssc500_k1.0_dphi0'), ref.caseA));
[Sa, Sb] = loads_A(c);
m = net_once(K, o, c.Ssc_MVA, spec_Z(Sa, K), spec_Z(Sb, K), ci_zero(), ci_zero());
fprintf('Sanity test (k=1, equal loads): IUF = %.3f %%\n', m.IUF);
if m.IUF > 1.0
    warning('run:iuf', 'IUF of the balanced test case is %.2f %% (expected ~0): check the transformer wiring.', m.IUF);
end
st.eps_m = [sign_nz(real(m.Sa_meas)), sign_nz(real(m.Sb_meas))];   % measurement sign (V,I polarity)
% no-load calibration: phasors of the open-circuit feeder voltages (phase reference of the sources)
m0 = net_once(K, o, 500, spec_Z(0, K), spec_Z(0, K), ci_zero(), ci_zero());
st.U0 = [m0.Va, m0.Vb];
% sign of the controlled current sources
st.f = [1 1];
Stest = 5e6;                                    % 5 MVA test
for fd = 1:2
    ca = ci_zero(); cb = ci_zero();
    if fd == 1, ca = ci_spec(Stest, st.U0(1), 1); else, cb = ci_spec(Stest, st.U0(2), 1); end
    mm = net_once(K, o, 500, spec_Z(0, K), spec_Z(0, K), ca, cb);
    S = [st.eps_m(1)*mm.Sa_meas, st.eps_m(2)*mm.Sb_meas];
    if real(S(fd)) < 0, st.f(fd) = -1; end
end
fprintf('Current-source sign factors: alpha %+d, beta %+d\n', st.f(1), st.f(2));
end

function run_set(K, o, ref, st, outdir, which)
if which == 'A'
    cases = ref.caseA; models = cellstr(ref.load_models_A);
    cols = {'case_id','load_model','Ssc_MVA','k','dphi_deg'};
else
    cases = ref.caseB; models = cellstr(ref.load_models_B);
    cols = {'case_id','load_model','Ssc_MVA','rating_MVA'};
end
cols = [cols, {'Sa_set_P_MW','Sa_set_Q_Mvar','Sb_set_P_MW','Sb_set_Q_Mvar', ...
               'Sa_act_P_MW','Sa_act_Q_Mvar','Sb_act_P_MW','Sb_act_Q_Mvar', ...
               'IUF_pct','VUF_pct','V1_pcc_kVll','VUF_seqblock_pct','n_iter','converged'}];
rows = [];
for ic = 1:numel(cases)
    c = cases(ic);
    if which == 'A', [Sa, Sb] = loads_A(c); else, [Sa, Sb] = loads_B(c); end
    for im = 1:numel(models)
        mod = models{im};
        tic;
        switch mod
            case 'CZ'
                m = net_once(K, o, c.Ssc_MVA, spec_Z(Sa, K), spec_Z(Sb, K), ci_zero(), ci_zero());
                nit = 1; conv = 1;
            case 'CP'
                [m, nit, conv] = run_CP(K, o, c.Ssc_MVA, Sa, Sb);
            case 'CI'
                ca = ci_spec(Sa*1e6, st.U0(1), st.f(1));
                cb = ci_spec(Sb*1e6, st.U0(2), st.f(2));
                m = net_once(K, o, c.Ssc_MVA, spec_Z(0, K), spec_Z(0, K), ca, cb);
                nit = 1; conv = 1;
            otherwise
                error('unknown load model %s', mod);
        end
        r = struct();
        r.case_id = c.id; r.load_model = mod; r.Ssc_MVA = c.Ssc_MVA;
        if which == 'A', r.k = c.k; r.dphi_deg = c.dphi_deg; else, r.rating_MVA = c.rating_MVA; end
        r.Sa_set_P_MW = real(Sa); r.Sa_set_Q_Mvar = imag(Sa);
        r.Sb_set_P_MW = real(Sb); r.Sb_set_Q_Mvar = imag(Sb);
        Sa_act = st.eps_m(1)*m.Sa_meas/1e6;  Sb_act = st.eps_m(2)*m.Sb_meas/1e6;
        r.Sa_act_P_MW = real(Sa_act); r.Sa_act_Q_Mvar = imag(Sa_act);
        r.Sb_act_P_MW = real(Sb_act); r.Sb_act_Q_Mvar = imag(Sb_act);
        r.IUF_pct = m.IUF; r.VUF_pct = m.VUF;
        r.V1_pcc_kVll = sqrt(3)*abs(m.V1)/sqrt(2)/1e3;
        r.VUF_seqblock_pct = m.VUF_seq;
        r.n_iter = nit; r.converged = conv;
        rows = [rows, r]; %#ok<AGROW>
        fprintf('%s  %-3s  Ssc %4g  IUF %8.4f %%  VUF %8.4f %%  (%d sim, %.1f s)\n', ...
            c.id, mod, c.Ssc_MVA, r.IUF_pct, r.VUF_pct, nit, toc);
    end
end
write_csv(fullfile(outdir, ['case' which '_results.csv']), cols, rows);
end

function [m, nit, conv] = run_CP(K, o, Ssc, Sa, Sb)
% constant power: iterate Vn of the loads until the terminal voltage equals Vn
Vn = [K.V_sec_kV, K.V_sec_kV]*1e3;
conv = 0;
for nit = 1:o.cp_maxit
    m = net_once(K, o, Ssc, spec_S(Sa, Vn(1)), spec_S(Sb, Vn(2)), ci_zero(), ci_zero());
    Vnew = [m.Vrms_a, m.Vrms_b];
    chg = max(abs(Vnew - Vn)./Vn);
    Vn = Vnew;
    if chg < o.cp_tol, conv = 1; break; end
end
end

function [Sa, Sb] = loads_A(c)
Sa = c.Sa_MVA*exp(1j*deg2rad_(c.phia_deg));
Sb = c.Sb_MVA*exp(1j*deg2rad_(c.phib_deg));
end

function [Sa, Sb] = loads_B(c)
Sa = complex(c.Sa_P_MW, c.Sa_Q_Mvar);
Sb = complex(c.Sb_P_MW, c.Sb_Q_Mvar);
end

function r = deg2rad_(d)
r = d*pi/180;
end

function s = sign_nz(x)
s = 1; if x < 0, s = -1; end
end

function s = spec_S(S_MVA, Vn)
% Series RLC Load parameters for power S (MVA, complex) drawn at the rms voltage Vn
P = real(S)*1e6; Q = imag(S)*1e6;
s.Vn = Vn; s.P = max(P, 1); s.QL = max(Q, 0); s.QC = max(-Q, 0);
end

function s = spec_Z(S_MVA, K)
s = spec_S(S_MVA, K.V_sec_kV*1e3);
end

function c = ci_zero()
c.amp = 0; c.ph = 0;
end

function c = ci_spec(S_VA, U0, f)
% current source for power S_VA (complex, VA) at the open-circuit feeder phasor U0 (peak, V):
% peak phasor I = 2*conj(S)/conj(U0);  i(t) = amp*sin(wt + ph) = amp*cos(wt + ph - pi/2)
if abs(S_VA) < 1
    c = ci_zero(); return
end
I = f*2*conj(S_VA)/conj(U0);
c.amp = abs(I); c.ph = angle(I) + pi/2;
end

function m = net_once(K, o, Ssc, la, lb, ca, cb)
% one simulation of rpc_val_net and DFT analysis of the last o.ncyc cycles
w = 2*pi*K.f_Hz;
Zs = (K.V_prim_kV*1e3)^2/(Ssc*1e6);
Rs = Zs/sqrt(1 + K.XR_source^2);
as = @(n, v) assignin('base', n, v);
as('Vp_V', K.V_prim_kV*1e3); as('fn_Hz', K.f_Hz); as('XR_src', K.XR_source);
as('Ssc_VA', Ssc*1e6); as('Rs_ohm', Rs); as('Ls_H', Rs*K.XR_source/w);
as('Ts_s', o.Ts); as('T_stop_s', o.T_stop);
as('Pa_W', la.P); as('QLa_var', la.QL); as('QCa_var', la.QC); as('Vna_V', la.Vn);
as('Pb_W', lb.P); as('QLb_var', lb.QL); as('QCb_var', lb.QC); as('Vnb_V', lb.Vn);
as('Ci_a_amp', ca.amp); as('Ci_a_ph', ca.ph); as('Ci_b_amp', cb.amp); as('Ci_b_ph', cb.ph);
so = sim('rpc_val_net', 'StopTime', num2str(o.T_stop, '%.6g'), 'ReturnWorkspaceOutputs', 'on');
t = so.get('tout');
N = round(o.ncyc/K.f_Hz/o.Ts);
idx = (numel(t) - N + 1):numel(t);
tt = t(idx); tt = tt(:);
E = exp(-1j*w*tt).';
ph = @(x) (E*x(idx, :))*2/N;                  % peak phasors (cos reference)
Vp = ph(so.get('Vpcc')); Ip = ph(so.get('Ipcc'));
Va = ph(so.get('Va'));   Ia = ph(so.get('Ia'));
Vb = ph(so.get('Vb'));   Ib = ph(so.get('Ib'));
a = exp(2j*pi/3);
V1 = (Vp(1) + a*Vp(2) + a^2*Vp(3))/3;  V2 = (Vp(1) + a^2*Vp(2) + a*Vp(3))/3;
I1 = (Ip(1) + a*Ip(2) + a^2*Ip(3))/3;  I2 = (Ip(1) + a^2*Ip(2) + a*Ip(3))/3;
m.VUF = abs(V2)/abs(V1)*100;
m.IUF = abs(I2)/abs(I1)*100;
m.V1 = V1;
m.Va = Va; m.Vb = Vb;
m.Vrms_a = abs(Va)/sqrt(2); m.Vrms_b = abs(Vb)/sqrt(2);
m.Sa_meas = Va*conj(Ia)/2;                    % VA, sign fixed later with the measurement polarity
m.Sb_meas = Vb*conj(Ib)/2;
m.VUF_seq = NaN;
try                                           % optional Sequence Analyzer blocks (not required)
    vp = so.get('SeqV_pos'); vn = so.get('SeqV_neg');
    r = vn(end, 1)/vp(end, 1)*100;
    if abs(r - m.VUF) < 0.01*max(m.VUF, 0.01) + 1e-4, m.VUF_seq = r; end
catch
end
end

%% ============================================================================ case C
function run_caseC(ref, o, outdir, root)
pc = ref.caseC; p = pc.params;
P = pc.P_MW(:); Q = pc.Q_Mvar(:);
T = numel(P) - 1;
dt = 2e-4;
n = round(T/dt);
tg = (0:n-1)'*dt;
PLg = lininterp(P, tg) + (tg >= pc.t_step_s)*pc.step_MW;
QLg = lininterp(Q, tg);
sumrows = []; tsrows = [];
useSim = ~o.skip_sim_C;
if useSim
    try
        build_validation_model('which', 'avg');
        load_system(fullfile(root, 'simulink_models', 'rpc_val_avg.slx'));
    catch ME
        fprintf(2, 'Simulink model of case C not available (%s); only ode45 will be run.\n', ME.message);
        useSim = false;
    end
end
for v = 1:numel(pc.variants)
    var = pc.variants(v);
    x0 = var.x0(:);
    % ---------------- MATLAB ode45
    tic;
    rpc_avg_rhs('init', p, var.ff);
    ts = pc.t_step_s; stp = pc.step_MW;
    rhs = @(t, x) rpc_avg_rhs([x(:); lininterp(P, t) + (t >= ts)*stp; lininterp(Q, t)]);
    opts = odeset('RelTol', 1e-8, 'AbsTol', 1e-9, 'MaxStep', 2e-3);
    [t1, X1] = ode45(rhs, [0 ts], x0, opts);
    [t2, X2] = ode45(rhs, [ts T], X1(end, :)', opts);
    t = [t1; t2(2:end)]; X = [X1; X2(2:end, :)];
    Xg = interp1(t, X, tg, 'linear', 'extrap');
    [sumrows, tsrows] = collect(sumrows, tsrows, var, 'matlab_ode45', Xg, tg, PLg, QLg, p, pc, toc);
    fprintf('Case C %s  matlab_ode45 done (%.1f s)\n', var.case_id, toc);
    % ---------------- Simulink
    if useSim
        try
            tic;
            assignin('base', 'x0_vec', x0);
            rpc_avg_rhs('init', p, var.ff);
            so = sim('rpc_val_avg', 'ReturnWorkspaceOutputs', 'on');
            ts_ = so.get('tout'); Xs = so.get('Xout');
            [ts_, iu] = unique(ts_); Xs = Xs(iu, :);
            Xg = interp1(ts_, Xs, tg, 'linear', 'extrap');
            [sumrows, tsrows] = collect(sumrows, tsrows, var, 'simulink', Xg, tg, PLg, QLg, p, pc, toc);
            fprintf('Case C %s  simulink done (%.1f s)\n', var.case_id, toc);
        catch ME
            fprintf(2, 'Case C %s Simulink run failed: %s\n', var.case_id, ME.message);
        end
    end
end
write_csv(fullfile(outdir, 'caseC_summary.csv'), ...
    {'case_id','method','ff','Vdc_min_V','Vdc_max_V','Vdc_dev_max_pct','Ia_max_pu','Ib_max_pu','settle_s','runtime_s'}, sumrows);
write_csv(fullfile(outdir, 'caseC_timeseries.csv'), ...
    {'case_id','method','t_s','Vdc_V','Ia_pu','Ib_pu','Pa_MW','Pb_MW'}, tsrows);
end

function [sumrows, tsrows] = collect(sumrows, tsrows, var, method, Xg, tg, PLg, QLg, p, pc, rt)
out = rpc_avg_out(Xg, PLg, QLg, p);
Vdc = out(:, 1); Ia = out(:, 2); Ib = out(:, 3);
Vref = p.Vref;
r = struct();
r.case_id = var.case_id; r.method = method; r.ff = var.ff;
r.Vdc_min_V = min(Vdc); r.Vdc_max_V = max(Vdc);
r.Vdc_dev_max_pct = max(abs(Vdc - Vref))/Vref*100;
r.Ia_max_pu = max(Ia); r.Ib_max_pu = max(Ib);
after = tg >= pc.t_step_s;
outband = abs(Vdc(after) - Vref) > pc.band_pct/100*Vref;
tafter = tg(after);
if any(outband), r.settle_s = tafter(find(outband, 1, 'last')) - pc.t_step_s; else, r.settle_s = 0; end
r.runtime_s = rt;
sumrows = [sumrows, r];
sel = find(tg >= 38 & tg <= 44 & mod((0:numel(tg)-1)', 10) == 0);
for i = sel'
    q = struct('case_id', var.case_id, 'method', method, 't_s', tg(i), 'Vdc_V', Vdc(i), ...
               'Ia_pu', Ia(i), 'Ib_pu', Ib(i), 'Pa_MW', Xg(i, 2), 'Pb_MW', Xg(i, 4));
    tsrows = [tsrows, q]; %#ok<AGROW>
end
end

function y = lininterp(P, t)
% linear interpolation of the 1-s samples P(1..n) at times t (s); end values held
x = min(max(t, 0), numel(P) - 1);
i = min(floor(x) + 1, numel(P) - 1);
f = x - (i - 1);
y = P(i).*(1 - f) + P(i + 1).*f;
end

%% ============================================================================ output helpers
function write_csv(file, cols, rows)
fid = fopen(file, 'w');
if fid < 0, error('cannot write %s', file); end
fprintf(fid, '%s\n', strjoin(cols, ','));
for i = 1:numel(rows)
    c = cell(1, numel(cols));
    for j = 1:numel(cols)
        v = rows(i).(cols{j});
        if ischar(v), c{j} = v; else, c{j} = sprintf('%.10g', v); end
    end
    fprintf(fid, '%s\n', strjoin(c, ','));
end
fclose(fid);
fprintf('wrote %s (%d rows)\n', file, numel(rows));
end

function write_info(outdir, o)
fid = fopen(fullfile(outdir, 'run_info.txt'), 'w');
fprintf(fid, 'date: %s\nmatlab: %s\ncomputer: %s\noptions: cases=%s T_stop=%g Ts=%g ncyc=%d cp_tol=%g\n', ...
    datestr(now, 31), version, computer, o.cases, o.T_stop, o.Ts, o.ncyc, o.cp_tol);
try
    fprintf(fid, '\n%s\n', evalc('ver'));
catch
end
fclose(fid);
end
