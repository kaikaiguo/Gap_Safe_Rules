# Author: Eugene Ndiaye
#         Olivier Fercoq
#         Alexandre Gramfort
#         Joseph Salmon
# GAP Safe Screening Rules for Sparse-Group Lasso.
# http://arxiv.org/abs/1602.06225
# firstname.lastname@telecom-paristech.fr

import numpy as np
from scipy.linalg import toeplitz
from sklearn.utils import check_random_state


def vect_ST(u, x):
    """
        Vectorial soft-thresholding at level u.

    """
    return np.sign(x) * np.maximum(np.abs(x) - u, 0.)


def generate_data(n_samples, n_features, size_groups, rho=0.5,
                  random_state=24):
    """ Data generation process with Toplitz like correlated features:
        this correspond to the synthetic dataset used in our paper
        "GAP Safe Screening Rules for Sparse-Group Lasso".

    """

    rng = check_random_state(random_state)
    n_groups = len(size_groups)
    g_start = np.cumsum(size_groups, dtype=np.intc) - size_groups[0]

    # 10% of groups are actives
    gamma1 = int(np.ceil(n_groups * 0.1))
    selected_groups = rng.random_integers(0, n_groups - 1, gamma1)
    true_beta = np.zeros(n_features)

    for i in selected_groups:

        begin = g_start[i]
        end = g_start[i] + size_groups[i]
        # 10% of features are actives
        gamma2 = int(np.ceil(size_groups[i] * 0.1))
        selected_features = rng.random_integers(begin, end - 1, gamma2)

        ns = len(selected_features)
        s = 2 * rng.rand(ns) - 1
        u = rng.rand(ns)
        true_beta[selected_features] = np.sign(s) * (10 * u + (1 - u) * 0.5)

    vect = rho ** np.arange(n_features)
    covar = toeplitz(vect, vect)

    X = rng.multivariate_normal(np.zeros(n_features), covar, n_samples)
    y = np.dot(X, true_beta) + 0.01 * rng.normal(0, 1, n_samples)

    return X, y


def epsilon_norm(x, alpha, R):
    """
        Compute the unique positive solution in z of the equation
        norm(ST(x, alpha * z), 2) = alpha * R. The epsilon-norm correspond to
        the case alpha = 1 - epsilon and R = epsilon.
        See our paper "GAP Safe Screening Rules for Sparse-Group Lasso".

    """
    if alpha == 0 and R != 0:
            return np.linalg.norm(x, ord=2) / R

    if R == 0:  # j0 = 0 iif R = 0 iif alpha = 1 in practice
        return np.linalg.norm(x, ord=np.inf) / alpha

    zx = np.abs(x)
    norm_inf = np.linalg.norm(x, ord=np.inf)
    I_inf = np.where(zx > alpha * (norm_inf) / (alpha + R))[0]
    n_inf = len(I_inf)
    zx = np.sort(zx[I_inf])[::-1]

    if norm_inf == 0:
        return 0

    if n_inf == 1:
        return zx[0]

    R2 = R ** 2
    alpha2 = alpha ** 2
    R2onalpha2 = R2 / alpha2
    a_k = S = S2 = 0

    for k in range(n_inf - 1):

        S += zx[k]
        S2 += zx[k] ** 2
        b_k = S2 / (zx[k + 1] ** 2) - 2 * S / zx[k + 1] + k + 1

        if a_k <= R2onalpha2 and R2onalpha2 < b_k:
            j0 = k + 1
            break
        a_k = b_k
    else:
        j0 = n_inf
        S += zx[n_inf - 1]
        S2 += zx[n_inf - 1] ** 2

    alpha_S = alpha * S
    j0alpha2_R2 = j0 * alpha2 - R2

    if (j0alpha2_R2 == 0):
        return S2 / (2 * alpha_S)

    delta = alpha_S ** 2 - S2 * j0alpha2_R2

    return (alpha_S - np.sqrt(delta)) / j0alpha2_R2


def precompute_norm(X, y, size_groups, g_start):
    """
        Precomputation of the norm and group's norm used in the algorithm.

    """
    nrm2_y = np.linalg.norm(y, ord=2) ** 2
    n, p = X.shape
    n_groups = len(size_groups)

    norm_X = np.linalg.norm(X, axis=0)
    norm_X_g = [np.linalg.norm(X[:, g_start[i]:g_start[i] + size_groups[i]])
                for i in range(n_groups)]

    return norm_X, np.array(norm_X_g), nrm2_y



def build_lambdas(X, y, omega, size_groups, g_start, n_lambdas=100, delta=3,
                  tau=0.5):
    """
        Compute a list of regularization parameters which decrease
        geometrically
    """
    eps_g = (1. - tau) * omega / (tau + (1. - tau) * omega)
    n_groups = len(size_groups)

    nrm = [epsilon_norm(
        np.dot(X[:, g_start[i]:g_start[i] + size_groups[i]].T, y),
        1. - eps_g[i], eps_g[i]) for i in range(n_groups)]

    nrm = np.array(nrm) / (tau + (1. - tau) * omega)
    imax = np.argmax(nrm)
    lambda_max = nrm[imax]

    lambdas = lambda_max * \
        10 ** (-delta * np.arange(n_lambdas) / (n_lambdas - 1.))

    return lambdas, imax
