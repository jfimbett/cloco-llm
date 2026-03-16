"""
Standard Kernel Ridge Regression (KRR).

This is the μ_j = 0 baseline — pure statistical regularization
without structural penalties. Must beat Ridge/Lasso to justify
the kernel approach.
"""
import numpy as np
from scipy.linalg import cho_factor, cho_solve

from code.utils.kernel import gaussian_rbf, median_heuristic


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

        # Solve (K + nλI) α = y
        A = K + n * self.lambda_stat * np.eye(n)
        c, low = cho_factor(A)
        self.alpha_ = cho_solve((c, low), y)

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

        for lam in lambda_grid:
            mse_folds = []
            for train_idx, val_idx in cv_splits:
                X_tr, y_tr = X[train_idx], y[train_idx]
                X_val, y_val = X[val_idx], y[val_idx]

                n_tr = X_tr.shape[0]
                K_tr = gaussian_rbf(X_tr, sigma=sigma)
                A = K_tr + n_tr * lam * np.eye(n_tr)

                try:
                    c, low = cho_factor(A)
                    alpha = cho_solve((c, low), y_tr)
                except np.linalg.LinAlgError:
                    mse_folds.append(np.inf)
                    continue

                K_val = gaussian_rbf(X_val, X_tr, sigma=sigma)
                pred = K_val @ alpha
                mse_folds.append(np.mean((y_val - pred) ** 2))

            avg_mse = np.mean(mse_folds)
            if avg_mse < best_mse:
                best_mse = avg_mse
                best_lam = lam

        self.lambda_stat = best_lam
        self.sigma = sigma
        self.fit(X, y)
        return {'lambda_stat': best_lam, 'sigma': sigma, 'cv_mse': best_mse}
