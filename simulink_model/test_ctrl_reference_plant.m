function r = test_ctrl_reference_plant(caseName, T, varargin)
%TEST_CTRL_REFERENCE_PLANT  Runs rpc_ctrl_fcn.m with the circuit equations of the Python model (no Simulink).
%   Used to check that the MATLAB controller reproduces the Python model before it is put into Simulink.
%   r = test_ctrl_reference_plant('S1_sustained', 1.2, 'dt', 2e-6)
p = rpc_params(caseName, varargin{:});
clear rpc_ctrl_fcn
Nb = p.Nb; dt = p.dt; n = round(T/dt);
Lj = Nb*p.Lt; Rj = Nb*p.Rt; N = p.N_TR;
kd = Nb*p.Lth/(N^2*Lj); kc = p.Lth/(N*Lj); inv1kd = 1/(1 + kd);
I = zeros(2, Nb); V = p.VREF;
vb = [p.Em; 0]; ib = zeros(2*Nb, 1); vdc = V;
dec = round(10e-6/dt); m = floor(n/dec);
LT = zeros(m, 1); LV = zeros(m, 1); LI = zeros(m, 2, Nb); LVB = zeros(m, 2);
il = 0; iL_prev = 0;
for k = 0:n - 1
    t = k*dt;
    [g, iL, isink, ~] = rpc_ctrl_fcn(t, vb, ib, vdc, p);       % measurements of the previous step
    s = zeros(2, Nb);
    for b = 1:2
        for j = 1:Nb
            o = ((b - 1)*Nb + (j - 1))*4;
            s(b, j) = g(o + 1) - g(o + 3);
        end
    end
    diL = (iL - iL_prev)/dt; if k == 0, diL = 0; end
    iL_prev = iL;
    % RK4 with held switching states and a linear load current
    f = @(tt, Ic, Vc) rhs(tt, Ic, Vc, s, iL + (tt - t)*diL, diL, p, Rj, Lj, kc, inv1kd, isink);
    [k1I, k1V, vb1] = f(t, I, V);
    [k2I, k2V] = f(t + dt/2, I + dt/2*k1I, V + dt/2*k1V);
    [k3I, k3V] = f(t + dt/2, I + dt/2*k2I, V + dt/2*k2V);
    [k4I, k4V] = f(t + dt, I + dt*k3I, V + dt*k3V);
    I = I + dt/6*(k1I + 2*k2I + 2*k3I + k4I);
    V = V + dt/6*(k1V + 2*k2V + 2*k3V + k4V);
    vb = vb1; ib = reshape(I', [], 1); vdc = V;
    if mod(k, dec) == 0 && il < m
        il = il + 1; LT(il) = t; LV(il) = V; LI(il, :, :) = reshape(I, 1, 2, Nb); LVB(il, :) = vb1';
    end
end
r = struct('t', LT(1:il), 'V', LV(1:il), 'I', LI(1:il, :, :), 'vbus', LVB(1:il, :), 'p', p);
end

function [dI, dV, vbo] = rhs(tt, Ic, Vc, s, iLs, diL, p, Rj, Lj, kc, inv1kd, isink)
Nb = size(Ic, 2); N = p.N_TR;
dI = zeros(2, Nb); dcI = 0; vbo = zeros(2, 1);
for b = 1:2
    if b == 1
        e = p.Em*cos(p.W0*tt); iLb = iLs; diLb = diL;
    else
        e = -p.Em*sin(p.W0*tt); iLb = 0; diLb = 0;
    end
    sumi = sum(Ic(b, :)); sumv = sum(Rj*Ic(b, :) + s(b, :)*Vc);
    isrc = iLb + sumi/N;
    v = (e - p.Rth*isrc - p.Lth*diLb + kc*sumv)*inv1kd;
    vbo(b) = v;
    dI(b, :) = (v/N - Rj*Ic(b, :) - s(b, :)*Vc)/Lj;
    dcI = dcI + sum(s(b, :).*Ic(b, :));
end
dV = (dcI - isink*1)/p.Cdc;     % isink is psink/V (A)
end
