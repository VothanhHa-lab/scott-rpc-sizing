function [g, iL, isink, lg] = rpc_ctrl_fcn(t, vb, ib, vdc, p)
%#codegen
% Controller, PWM and load-current command of the switching RPC model; runs every plant step p.dt.
% Same algorithm as _sim() in sw_rpc.py (Python).  Inputs are the measurements delayed by one step:
%   vb  [2x1]      busbar voltages alpha, beta (27.5 kV side)
%   ib  [2*Nb x 1] bridge currents (2 kV side, + from the busbar into the converter), alpha bridges first
%   vdc            DC-link voltage
% Outputs:
%   g   [8*Nb x 1] gate signals: per bridge [A_up A_low B_up B_low], alpha bridges first
%   iL             load-current command for the controlled current source on the alpha busbar
%   isink          DC loss-sink current command (A)
%   lg  [8x1]      log: sx, d_alpha, d_beta, iref_alpha, iref_beta, P_load, Q_load, U_alpha
% p.mode: 0 normal; 1 all gates off; 2 open-loop test (bridge voltage 0.97 vb/N); 3 gates off + resistive test
%         load p.Iload_test on alpha; 4 gates off + DC sink 200 A
Nb = p.Nb;
persistent init k xs ry re1 Pm Qm integ nt1 nt2 d_now d_next acc_i acc_v acc_V acc_n psink Vm_prev
persistent qbuf qptr pvfs pvqs sx_hold U_hold iref_hold
if isempty(init)
    init = 1; k = 0;
    xs = [p.Em 0; 0 p.Em];          % SOGI states (alpha: cos, beta: cos(wt+90deg))
    ry = zeros(2, 3, 2); re1 = zeros(2, 1);
    Pm = 0; Qm = 0; integ = 0;
    nt1 = (p.nb0 - p.na2)*p.Wref; nt2 = nt1;
    d_now = zeros(2, 1); d_next = zeros(2, 1);
    acc_i = zeros(2, 1); acc_v = zeros(2, 1); acc_V = 0; acc_n = 0;
    psink = 0; Vm_prev = p.VREF;
    qbuf = zeros(p.nq, 1);
    for ii = 1:p.nq
        qbuf(ii) = p.Em*cos(-p.W0*p.dt*(p.nq - ii + 1));
    end
    qptr = 1; pvfs = p.Em; pvqs = 0;
    sx_hold = 0; U_hold = 1; iref_hold = zeros(2, 1);
end
ibs = p.sgn_tr*ib;

% ---------------- schedule
K = numel(p.Pk);
tau = t - p.T_pre;
if tau <= 0
    Pt = p.Pk(1); Qt = p.Qk(1);
else
    idx = floor(tau);
    if idx >= K - 1
        Pt = p.Pk(K); Qt = p.Qk(K);
    else
        fr = tau - idx;
        Pt = p.Pk(idx + 1) + fr*(p.Pk(idx + 2) - p.Pk(idx + 1));
        Qt = p.Qk(idx + 1) + fr*(p.Qk(idx + 2) - p.Qk(idx + 1));
    end
end
if t < p.T_ramp
    lam = t/p.T_ramp; Pt = Pt*lam; Qt = Qt*lam;
end
rr = min(max((t - p.t_ev)/p.Tr, 0), 1);
Pt = Pt + p.dPs*rr; Qt = Qt + p.dQs*rr;

% ---------------- digital controller at the sampling instants
if mod(k, p.Ts_n) == 0
    d_now = d_next;
    if acc_n > 0
        im = acc_i/acc_n; vm = acc_v/acc_n; Vm_dc = acc_V/acc_n;
    else
        im = [0; 0]; vm = [p.Em; 0]; Vm_dc = vdc;
    end
    acc_i(:) = 0; acc_v(:) = 0; acc_V = 0; acc_n = 0;
    vfk = zeros(2, 1); vqk = zeros(2, 1);
    c = cos(p.cal_ph); sn = sin(p.cal_ph);
    for b = 1:2
        x0 = p.Ad(1,1)*xs(b,1) + p.Ad(1,2)*xs(b,2) + p.Bd(1)*vm(b);
        x1 = p.Ad(2,1)*xs(b,1) + p.Ad(2,2)*xs(b,2) + p.Bd(2)*vm(b);
        xs(b,1) = x0; xs(b,2) = x1;
        vfk(b) = (x0*c - x1*sn)/p.cal_g;
        vqk(b) = (x0*sn + x1*c)/p.cal_g;
    end
    Vma = sqrt(vfk(1)^2 + vqk(1)^2); Vmb = sqrt(vfk(2)^2 + vqk(2)^2);
    Ua = Vma/(sqrt(2)*p.VBUS_N);
    Pm = Pm + p.a50*(Pt - Pm); Qm = Qm + p.a50*(Qt - Qm);
    S = hypot(Pm, Qm);
    req = max(0, S - p.eps_u/100*p.Ssc*1e6)/2;
    lim = p.C*min(Ua, 1);
    sx = min(req, p.KAPPA*lim);
    Sg = max(S, 1e3);
    Px = sx*Pm/Sg; qx = sx*Qm/Sg;
    sh = sx/p.C;
    ploss = 2*p.C*(p.K0 + p.K1*sh + p.K2*sh^2);
    psink = p.ploss_scale*2*p.C*(p.K0 + p.K1*sh + (p.K2 - p.rt_pu)*sh^2);
    W = 0.5*p.Cdc*Vm_dc^2;
    y = p.nb0*W + nt1;
    nt1 = p.nb1*W - p.na1*y + nt2;
    nt2 = p.nb0*W - p.na2*y;
    eW = p.Wref - y;
    Ppi = p.Kpw*eW + integ;
    Pmx = [Vma; Vmb]*(p.Imax/(2*p.N_TR));
    Pr = [-Px; p.ff*(Px + ploss) + Ppi];
    Qr = [-qx; qx];
    Pc = zeros(2, 1); Qc = zeros(2, 1);
    for b = 1:2
        Pc(b) = min(max(Pr(b), -Pmx(b)), Pmx(b));
        qm = sqrt(max(Pmx(b)^2 - Pc(b)^2, 0));
        Qc(b) = min(max(Qr(b), -qm), qm);
    end
    awc = Pc(2) - Pr(2);
    integ = integ + p.Ts*(p.Kiw*eW + p.Kb*awc);
    integ = min(max(integ, -Pmx(2)), Pmx(2));
    Vpred = Vm_dc + p.v_pred*2*(Vm_dc - Vm_prev);
    Vm_prev = Vm_dc;
    Vdc_s = max(Vpred, 100);
    cb = cos(-p.W0*p.Ts/2); sb = sin(-p.W0*p.Ts/2);
    gav = sin(p.W0*p.Ts/2)/(p.W0*p.Ts/2);
    ca = cos(1.5*p.W0*p.Ts); sa = sin(1.5*p.W0*p.Ts);
    for b = 1:2
        vf = vfk(b); vq = vqk(b);
        Vm2 = vf^2 + vq^2;
        vfm = vf*cb - vq*sb; vqm = vf*sb + vq*cb;
        iref = gav*(2*p.N_TR/max(Vm2, 1))*(Pc(b)*vfm + Qc(b)*vqm);
        iref_hold(b) = iref;
        e = iref - im(b);
        yrs = zeros(3, 1); ysum = 0;
        for q = 1:3
            yrs(q) = 2*p.cwT(q)*ry(b,q,1) - ry(b,q,2) + p.krh(q)*p.Ts*(p.cphi(q)*e - p.cphi1(q)*re1(b));
            ysum = ysum + yrs(q);
        end
        u = p.Kp*e + ysum;
        vff = (vf*ca - vq*sa)/p.N_TR;
        vcs = p.kff*vff - u;
        dc = vcs/Vdc_s;
        dl = min(max(dc, -p.mlim), p.mlim);
        if dl == dc
            for q = 1:3
                ry(b,q,2) = ry(b,q,1); ry(b,q,1) = yrs(q);
            end
            re1(b) = e;
        end
        d_next(b) = dl;
    end
    sx_hold = sx; U_hold = Ua;
end

% ---------------- PWM (unipolar, interleaved carriers), gate signals
g = zeros(8*Nb, 1);
Tc = 1/p.fc;
for b = 1:2
    for j = 1:Nb
        if p.mode == 2
            dd = 0.97*vb(b)/p.N_TR/max(vdc, 100);
        else
            dd = d_now(b);
        end
        ph = mod(t/Tc + (j - 1)/(2*Nb), 1);
        if ph < 0.5, cr = 4*ph - 1; else, cr = 3 - 4*ph; end
        sA = double(dd > cr); sB = double(-dd > cr);
        if p.sgn_tr < 0, tmp = sA; sA = sB; sB = tmp; end
        o = ((b - 1)*Nb + (j - 1))*4;
        g(o + 1) = sA; g(o + 2) = 1 - sA; g(o + 3) = sB; g(o + 4) = 1 - sB;
    end
end
if p.mode == 1 || p.mode == 3 || p.mode == 4
    g(:) = 0;
end

% ---------------- load current from the plant-side SOGI (constant power, sinusoidal)
pvq = qbuf(qptr);
Vm2p = pvfs^2 + pvq^2;
iL = (2/Vm2p)*(Pt*pvfs + Qt*pvq);
pvf_old = pvfs;
pvfs = pvfs + p.dt*p.W0*(sqrt(2)*(vb(1) - pvfs) - pvqs);
pvqs = pvqs + p.dt*p.W0*pvfs;
qbuf(qptr) = pvf_old; qptr = qptr + 1; if qptr > p.nq, qptr = 1; end
isink = psink/max(vdc, 100);
if p.mode == 1 || p.mode == 2 || p.mode == 4
    iL = 0;
end
if p.mode == 3
    iL = p.Iload_test*vb(1)/p.Em;           % resistive test load in phase with the busbar voltage
end
if p.mode ~= 0, isink = 0; end
if p.mode == 4, isink = 200; end
iL = p.sgn_load*iL;
isink = p.sgn_sink*isink;

% ---------------- measurement accumulation
for b = 1:2
    acc_i(b) = acc_i(b) + sum(ibs((b - 1)*Nb + 1:b*Nb));
end
acc_v = acc_v + vb; acc_V = acc_V + vdc; acc_n = acc_n + 1;
k = k + 1;
lg = [sx_hold; d_now(1); d_now(2); iref_hold(1); iref_hold(2); Pt; Qt; U_hold];
end
