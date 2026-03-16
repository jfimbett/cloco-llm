"""
Kernel functions for KRR estimation.

Provides Gaussian RBF kernel, median heuristic bandwidth selection,
and Nyström low-rank approximation.
"""
import numpy as np
from scipy.spatial.distance import pdist, cdist


def median_heuristic(X: np.ndarray, subsample: int = 5000) -> float:
    """
    Compute kernel bandwidth via median heuristic.

    Parameters
    ----------
    X : (n, p) feature matrix
    subsample : max points to use (for speed)

    Returns
    -------
    sigma : median pairwise Euclidean distance
    """
    if X.shape[0] > subsample:
        idx = np.random.choice(X.shape[0], subsample, replace=False)
        X = X[idx]
    dists = pdist(X, metric='euclidean')
    return float(np.median(dists))


def gaussian_rbf(
    X: np.ndarray,
    Y: np.ndarray | None = None,
    sigma: float | None = None,
) -> np.ndarray:
    """
    Compute Gaussian RBF kernel matrix.

    K(x, y) = exp(-||x - y||² / (2σ²))

    Parameters
    ----------
    X : (n, p) feature matrix
    Y : (m, p) feature matrix (default: X)
    sigma : bandwidth (default: median heuristic on X)

    Returns
    -------
    K : (n, m) kernel matrix
    """
    if sigma is None:
        sigma = median_heuristic(X)
    if sigma <= 0:
        sigma = 1.0

    gamma = 1.0 / (2.0 * sigma ** 2)

    if Y is None:
        sq_dists = cdist(X, X, metric='sqeuclidean')
    else:
        sq_dists = cdist(X, Y, metric='sqeuclidean')

    return np.exp(-gamma * sq_dists)


def nystrom_approx(
    X: np.ndarray,
    m: int = 500,
    sigma: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Nyström low-rank approximation of the kernel matrix.

    K ≈ Z W Z^T where Z = K_{n,m}, W = K_{m,m}^{-1}

    Parameters
    ----------
    X : (n, p) feature matrix
    m : number of landmark points
    sigma : kernel bandwidth

    Returns
    -------
    Z : (n, m) feature map
    W : (m, m) pseudo-inverse of landmark kernel
    """
    n = X.shape[0]
    m = min(m, n)

    # Select landmarks uniformly at random
    idx = np.random.choice(n, m, replace=False)
    landmarks = X[idx]

    if sigma is None:
        sigma = median_heuristic(X)

    # Kernel between all points and landmarks
    K_nm = gaussian_rbf(X, landmarks, sigma=sigma)
    # Kernel among landmarks
    K_mm = gaussian_rbf(landmarks, sigma=sigma)

    # Regularized pseudo-inverse via eigendecomposition
    eigvals, eigvecs = np.linalg.eigh(K_mm)
    # Clip small eigenvalues for numerical stability
    eigvals = np.maximum(eigvals, 1e-10)
    W = eigvecs @ np.diag(1.0 / eigvals) @ eigvecs.T

    return K_nm, W
