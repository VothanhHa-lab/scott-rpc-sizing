function R = run_rpc_checks(cases, Nb, skipBuild)
%RUN_RPC_CHECKS  Builds the Simulink switching model, checks the polarities, runs the test cases and compares
%   the results with the Python switching model (python_reference.csv).
%   R = run_rpc_checks                                   S1, S4a, S6 with 2 bridges per leg
%   R = run_rpc_checks({'S1_sustained'}, 1)              one case, one bridge per leg
%   R = run_rpc_checks('all', 2)                         all 16 cases
%   Outputs: simulink_vs_python_Nb<Nb>.csv, simulink_check_Nb<Nb>.png, rpc_fix_Nb<Nb>.mat (polarity corrections)
if nargin < 1 || isempty(cases), cases = {'S1_sustained', 'S4a_step+10_seg', 'S6_step+20_pf90'}; end
if nargin < 2, Nb = 2; end
if nargin < 3, skipBuild = false; end
here = fileparts(mfilename('fullpath'));
addpath(here);
ref = readtable(fullfile(here, 'python_reference.csv'), 'TextType', 'string');
if ischar(cases) && strcmp(cases, 'all'), cases = cellstr(unique(ref.case, 'stable'))'; end

% ---------------- 1. build
p = rpc_params(cases{1}, 'Nb', Nb);
setP(p);
mdl = sprintf('rpc_switching_Nb%d', Nb);
if ~skipBuild || ~exist([mdl '.slx'], 'file')
    build_rpc_switching_model(Nb, mdl);
end
load_system(mdl);

% ---------------- 2. polarity self-tests
fix = self_tests(mdl, p);
save(fullfile(here, sprintf('rpc_fix_Nb%d.mat', Nb)), 'fix');

% ---------------- 3. test cases
R = struct([]);
figure('Color', 'w', 'Position', [100 100 1100 300*numel(cases)]);
for c = 1:numel(cases)
    p = applyFix(rpc_params(cases{c}, 'Nb', Nb), fix);
    setP(p);
    fprintf('Running %s (%.1f s simulated) ...\n', cases{c}, p.T_end);
    tic; L = runModel(mdl, p.T_end); cpu = toc;
    r = metrics(L, p);
    r.case = string(cases{c}); r.cpu_s = cpu;
    rr = ref(ref.case == string(cases{c}) & ref.Nb == Nb, :);
    if ~isempty(rr)
        r.py_Vmin = rr.Vmin_V; r.py_Vmax = rr.Vmax_V; r.py_Ia = rr.I1a_pu; r.py_Ib = rr.I1b_pu;
        r.py_pk = rr.Ibr_peak_pu; r.py_rms = rr.Ibr_rms_pu; r.py_tdd = rr.TDD_pct;
    end
    R = [R r]; %#ok<AGROW>
    fprintf('  Simulink: v_dc %.0f-%.0f V, I1 %.3f/%.3f pu, bridge peak %.3f pu, rms %.3f pu, TDD %.2f %%  (%.0f s)\n', ...
            r.Vmin, r.Vmax, r.Ia, r.Ib, r.pk, r.rms, r.tdd, cpu);
    if ~isempty(rr)
        fprintf('  Python  : v_dc %.0f-%.0f V, I1 %.3f/%.3f pu, bridge peak %.3f pu, rms %.3f pu, TDD %.2f %%\n', ...
                rr.Vmin_V, rr.Vmax_V, rr.I1a_pu, rr.I1b_pu, rr.Ibr_peak_pu, rr.Ibr_rms_pu, rr.TDD_pct);
    end
    plotCase(L, p, c, numel(cases), cases{c});
end
T = struct2table(R);
writetable(T, fullfile(here, sprintf('simulink_vs_python_Nb%d.csv', Nb)));
exportgraphics(gcf, fullfile(here, sprintf('simulink_check_Nb%d.png', Nb)), 'Resolution', 200);
disp(T);
end

% =====================================================================================================
function setP(p)
P = rmfield(p, 'caseName');
assignin('base', 'rpcP', P);
end

function p = applyFix(p, fix)
f = fieldnames(fix);
for k = 1:numel(f), p.(f{k}) = fix.(f{k}); end
end

function L = runModel(mdl, Tstop)
so = sim(mdl, 'StopTime', num2str(Tstop, '%.6f'), 'ReturnWorkspaceOutputs', 'on');
X = so.get('rpc_log');
P = evalin('base', 'rpcP'); Nb = P.Nb;
L.t = X(:, 1); L.vdc = X(:, 2); L.vb = X(:, 3:4);
L.ib = X(:, 5:4 + 2*Nb);
L.isrc = X(:, 5 + 2*Nb:6 + 2*Nb);
L.lg = X(:, 7 + 2*Nb:14 + 2*Nb);
end

function z = phasor1(x, t, W0)
% fundamental phasor (peak) over the whole window (integer number of cycles expected)
z = 2*mean(x.*exp(-1i*W0*t));
end

function fix = self_tests(mdl, p)
W0 = p.W0;
fix = struct('sgn_vdc', 1, 'ph_a', p.ph_a, 'ph_b', p.ph_b, 'sgn_load', 1, 'sgn_sink', 1, 'sgn_tr', 1, 'sgn_ib', 1);
fprintf('\n--- Polarity self-tests ---\n');
% Test 0/A: gates off, no load: DC voltage sign and source phases
for it = 1:2
    q = applyFix(p, fix); q.mode = 1; setP(q);
    L = runModel(mdl, 0.06);
    w = L.t >= 0.02 & L.t < 0.06;
    v0 = mean(L.vdc(L.t < 1e-3));
    if it == 1 && v0 < 0, fix.sgn_vdc = -1; fprintf('  DC-voltage measurement inverted -> sgn_vdc = -1\n'); end
    za = phasor1(L.vb(w, 1), L.t(w), W0); zb = phasor1(L.vb(w, 2), L.t(w), W0);
    ea = rad2deg(angle(za)); eb = rad2deg(angle(zb)) - 90;
    fprintf('  test A (no load): |v_a| = %.0f V (expected %.0f), phase a = %.1f deg (0), phase b = %.1f deg (90)\n', ...
            abs(za), p.Em, rad2deg(angle(za)), rad2deg(angle(zb)));
    if abs(wrap180(ea)) < 2 && abs(wrap180(eb)) < 2, break; end
    fix.ph_a = fix.ph_a - ea; fix.ph_b = fix.ph_b - eb;
    fprintf('  -> source phases corrected: ph_a = %.1f, ph_b = %.1f deg\n', fix.ph_a, fix.ph_b);
end
assert(abs(abs(v0) - p.VREF) < 0.05*p.VREF, ['DC link does not start at 3.5 kV (%.0f V): set the initial ' ...
       'capacitor voltage of block Cdc to rpcP.VREF'], v0);
assert(abs(abs(za) - p.Em) < 0.03*p.Em, 'Busbar voltage amplitude wrong (%.0f V): check the AC sources', abs(za));
% Test C: resistive test load on alpha must draw power (busbar voltage lags the source)
q = applyFix(p, fix); q.mode = 3; setP(q);
L = runModel(mdl, 0.06); w = L.t >= 0.02 & L.t < 0.06;
ang = rad2deg(angle(phasor1(L.vb(w, 1), L.t(w), W0)));
fprintf('  test C (2 kA resistive load): phase of v_a = %.2f deg (expected about %.1f)\n', ang, ...
        -rad2deg(p.W0*p.Lth*p.Iload_test/p.Em));
if ang > 0, fix.sgn_load = -1; fprintf('  -> load-current source inverted: sgn_load = -1\n'); end
% Test E: DC sink of 200 A must discharge the capacitor
q = applyFix(p, fix); q.mode = 4; setP(q);
L = runModel(mdl, 0.03); w = L.t >= 0.005;
slope = polyfit(L.t(w), L.vdc(w), 1);   % vdc in the log is already after the sgn_vdc gain
fprintf('  test E (DC sink 200 A): dv/dt = %.0f V/s (expected %.0f)\n', slope(1), -200/p.Cdc);
if slope(1) > 0, fix.sgn_sink = -1; fprintf('  -> DC sink inverted: sgn_sink = -1\n'); end
% Test D: open loop, bridge voltage 0.97 v_bus/N -> bridge current lags the busbar voltage by 90 deg, about 0.3 pu
for it = 1:2
    q = applyFix(p, fix); q.mode = 2; setP(q);
    L = runModel(mdl, 0.10); w = L.t >= 0.06 & L.t < 0.10;
    Ibr = p.Imax/p.Nb;
    pk = max(abs(L.ib(w, :)), [], 'all')/Ibr;
    zi = phasor1(fix.sgn_tr*L.ib(w, 1), L.t(w), W0); zv = phasor1(L.vb(w, 1), L.t(w), W0);
    phi = rad2deg(angle(zi/zv));
    fprintf('  test D (open loop): bridge peak %.2f pu, angle(i/v) = %.1f deg (expected about -90)\n', pk, phi);
    if pk > 2 && it == 1
        fix.sgn_tr = -fix.sgn_tr; fprintf('  -> transformer/bridge polarity reversed: sgn_tr = %d\n', fix.sgn_tr); continue
    end
    if abs(wrap180(phi - 90)) < 45
        fix.sgn_ib = -fix.sgn_ib; fprintf('  -> bridge-current measurement inverted: sgn_ib = %d\n', fix.sgn_ib);
    end
    break
end
assert(pk < 2, 'Open-loop test still gives %.1f pu: check the transformer and bridge connections', pk);
fprintf('--- corrections: sgn_vdc %d, ph_a %.1f, ph_b %.1f, sgn_load %d, sgn_sink %d, sgn_tr %d, sgn_ib %d ---\n\n', ...
        fix.sgn_vdc, fix.ph_a, fix.ph_b, fix.sgn_load, fix.sgn_sink, fix.sgn_tr, fix.sgn_ib);
end

function r = metrics(L, p)
t = L.t; dtl = t(2) - t(1);
n20 = round(0.02/dtl);
sl = t >= p.T_pre + 0.02 & t <= t(end) - 0.02;
Nb = p.Nb; Imax = p.Imax; Ibr = Imax/Nb;
ib = p.sgn_tr*L.ib;
r.Vmin = min(L.vdc(sl)); r.Vmax = max(L.vdc(sl));
Ileg = [sum(ib(:, 1:Nb), 2), sum(ib(:, Nb + 1:2*Nb), 2)];
Z = 2*movmean(Ileg.*exp(-1i*p.W0*t), n20, 1);
r.Ia = max(abs(Z(sl, 1)))/Imax; r.Ib = max(abs(Z(sl, 2)))/Imax;
r.pk = max(abs(ib(sl, :)), [], 'all')/Ibr;
rmsI = sqrt(movmean(ib.^2, n20, 1));
r.rms = max(rmsI(sl, :), [], 'all')/(p.C/Nb/p.VS0);
m = numel(t) - 5*n20 + 1:numel(t);
tdd = zeros(1, 2);
for b = 1:2
    X = fft(Ileg(m, b))/numel(m)*2; f = (0:numel(m) - 1)'/(numel(m)*dtl);
    h = f > 75 & f <= 10e3;
    tdd(b) = sqrt(sum(abs(X(h)).^2))/Imax*100;
end
r.tdd = max(tdd);
r.dmax = max(max(abs(L.lg(sl, 2:3))));
iC = p.Cdc*gradient(L.vdc(m), dtl);
r.ICdc_rms = sqrt(mean(iC.^2));
end

function plotCase(L, p, c, nc, name)
t = L.t; w = t >= p.T_end - 0.04;
subplot(nc, 2, 2*c - 1);
plot(t(w), L.vdc(w)/1e3, 'LineWidth', 0.7); hold on; yline([3.15 3.85], '--k'); grid on;
ylabel('v_{dc} (kV)'); title([strrep(name, '_', '\_') ': DC link (last 40 ms)']);
subplot(nc, 2, 2*c);
plot(t(w), p.sgn_tr*L.ib(w, :)/(p.Imax/p.Nb), 'LineWidth', 0.5); hold on; yline([-1 1], '--k'); grid on;
ylabel('i / rated bridge peak'); title('bridge currents');
end

function y = wrap180(x)
y = mod(x + 180, 360) - 180;
end
