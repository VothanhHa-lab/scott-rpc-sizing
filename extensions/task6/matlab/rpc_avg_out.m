function out = rpc_avg_out(X, PL, QL, p)
%RPC_AVG_OUT  Outputs of the averaged RPC model: [Vdc (V), Ia (pu), Ib (pu)].
%   X is N x 8 (states of rpc_avg_rhs), PL and QL are N x 1 (MW, Mvar).
%   Ia, Ib: leg apparent power divided by busbar voltage (pu) and rating C.
W = X(:,1); Pa = X(:,2); Qa = X(:,3); Pb = X(:,4); Qb = X(:,5);
Vdc = sqrt(max(2*W*1e6/p.Cdc_F, 0));
U = 1 - (p.r_pu_per_MVA*(PL(:) - Pa) + p.x_pu_per_MVA*(QL(:) - Qa));
Ia = hypot(Pa, Qa)./max(U, 1e-3)/max(p.C, 1e-6);
Ib = hypot(Pb, Qb)/max(p.C, 1e-6);            % beta busbar lightly loaded: U = 1
out = [Vdc, Ia, Ib];
end
