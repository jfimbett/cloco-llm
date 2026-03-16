"""
Standard Kernel Ridge Regression (KRR).

This is the μ_j = 0 baseline — pure statistical regularization
without structural penalties. Must beat Ridge/Lasso to justify
the kernel approach.
"""
import numpy as np
from scipy.linalg import cho_factor, cho_solve

from code.utils.kernel import gaussian_rbf, median_heuristic, _check_gpu


def _cholesky_solve(K: np.ndarray, y: np.ndarray, n: int, lambda_stat: float) -> np.ndarray:
    """Solve (K + nλI)α = y via Cholesky, using GPU if available."""
    if _check_gpu():
        import torch
        device = 'cuda'
        K_gpu = torch.as_tensor(K, dtype=torch.float64, device=device)
        A_gpu = K_gpu + n * lambda_stat * torch.eye(n, device=device, dtype=torch.float64)
        L = torch.linalg.cholesky(A_gpu)
        y_gpu = torch.as_tensor(y, dtype=torch.float64, device=device).unsqueeze(1)
        alpha = torch.cholesky_solve(y_gpu, L).squeeze(1)
        return alpha.cpu().numpy()

    A = K + n * lambda_stat * np.eye(n)
    c, low = cho_factor(A)
    return cho_solve((c, low), y)


class StandardKRR:
    """
    Standard KRR: f(x) = k(x, X)^T α, where α = (K + nλI)^{-1} y.

    Parameters
    ----------
    sigma : kernel bandwidth (None = median heuristic)
    lambda_stat : ridge penalty
    """

    def __init__(self, sigma: float | None = None, lambda_stat: float = 1e-3):
        self.sigma = sigma
        self.lambda_stat = lambda_stat
        self.alpha_ = None
        self.X_train_ = None
        self.sigma_used_ = None

    def fit(self, X: np.ndarray, y: np.ndarray, lambda_stat: float | None = None, **kwargs):
        """
        Fit KRR via Cholesky factorization.

        Parameters
        ----------
        X : (n, p) training features
        y : (n,) training targets
        lambda_stat : override penalty (if None, use self.lambda_stat)
        """
        if lambda_stat is not None:
            self.lambda_stat = lambda_stat

        n = X.shape[0]
        self.X_train_ = X.copy()
        self.sigma_used_ = self.sigma if self.sigma else median_heuristic(X)

        K = gaussian_rbf(X, sigma=self.sigma_used_)
        self.alpha_ = _cholesky_solve(K, y, n, self.lambda_stat)

        return self

    def predict(self, X_new: np.ndarray) -> np.ndarray:
        """Predict on new data."""
        K_new = gaussian_rbf(X_new, self.X_train_, sigma=self.sigma_used_)
        return K_new @ self.alpha_

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        lambda_grid: np.ndarray | None = None,
        **kwargs,
    ) -> dict:
        """
        LOYO cross-validation over λ_stat.

        Parameters
        ----------
        X, y : full training data
        cv_splits : list of (train_idx, val_idx) tuples
        lambda_grid : grid of lambda values
        """
        if lambda_grid is None:
            lambda_grid = np.logspace(-6, 2, 30)

        best_lam = self.lambda_stat
        best_mse = np.inf

        # Fix sigma on full training set
        sigma = self.sigma if self.sigma else median_heuristic(X)

        # Pre-compute full kernel matrix and slice per fold
        K_full = gaussian_rbf(X, sigma=sigma)

        for lam in lambda_grid:
            mse_folds = []
            for train_idx, val_idx in cv_splits:
                K_tr = K_full[np.ix_(train_idx, train_idx)]
                y_tr = y[train_idx]
                n_tr = len(train_idx)

                try:
                    alpha = _cholesky_solve(K_tr, y_tr, n_tr, lam)
                except (np.linalg.LinAlgError, Exception):
                    mse_folds.append(np.inf)
                    continue

                K_val = K_full[np.ix_(val_idx, train_idx)]
                pred = K_val @ alpha
                mse_folds.append(np.mean((y[val_idx] - pred) ** 2))

            avg_mse = np.mean(mse_folds)
            if avg_mse < best_mse:
                best_mse = avg_mse
                best_lam = lam

        self.lambda_stat = best_lam
        self.sigma = sigma
        self.fit(X, y)
        return {'lambda_stat': best_lam, 'sigma': sigma, 'cv_mse': best_mse}
