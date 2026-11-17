function mdl = build_rpc_switching_model(Nb, mdl)
%BUILD_RPC_SWITCHING_MODEL  Builds the Simulink / Specialized Power Systems model of one Scott co-phase substation
%   with two RPC legs (Nb single-phase IGBT full bridges per leg) on a common DC link.
%   mdl = build_rpc_switching_model(2)      -> rpc_switching_Nb2.slx
%   Requires Simulink and Simscape Electrical (Specialized Power Systems library 'powerlib').
%   All parameters are read from the base-workspace struct rpcP (see rpc_params.m and run_rpc_checks.m).
%
%   Circuit per feeder b (alpha, beta):
%     AC source (rpcP.Em, phase rpcP.ph_a / ph_b) - R-L Thevenin (rpcP.Rth, rpcP.Lth) - 27.5 kV busbar
%     busbar - controlled current source (train load, alpha only)
%     busbar - Nb x [linear transformer 27.5/2 kV, C/Nb, x = 0.10 pu, r = x/30 - current measurement - IGBT full bridge]
%   DC link: all bridges in parallel, capacitor rpcP.Cdc (initial 3.5 kV), controlled current source (loss sink).
%   Controller: MATLAB Function block with the code of rpc_ctrl_fcn.m (same algorithm as the Python model),
%   measurements delayed by one step (Unit Delay), powergui discrete with step rpcP.dt.

if nargin < 1, Nb = 2; end
if nargin < 2, mdl = sprintf('rpc_switching_Nb%d', Nb); end
P = evalin('base', 'rpcP');
assert(P.Nb == Nb, 'rpcP.Nb (%d) differs from the requested Nb (%d): call rpc_params first', P.Nb, Nb);
load_system('powerlib');
if bdIsLoaded(mdl), close_system(mdl, 0); end
if exist([mdl '.slx'], 'file'), delete([mdl '.slx']); end
new_system(mdl);
set_param(mdl, 'SolverType', 'Fixed-step', 'Solver', 'FixedStepDiscrete', 'FixedStep', 'rpcP.dt', ...
          'StopTime', 'rpcP.T_end', 'SaveTime', 'off', 'SaveOutput', 'off', 'ReturnWorkspaceOutputs', 'off');

B = @(lib, name, pos) add_block(lib, [mdl '/' name], 'Position', pos);
pg = B('powerlib/powergui', 'powergui', [20 20 90 60]);
setp(pg, 'SimulationMode', 'Discrete'); setp(pg, 'SampleTime', 'rpcP.dt');

% ---------------- controller
ctrl = B('simulink/User-Defined Functions/MATLAB Function', 'ctrl', [700 700 900 900]);
code = fileread(fullfile(fileparts(mfilename('fullpath')), 'rpc_ctrl_fcn.m'));
code = strrep(code, 'function [g, iL, isink, lg] = rpc_ctrl_fcn(t, vb, ib, vdc, p)', ...
                    'function [g, iL, isink, lg] = ctrl(t, vb, ib, vdc, rpcP)');
code = strrep(code, '%#codegen', sprintf('%%#codegen\np = rpcP;'));
rt = sfroot;
ch = rt.find('-isa', 'Stateflow.EMChart', 'Path', [mdl '/ctrl']);
ch.Script = code;
d = ch.find('-isa', 'Stateflow.Data', 'Name', 'rpcP');
d.Scope = 'Parameter';
try, d.Tunable = false; catch, warning('Set the parameter rpcP of the MATLAB Function block to non-tunable.'); end

clk = B('simulink/Sources/Clock', 'clock', [560 690 590 710]);
ud_vb = B('simulink/Discrete/Unit Delay', 'ud_vb', [600 740 630 770]);
ud_ib = B('simulink/Discrete/Unit Delay', 'ud_ib', [600 790 630 820]);
ud_vdc = B('simulink/Discrete/Unit Delay', 'ud_vdc', [600 840 630 870]);
for h = [ud_vb ud_ib ud_vdc], set_param(h, 'SampleTime', 'rpcP.dt', 'InitialCondition', '0'); end
set_param(ud_vb, 'InitialCondition', '[rpcP.Em; 0]');
set_param(ud_ib, 'InitialCondition', sprintf('zeros(%d,1)', 2*Nb));
set_param(ud_vdc, 'InitialCondition', 'rpcP.VREF');
sl(mdl, 'clock/1', 'ctrl/1'); sl(mdl, 'ud_vb/1', 'ctrl/2'); sl(mdl, 'ud_ib/1', 'ctrl/3'); sl(mdl, 'ud_vdc/1', 'ctrl/4');
mux_vb = B('simulink/Signal Routing/Mux', 'mux_vb', [520 735 525 775]); set_param(mux_vb, 'Inputs', '2');
mux_ib = B('simulink/Signal Routing/Mux', 'mux_ib', [500 780 505 830]); set_param(mux_ib, 'Inputs', num2str(2*Nb));
g_ib = B('simulink/Math Operations/Gain', 'sgn_ib', [540 790 570 820]); set_param(g_ib, 'Gain', 'rpcP.sgn_ib');
g_vdc = B('simulink/Math Operations/Gain', 'sgn_vdc', [540 840 570 870]); set_param(g_vdc, 'Gain', 'rpcP.sgn_vdc');
sl(mdl, 'mux_vb/1', 'ud_vb/1'); sl(mdl, 'mux_ib/1', 'sgn_ib/1'); sl(mdl, 'sgn_ib/1', 'ud_ib/1'); sl(mdl, 'sgn_vdc/1', 'ud_vdc/1');
dm = B('simulink/Signal Routing/Demux', 'demux_g', [950 700 955 900]);
set_param(dm, 'Outputs', ['[' num2str(4*ones(1, 2*Nb)) ']']);
sl(mdl, 'ctrl/1', 'demux_g/1');

% ---------------- logging: [t vdc vb(2) ib(2Nb) isrc(2) lg(8)] every 10 steps
mux_log = B('simulink/Signal Routing/Mux', 'mux_log', [1000 950 1005 1100]); set_param(mux_log, 'Inputs', '6');
tw = B('simulink/Sinks/To Workspace', 'log', [1040 1010 1100 1040]);
set_param(tw, 'VariableName', 'rpc_log', 'SaveFormat', 'Array', 'Decimation', '10', 'MaxDataPoints', 'inf');
sl(mdl, 'mux_log/1', 'log/1');
sl(mdl, 'clock/1', 'mux_log/1'); sl(mdl, 'sgn_vdc/1', 'mux_log/2'); sl(mdl, 'mux_vb/1', 'mux_log/3');
sl(mdl, 'sgn_ib/1', 'mux_log/4'); sl(mdl, 'ctrl/4', 'mux_log/6');
mux_is = B('simulink/Signal Routing/Mux', 'mux_isrc', [960 980 965 1010]); set_param(mux_is, 'Inputs', '2');
sl(mdl, 'mux_isrc/1', 'mux_log/5');

% ---------------- DC link
cdc = B('powerlib/Elements/Series RLC Branch', 'Cdc', [400 1000 430 1060]);
setp(cdc, 'BranchType', 'C'); setp(cdc, 'Capacitance', 'rpcP.Cdc');
ok = false;
for cand = {{'Setx0', 'InitialVoltage'}, {'SetiC', 'InitialVoltage'}, {'Setx0', 'x0'}}
    try, set_param(cdc, cand{1}{1}, 'on'); set_param(cdc, cand{1}{2}, 'rpcP.VREF'); ok = true; break; catch, end
end
if ~ok
    warning(['Initial voltage of Cdc could not be set: open block Cdc and set the initial capacitor voltage ' ...
             'to rpcP.VREF (3500 V) by hand, otherwise the DC link charges through the diodes at the start.']);
end
vdcm = B('powerlib/Measurements/Voltage Measurement', 'Vdc_meas', [470 1000 500 1030]);
sink = B('powerlib/Electrical Sources/Controlled Current Source', 'loss_sink', [330 1000 360 1060]);
setp(sink, 'Initialize', 'off');
gdc = B('powerlib/Elements/Ground', 'gnd_dc', [400 1100 430 1120]);
nodeP = T(cdc, 1); nodeN = T(cdc, 2);
pc(mdl, T(vdcm, 1), nodeP); pc(mdl, T(vdcm, 2), nodeN);
pc(mdl, T(sink, 1), nodeP); pc(mdl, T(sink, 2), nodeN);
pc(mdl, T(gdc, 1), nodeN);
sl(mdl, 'Vdc_meas/1', 'sgn_vdc/1');
sl(mdl, 'ctrl/3', 'loss_sink/1');

% ---------------- feeders
names = {'a', 'b'}; ph = {'rpcP.ph_a', 'rpcP.ph_b'};
for b = 1:2
    y0 = 100 + (b - 1)*420;
    src = B('powerlib/Electrical Sources/AC Voltage Source', ['src_' names{b}], [40 y0 80 y0 + 40]);
    setp(src, 'Amplitude', 'rpcP.Em'); setp(src, 'Phase', ph{b}); setp(src, 'Frequency', '50');
    gs = B('powerlib/Elements/Ground', ['gnd_src_' names{b}], [40 y0 + 80 70 y0 + 100]);
    cms = B('powerlib/Measurements/Current Measurement', ['isrc_' names{b}], [110 y0 140 y0 + 30]);
    zth = B('powerlib/Elements/Series RLC Branch', ['Zth_' names{b}], [170 y0 210 y0 + 30]);
    setp(zth, 'BranchType', 'RL'); setp(zth, 'Resistance', 'rpcP.Rth'); setp(zth, 'Inductance', 'rpcP.Lth');
    pc(mdl, T(src, 1), T(cms, 1)); pc(mdl, T(src, 2), T(gs, 1));
    pc(mdl, T(cms, 2), T(zth, 1));
    bus = T(zth, 2);
    sl(mdl, sprintf('isrc_%s/1', names{b}), sprintf('mux_isrc/%d', b));
    vm = B('powerlib/Measurements/Voltage Measurement', ['vbus_' names{b}], [250 y0 + 60 280 y0 + 90]);
    gv = B('powerlib/Elements/Ground', ['gnd_vm_' names{b}], [250 y0 + 120 280 y0 + 140]);
    pc(mdl, T(vm, 1), bus); pc(mdl, T(vm, 2), T(gv, 1));
    sl(mdl, sprintf('vbus_%s/1', names{b}), sprintf('mux_vb/%d', b));
    if b == 1
        ld = B('powerlib/Electrical Sources/Controlled Current Source', 'train_load', [250 y0 + 160 280 y0 + 220]);
        setp(ld, 'Initialize', 'off');
        gl = B('powerlib/Elements/Ground', 'gnd_load', [250 y0 + 240 280 y0 + 260]);
        pc(mdl, T(ld, 1), bus); pc(mdl, T(ld, 2), T(gl, 1));
        sl(mdl, 'ctrl/2', 'train_load/1');
    end
    for j = 1:Nb
        x0 = 330 + (j - 1)*260;
        tag = sprintf('%s%d', names{b}, j);
        tr = B('powerlib/Elements/Linear Transformer', ['tr_' tag], [x0 y0 + 40 x0 + 50 y0 + 100]);
        setp(tr, 'UNITS', 'pu', true);
        setp(tr, 'NominalPower', '[rpcP.C/rpcP.Nb 50]');
        setp(tr, 'Winding1', '[rpcP.VBUS_N rpcP.uk_t/rpcP.xr_t/2 rpcP.uk_t/2]');
        setp(tr, 'Winding2', '[rpcP.VS0 rpcP.uk_t/rpcP.xr_t/2 rpcP.uk_t/2]');
        setp(tr, 'ThreeWindings', 'off');
        setp(tr, 'RmLm', '[1e4 1e4]');
        gt = B('powerlib/Elements/Ground', ['gnd_tr_' tag], [x0 y0 + 140 x0 + 30 y0 + 160]);
        cmb = B('powerlib/Measurements/Current Measurement', ['ibr_' tag], [x0 + 80 y0 + 30 x0 + 110 y0 + 60]);
        ub = B('powerlib/Power Electronics/Universal Bridge', ['bridge_' tag], [x0 + 140 y0 + 30 x0 + 200 y0 + 110]);
        setp(ub, 'Arms', '2'); setp(ub, 'Device', 'IGBT / Diodes');
        setp(ub, 'SnubberResistance', '1e6'); setp(ub, 'SnubberCapacitance', 'inf');
        setp(ub, 'Ron', '1e-4'); setp(ub, 'ForwardVoltages', '[0 0]', true);
        W = get_param(tr, 'PortHandles');
        pc(mdl, W.LConn(1), bus); pc(mdl, W.LConn(2), T(gt, 1));
        pc(mdl, W.RConn(1), T(cmb, 1)); pc(mdl, T(cmb, 2), TN(ub, 'A', 'L', 1));
        pc(mdl, W.RConn(2), TN(ub, 'B', 'L', 2));
        pc(mdl, TN(ub, '+', 'R', 1), nodeP); pc(mdl, TN(ub, '-', 'R', 2), nodeN);
        k = (b - 1)*Nb + j;
        sl(mdl, sprintf('ibr_%s/1', tag), sprintf('mux_ib/%d', k));
        sl(mdl, sprintf('demux_g/%d', k), sprintf('bridge_%s/1', tag));
    end
end
try
    Simulink.BlockDiagram.arrangeSystem(mdl);
catch
end
save_system(mdl);
fprintf('Model %s.slx built (Nb = %d).\n', mdl, Nb);
end

% ---------------- helpers
function setp(h, prm, val, optional)
if nargin < 4, optional = false; end
try
    set_param(h, prm, val);
catch err
    if optional
        warning('Optional parameter %s of %s not set (%s); check it in the block dialog.', prm, getfullname(h), err.message);
        return
    end
    dp = fieldnames(get_param(h, 'DialogParameters'));
    error('build:param', 'Could not set %s = %s on %s (%s).\nDialog parameters of this block: %s', ...
          prm, val, getfullname(h), err.message, strjoin(dp', ', '));
end
end

function sl(mdl, a, b)
add_line(mdl, a, b, 'autorouting', 'on');
end

function h = T(blk, i)
% i-th physical terminal of a two-terminal block (left connections first, then right connections)
ph = get_param(blk, 'PortHandles');
all = [ph.LConn ph.RConn];
assert(numel(all) >= i, 'Block %s has only %d physical terminals', getfullname(blk), numel(all));
h = all(i);
end

function h = U(blk, side, i)
ph = get_param(blk, 'PortHandles');
if side == 'L', h = ph.LConn(i); else, h = ph.RConn(i); end
end

function h = TN(blk, name, side, idx)
% terminal of a power-electronics block found by the name of the internal physical port (falls back to position)
ph = get_param(blk, 'PortHandles');
pm = find_system(blk, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'SearchDepth', 1, 'BlockType', 'PMIOPort');
h = [];
for k = 1:numel(pm)
    if strcmp(get_param(pm(k), 'Name'), name)
        sd = get_param(pm(k), 'Side');
        same = pm(strcmp(get_param(pm, 'Side'), sd));
        nums = cellfun(@str2double, get_param(same, 'Port'));
        rank = find(sort(nums) == str2double(get_param(pm(k), 'Port')), 1);
        if strcmpi(sd, 'Left'), h = ph.LConn(rank); else, h = ph.RConn(rank); end
        fprintf('  %s: terminal "%s" = %s connection %d\n', getfullname(blk), name, sd, rank);
        return
    end
end
if side == 'L', h = ph.LConn(idx); else, h = ph.RConn(idx); end
fprintf('  %s: terminal "%s" not found by name, using %s connection %d\n', getfullname(blk), name, side, idx);
end

function pc(mdl, h1, h2)
add_line(mdl, h1, h2, 'autorouting', 'on');
end
