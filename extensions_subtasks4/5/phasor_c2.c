/* C re-implementation of rpc_sizing.network.solve (same fixed-point iteration, same global stopping rule
   max|U_new-U| < tol checked after each sweep), written for speed only.  Complex arithmetic in IEEE double. */
#include <complex.h>
#include <math.h>
#include <stdlib.h>

void solve_c(int n, const double complex *sa, const double complex *sb,
             const double complex *zTp, const double complex *Zsp, const double complex *E, int n_iter, double tol,
             double complex *ratio, double *vuf, double *uaabs, double *ubabs)
{
    double complex *U0 = malloc(n * sizeof(double complex)), *U1 = malloc(n * sizeof(double complex)),
                   *U2 = malloc(n * sizeof(double complex)), *Ia = calloc(n, sizeof(double complex)),
                   *Ib = calloc(n, sizeof(double complex));
    const double complex zT = *zTp, Zs = *Zsp;
    const double R3 = 1.0 / sqrt(3.0), SQ3 = sqrt(3.0);
    for (int i = 0; i < n; i++) { U0[i] = E[0]; U1[i] = E[1]; U2[i] = E[2]; }
    for (int it = 0; it < n_iter; it++) {
        double err = 0.0;
        for (int i = 0; i < n; i++) {
            double complex ua = (U1[i] - U2[i]) * R3 - zT * Ia[i];
            double complex ub = (2.0 * U0[i] - U1[i] - U2[i]) / 3.0 - zT * Ib[i];
            uaabs[i] = cabs(ua); ubabs[i] = cabs(ub);   /* terminal voltages of the last sweep (as returned by network.solve) */
            double complex Ian = conj(sa[i] / ua);
            double complex Ibn = conj(sb[i] / ub);
            double complex N0 = E[0] - Zs * (2.0 * Ibn);
            double complex N1 = E[1] - Zs * (SQ3 * Ian - Ibn);
            double complex N2 = E[2] - Zs * (-SQ3 * Ian - Ibn);
            double complex d0 = N0 - U0[i], d1 = N1 - U1[i], d2 = N2 - U2[i];
            double e0 = creal(d0)*creal(d0)+cimag(d0)*cimag(d0), e1 = creal(d1)*creal(d1)+cimag(d1)*cimag(d1), e2 = creal(d2)*creal(d2)+cimag(d2)*cimag(d2);
            if (e0 > err) err = e0; if (e1 > err) err = e1; if (e2 > err) err = e2;
            U0[i] = N0; U1[i] = N1; U2[i] = N2; Ia[i] = Ian; Ib[i] = Ibn;
        }
        if (err < tol * tol) break;   /* err is the squared max modulus */
    }
    double complex A = cexp(I * 2.0 * M_PI / 3.0), A2 = A * A;
    for (int i = 0; i < n; i++) {
        double complex V1 = (U0[i] + A * U1[i] + A2 * U2[i]) / 3.0;
        double complex V2 = (U0[i] + A2 * U1[i] + A * U2[i]) / 3.0;
        ratio[i] = V2 / V1;
        vuf[i] = cabs(V2) / cabs(V1) * 100.0;
    }
    free(U0); free(U1); free(U2); free(Ia); free(Ib);
}
