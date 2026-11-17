function build_validation_model(varargin)
%BUILD_VALIDATION_MODEL  Build the two Simulink models of the validation package.
%
%   build_validation_model                      build both models
%   build_validation_model('which','net')       only the network model  (cases A, B)
%   build_validation_model('which','avg')       only the averaged RPC   (case C)
%   build_validation_model('flip_teaser',true)  reverse the polarity of the teaser secondary
%                                               (run_validation does this automatically if its
%                                               polarity self-test fails)
%   build_validation_model('source','branch')   ideal Three-Phase Source + explicit RL branch
%                                               instead of the source's own short-circuit-level
%                                               impedance (fallback if the block parameters of
%                                               your release differ)
%
%   Network model  rpc_val_net.slx  (Simscape Electrical, Specialized Power Systems, discrete):
%     Three-Phase Source (110 kV, 50 Hz, Ssc, X/R = 10)
%       -> Three-Phase V-I Measurement (PCC)
%       -> Scott transformer made of single-phase Linear Transformers:
%            main  = two identical half-windings M1, M2 in series (centre-tapped primary B-C),
%            teaser T (primary A - centre tap, 110*sqrt(3)/2 kV)
%          leakage of each leg: 40 MVA, uk = 10.5 %, X/R = 30, referred to the 27.5 kV side
%       -> feeder alpha (main secondary) and feeder beta (teaser secondary), each with
%          current measurement, voltage measurement, Series RLC Load (constant impedance /
%          iterated constant power) and a Controlled Current Source (ideal converter, constant
%          current), and a Ground reference.
%   Averaged model  rpc_val_avg.slx : Integrator + Interpreted MATLAB Function (rpc_avg_rhs.m).
%
%   All block parameters are workspace variable names; run_validation.m assigns them.
%   If a block parameter name differs in your release, the error message lists the valid names:
%   copy that message when asking for help (or follow the manual block list in README_VI.md).

p = inputParser;
addParameter(p, 'which', 'both');
addParameter(p, 'flip_teaser', false);
addParameter(p, 'source', 'builtin');
addParameter(p, 'outdir', '');
parse(p, varargin{:});
opt = p.Results;

here = fileparts(mfilename('fullpath'));
root = fileparts(here);
if isempty(opt.outdir), opt.outdir = fullfile(root, 'simulink_models'); end
if ~exist(opt.outdir, 'dir'), mkdir(opt.outdir); end
ref = read_ref(here);
K = ref.constants;

load_system('powerlib');
load_system('simulink');

if any(strcmp(opt.which, {'both', 'net'}))
    assign_net_defaults(K);
    build_net('rpc_val_net', K, opt);
end
if any(strcmp(opt.which, {'both', 'avg'}))
    assign_avg_defaults(ref);
    build_avg('rpc_val_avg', ref, opt);
end
fprintf('build_validation_model: done. Models saved in %s\n', opt.outdir);
end

%% ----------------------------------------------------------------------------------------
function ref = read_ref(here)
f = fullfile(here, '..', 'python_reference.json');
if ~exist(f, 'file'), f = fullfile(here, 'python_reference.json'); end
if ~exist(f, 'file'), error('python_reference.json not found next to the matlab folder'); end
ref = jsondecode(fileread(f));
end

function assign_net_defaults(K)
w = 2*pi*K.f_Hz;
assignin('base', 'Vp_V', K.V_prim_kV*1e3);
assignin('base', 'fn_Hz', K.f_Hz);
assignin('base', 'XR_src', K.XR_source);
assignin('base', 'Ssc_VA', 500e6);
Zs = (K.V_prim_kV*1e3)^2/500e6;
Rs = Zs/sqrt(1 + K.XR_source^2);
assignin('base', 'Rs_ohm', Rs);
assignin('base', 'Ls_H', Rs*K.XR_source/w);
assignin('base', 'Ts_s', 50e-6);
assignin('base', 'T_stop_s', 2.0);
tags = {'a', 'b'};
for i = 1:2
    t = tags{i};
    assignin('base', ['P' t '_W'], 1);          % 1 W: practically open
    assignin('base', ['QL' t '_var'], 0);
    assignin('base', ['QC' t '_var'], 0);
    assignin('base', ['Vn' t '_V'], K.V_sec_kV*1e3);
    assignin('base', ['Ci_' t '_amp'], 0);
    assignin('base', ['Ci_' t '_ph'], 0);
end
end

function assign_avg_defaults(ref)
pc = ref.caseC;
P = pc.P_MW(:); Q = pc.Q_Mvar(:);
tt = (0:numel(P)-1)';
assignin('base', 'PLts', [tt P]);
assignin('base', 'QLts', [tt Q]);
assignin('base', 't_step_s', pc.t_step_s);
assignin('base', 'step_MW', pc.step_MW);
assignin('base', 'T_stop_C', numel(P) - 1);
assignin('base', 'x0_vec', pc.variants(1).x0(:));
end

%% ---------------------------------------------------------------------------- network model
function build_net(mdl, K, opt)
if bdIsLoaded(mdl), close_system(mdl, 0); end
new_system(mdl);
lib = 'powerlib/';
w = 2*pi*K.f_Hz;
Vp = K.V_prim_kV*1e3;  Vs = K.V_sec_kV*1e3;  Pleg = K.leg_MVA*1e6;
Zb2 = Vs^2/Pleg;                                   % leg base impedance at 27.5 kV
zleg = K.uk_pu*Zb2;
Rleg = zleg/sqrt(1 + K.XR_leg^2);
Lleg = Rleg*K.XR_leg/w;

% ---- source (+ optional explicit impedance) ----
src = add(mdl, [lib 'Electrical Sources/Three-Phase Source'], 'Source', [30 120 100 220]);
setp(src, 'Voltage', 'Vp_V', 'PhaseAngle', '0', 'Frequency', 'fn_Hz', 'InternalConnection', 'Yg');
useBranch = strcmp(opt.source, 'branch');
if ~useBranch
    try
        trysetp(src, 'NonIdealSource', 'on');
        setp(src, 'SpecifyImpedance', 'on', 'ShortCircuitLevel', 'Ssc_VA', ...
             'BaseVoltage', 'Vp_V', 'XRratio', 'XR_src');
    catch ME
        warning('build:source', ['Three-Phase Source short-circuit parameters not accepted (%s)\n' ...
                'Falling back to ideal source + explicit RL branch.'], ME.message);
        useBranch = true;
    end
end
if useBranch
    if ~trysetp(src, 'NonIdealSource', 'off')
        trysetp(src, 'SpecifyImpedance', 'off', 'Resistance', '1e-6', 'Inductance', '1e-9');
    end
    zsb = add(mdl, [lib 'Elements/Three-Phase Series RLC Branch'], 'Zs', [140 120 200 220]);
    setp(zsb, 'BranchType', 'RL', 'Resistance', 'Rs_ohm', 'Inductance', 'Ls_H');
end

% ---- PCC measurement ----
pcc = add(mdl, [lib 'Measurements/Three-Phase V-I Measurement'], 'PCC', [260 120 320 220]);
setp(pcc, 'VoltageMeasurement', 'phase-to-ground', 'CurrentMeasurement', 'yes');
phS = get_param(src, 'PortHandles');
phP = get_param(pcc, 'PortHandles');
if useBranch
    phZ = get_param(zsb, 'PortHandles');
    for i = 1:3
        add_line(mdl, phS.RConn(i), phZ.LConn(i));
        add_line(mdl, phZ.RConn(i), phP.LConn(i));
    end
else
    for i = 1:3
        add_line(mdl, phS.RConn(i), phP.LConn(i));
    end
end
if numel(phP.Outport) < 2
    error('build:vi', 'Three-Phase V-I Measurement has %d signal outputs (expected 2: Vabc, Iabc)', numel(phP.Outport));
end
tw(mdl, 'Vpcc', phP.Outport(1), [380 100 440 120]);
tw(mdl, 'Ipcc', phP.Outport(2), [380 150 440 170]);
try_seq(mdl, phP.Outport(1), 'SeqV', [380 200 440 220]);
try_seq(mdl, phP.Outport(2), 'SeqI', [380 250 440 270]);

% ---- Scott transformer ----
R1f = 1e-5; Rm_pu = 1e5;
M1 = add(mdl, [lib 'Elements/Linear Transformer'], 'M1', [420 330 480 410]);
M2 = add(mdl, [lib 'Elements/Linear Transformer'], 'M2', [420 460 480 540]);
Tt = add(mdl, [lib 'Elements/Linear Transformer'], 'T',  [420 200 480 280]);
lintr(M1, Vp/2,        Vs/2, Pleg/2, Rleg/2, Lleg/2, w, R1f, Rm_pu, K.f_Hz);
lintr(M2, Vp/2,        Vs/2, Pleg/2, Rleg/2, Lleg/2, w, R1f, Rm_pu, K.f_Hz);
lintr(Tt, Vp*sqrt(3)/2, Vs,   Pleg,   Rleg,   Lleg,   w, R1f, Rm_pu, K.f_Hz);
pM1 = get_param(M1, 'PortHandles');
pM2 = get_param(M2, 'PortHandles');
pT  = get_param(Tt, 'PortHandles');
% primary: A -> teaser(+), B -> M1(+), C -> M2(-); centre tap N joins M1(-), M2(+), T(-)
add_line(mdl, phP.RConn(1), pT.LConn(1));
add_line(mdl, phP.RConn(2), pM1.LConn(1));
add_line(mdl, phP.RConn(3), pM2.LConn(2));
join(mdl, pM1.LConn(2), pM2.LConn(1), pT.LConn(2));
% secondary of the main transformer: M1 and M2 in series (aiding)
add_line(mdl, pM1.RConn(2), pM2.RConn(1));
if opt.flip_teaser
    tPlus = pT.RConn(2);  tMinus = pT.RConn(1);
else
    tPlus = pT.RConn(1);  tMinus = pT.RConn(2);
end

% ---- feeders ----
feeder(mdl, 'a', pM1.RConn(1), pM2.RConn(2), 560, 330);
feeder(mdl, 'b', tPlus, tMinus, 560, 200);

% ---- powergui and solver ----
pg = add(mdl, 'powerlib/powergui', 'powergui', [30 20 120 60]);
setp(pg, 'SimulationMode', 'Discrete', 'SampleTime', 'Ts_s');
set_param(mdl, 'SolverType', 'Fixed-step', 'Solver', 'FixedStepDiscrete', ...
    'FixedStep', 'Ts_s', 'StopTime', 'T_stop_s');

save_system(mdl, fullfile(opt.outdir, mdl));
fprintf('build_validation_model: %s built (flip_teaser=%d, builtin source impedance=%d).\n', ...
    mdl, opt.flip_teaser, ~useBranch);

% ---- smoke test ----
try
    sim(mdl, 'StopTime', '0.1');
    fprintf('build_validation_model: smoke test of %s OK.\n', mdl);
catch ME
    fprintf(2, ['build_validation_model: model %s was built but the smoke test FAILED:\n%s\n' ...
        'Typical causes: floating/singular circuit, parameter names. See README_VI.md.\n'], mdl, ME.message);
end
end

function lintr(blk, V1, V2, Pn, R2, L2, w, R1f, Rm_pu, fn)
% Linear Transformer in SI units. Leakage on the secondary (R2, L2); the primary leakage is
% made negligible (1e-5 pu) because only the secondary leakage is part of the study model.
Zb1 = V1^2/Pn;
setp(blk, 'UNITS', 'SI');
setp(blk, 'NominalPower', mat2str([Pn fn]));
setp(blk, 'Winding1', mat2str([V1, R1f*Zb1, R1f*Zb1/w]));
setp(blk, 'Winding2', mat2str([V2, R2, L2]));
setp(blk, 'RmLm', mat2str([Rm_pu*Zb1, Rm_pu*Zb1/w]));
end

function feeder(mdl, t, pPlus, pMinus, x, y)
lib = 'powerlib/';
Im = add(mdl, [lib 'Measurements/Current Measurement'], ['Im_' t], [x y x+40 y+30]);
Vm = add(mdl, [lib 'Measurements/Voltage Measurement'], ['Vm_' t], [x+160 y+60 x+200 y+100]);
Ld = add(mdl, [lib 'Elements/Series RLC Load'],         ['Load_' t], [x+100 y-70 x+140 y-20]);
setp(Ld, 'NominalVoltage', ['Vn' t '_V'], 'NominalFrequency', 'fn_Hz', ...
     'ActivePower', ['P' t '_W'], 'InductivePower', ['QL' t '_var'], 'CapacitivePower', ['QC' t '_var']);
Cs = add(mdl, [lib 'Electrical Sources/Controlled Current Source'], ['Ccs_' t], [x+100 y+110 x+140 y+160]);
Sw = add(mdl, 'simulink/Sources/Sine Wave', ['Sine_' t], [x+20 y+120 x+60 y+150]);
setp(Sw, 'Amplitude', ['Ci_' t '_amp'], 'Frequency', '2*pi*fn_Hz', 'Phase', ['Ci_' t '_ph'], ...
     'Bias', '0', 'SampleTime', '0');
Gn = add(mdl, [lib 'Elements/Ground'], ['Gnd_' t], [x+230 y+160 x+250 y+180]);
pI = get_param(Im, 'PortHandles');  pV = get_param(Vm, 'PortHandles');
pL = get_param(Ld, 'PortHandles');  pC = get_param(Cs, 'PortHandles');
pG = get_param(Gn, 'PortHandles');
cI = [pI.LConn(:); pI.RConn(:)];  cV = [pV.LConn(:); pV.RConn(:)];
cL = [pL.LConn(:); pL.RConn(:)];  cC = [pC.LConn(:); pC.RConn(:)];
cG = [pG.LConn(:); pG.RConn(:)];
if numel(cV) < 2 || numel(cI) < 2 || numel(cL) < 2 || numel(cC) < 2
    error('build:ports', 'unexpected number of connection ports on a feeder block');
end
add_line(mdl, pPlus, cI(1));                       % transformer + -> current sensor
join(mdl, cI(2), cL(1), cC(1), cV(1));             % load + node
join(mdl, pMinus, cL(2), cC(2), cV(2), cG(1));     % load - node (grounded)
pS = get_param(Sw, 'PortHandles');
add_line(mdl, pS.Outport(1), pC.Inport(1));        % sine reference -> controlled current source
tw(mdl, ['V' t], pickout(Vm), [x+260 y+60 x+320 y+80]);
tw(mdl, ['I' t], pickout(Im), [x+260 y x+320 y+20]);
end

function ph = pickout(blk)
q = get_param(blk, 'PortHandles');
ph = q.Outport(1);
end

%% ------------------------------------------------------------------------ averaged RPC model
function build_avg(mdl, ref, opt)
if bdIsLoaded(mdl), close_system(mdl, 0); end
new_system(mdl);
a = @(lib, name, pos) add(mdl, lib, name, pos);
a('simulink/Sources/From Workspace', 'PLin', [30 30 100 60]);
a('simulink/Sources/From Workspace', 'QLin', [30 190 100 220]);
a('simulink/Sources/Step', 'Pstep', [30 90 100 120]);
a('simulink/Math Operations/Sum', 'SumP', [150 55 180 100]);
a('simulink/Signal Routing/Mux', 'Mux', [260 100 265 200]);
f = pick_block({'simulink/User-Defined Functions/Interpreted MATLAB Function', ...
                'simulink/User-Defined Functions/Interpreted MATLAB Fcn'});
a(f, 'Rhs', [320 130 430 170]);
a('simulink/Continuous/Integrator', 'Int', [480 130 520 170]);
a('simulink/Sinks/To Workspace', 'Xout', [580 130 640 170]);
setp([mdl '/PLin'], 'VariableName', 'PLts', 'Interpolate', 'on', 'SampleTime', '0');
setp([mdl '/QLin'], 'VariableName', 'QLts', 'Interpolate', 'on', 'SampleTime', '0');
setp([mdl '/Pstep'], 'Time', 't_step_s', 'Before', '0', 'After', 'step_MW', 'SampleTime', '0');
setp([mdl '/SumP'], 'Inputs', '++');
setp([mdl '/Mux'], 'Inputs', '3');
setp([mdl '/Rhs'], 'MATLABFcn', 'rpc_avg_rhs', 'OutputDimensions', '8');
setp([mdl '/Int'], 'InitialCondition', 'x0_vec');
setp([mdl '/Xout'], 'VariableName', 'Xout', 'SaveFormat', 'Array', 'SampleTime', '-1', 'MaxDataPoints', 'inf');
add_line(mdl, 'PLin/1', 'SumP/1');
add_line(mdl, 'Pstep/1', 'SumP/2');
add_line(mdl, 'SumP/1', 'Mux/2');
add_line(mdl, 'QLin/1', 'Mux/3');
add_line(mdl, 'Int/1', 'Mux/1');
add_line(mdl, 'Mux/1', 'Rhs/1');
add_line(mdl, 'Rhs/1', 'Int/1');
add_line(mdl, 'Int/1', 'Xout/1');
set_param(mdl, 'SolverType', 'Variable-step', 'Solver', 'ode45', 'MaxStep', '2e-3', ...
    'RelTol', '1e-8', 'AbsTol', '1e-9', 'StopTime', 'T_stop_C');
save_system(mdl, fullfile(opt.outdir, mdl));
fprintf('build_validation_model: %s built.\n', mdl);
end

%% -------------------------------------------------------------------------------- helpers
function h = add(mdl, lib, name, pos)
h = [mdl '/' name];
try
    add_block(lib, h, 'Position', pos);
catch ME
    error('build:addblock', 'Cannot add block "%s" (%s): %s', lib, name, ME.message);
end
end

function f = pick_block(cands)
f = '';
for i = 1:numel(cands)
    try
        get_param(cands{i}, 'Handle');
        f = cands{i};
        return
    catch
    end
end
error('build:lib', 'None of the library blocks exists: %s', strjoin(cands, ' | '));
end

function setp(blk, varargin)
for k = 1:2:numel(varargin)
    try
        set_param(blk, varargin{k}, varargin{k+1});
    catch ME
        dp = '';
        try
            dp = strjoin(fieldnames(get_param(blk, 'DialogParameters'))', ', ');
        catch
        end
        error('build:param', ['Cannot set parameter "%s" of block %s: %s\n' ...
            'Valid dialog parameters of this block: %s'], varargin{k}, blk, ME.message, dp);
    end
end
end

function ok = trysetp(blk, varargin)
ok = true;
for k = 1:2:numel(varargin)
    try
        set_param(blk, varargin{k}, varargin{k+1});
    catch
        ok = false;
    end
end
end

function join(mdl, varargin)
% connect all given connection ports to the first one (one electrical node)
for k = 2:numel(varargin)
    add_line(mdl, varargin{1}, varargin{k});
end
end

function tw(mdl, name, outport, pos)
blk = add(mdl, 'simulink/Sinks/To Workspace', name, pos);
setp(blk, 'VariableName', name, 'SaveFormat', 'Array', 'SampleTime', '-1', 'MaxDataPoints', 'inf');
pt = get_param(blk, 'PortHandles');
add_line(mdl, outport, pt.Inport(1));
end

function try_seq(mdl, outport, name, pos)
% optional Sequence Analyzer (positive and negative sequence); skipped silently if the block or
% its parameters are not available. run_validation.m does not depend on it (it uses a DFT).
cands = {'powerlib_meas/Sequence Analyzer', 'powerlib_meas/Measurements/Sequence Analyzer', ...
         'powerlib/Measurements/Sequence Analyzer'};
for i = 1:numel(cands)
    for sq = {'Positive', 'Negative'}
        nm = [name '_' lower(sq{1}(1:3))];
        try
            b = [mdl '/' nm];
            add_block(cands{i}, b, 'Position', pos + [0 40*strcmp(sq{1}, 'Negative') 0 40*strcmp(sq{1}, 'Negative')]);
            trysetp(b, 'Sequence', sq{1}, 'Frequency', 'fn_Hz');
            pb = get_param(b, 'PortHandles');
            add_line(mdl, outport, pb.Inport(1));
            tw2 = [mdl '/' nm '_out'];
            add_block('simulink/Sinks/To Workspace', tw2, 'Position', pos + [90 40*strcmp(sq{1}, 'Negative') 90 40*strcmp(sq{1}, 'Negative')]);
            set_param(tw2, 'VariableName', nm, 'SaveFormat', 'Array', 'SampleTime', '-1');
            pw = get_param(tw2, 'PortHandles');
            add_line(mdl, pb.Outport(1), pw.Inport(1));
        catch
            try, delete_block([mdl '/' nm]); catch, end
            try, delete_block([mdl '/' nm '_out']); catch, end
        end
    end
end
end
