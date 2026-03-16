"""
Theory-Informed Kernel Ridge Regression (Theory-KRR).

Extends standard KRR with structural penalty terms derived from
economic theory. The objective is:

    min_f  ||y - f||² + n·λ·||f||²_H + Σ_j μ_j · C_j(f)

where C_j are structural restrictions from asset pricing theory.

For quadratic penalties (Types A/B): solved via augmented linear system.
For non-quadratic penalties (Type D): L-BFGS with quadratic warm start.
"""
import numpy as np
from scipy.optimize import minimize

from code.utils.kernel import gaussian_rbf, median_heuristic, _check_gpu
from code.estimation.krr import _cholesky_solve
from code.restrictions.base import Restriction


# --- Default group mapping ---
DEFAULT_GROUPS = {
    'consumption': 0,
    'production': 1,
    'intermediary': 2,
    'information': 3,
    'demand': 4,
    'volatility': 5,
    'behavioral': 6,
    'macro': 7,
}


class TheoryKRR:
    """
    Theory-Informed KRR with structural penalties.

    Parameters
    ----------
    restrictions : list of Restriction objects
    sigma : kernel bandwidth (None = median heuristic)
    groups : dict mapping family name → group index (for grouped μ_j)
    """

    def __init__(
        self,
        restrictions: list[Restriction],
        sigma: float | None = None,
        groups: dict[str, int] | None = None,
    ):
        self.restrictions = restrictions
        self.sigma = sigma
        self.groups = groups if groups is not None else DEFAULT_GROUPS

        # Fitted attributes
        self.alpha_ = None
        self.X_train_ = None
        self.sigma_used_ = None
        self.mu_values_ = None
        self.lambda_stat_ = None

    def _group_restrictions(self) -> dict[int, list[Restriction]]:
        """Group restrictions by family."""
        grouped = {}
        for r in self.restrictions:
            g = self.groups.get(r.family, 0)
            grouped.setdefault(g, []).append(r)
        return grouped

    def _active_restrictions(self, mu_groups: dict[int, float]) -> list[tuple[Restriction, float]]:
        """Return only restrictions whose group has mu > 0, with their mu values."""
        active = []
        for r in self.restrictions:
            g_idx = self.groups.get(r.family, 0)
            mu_g = mu_groups.get(g_idx, 0.0)
            if mu_g != 0:
                active.append((r, mu_g))
        return active

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        lambda_stat: float = 1e-3,
        mu_groups: dict[int, float] | None = None,
        data_context: dict | None = None,
        K_precomputed: np.ndarray | None = None,
    ):
        """
        Fit Theory-Informed KRR.

        Parameters
        ----------
        X : (n, p) training features
        y : (n,) training targets
        lambda_stat : statistical regularization
        mu_groups : dict mapping group index → μ_g multiplier
        data_context : dict of data arrays aligned with X
        K_precomputed : optional pre-computed kernel matrix (avoids recomputation)
        """
        self.lambda_stat_ = lambda_stat
        n = X.shape[0]
        self.X_train_ = X.copy()
        self.sigma_used_ = self.sigma if self.sigma else median_heuristic(X)

        if K_precomputed is not None:
            K = K_precomputed
        else:
            K = gaussian_rbf(X, sigma=self.sigma_used_)

        if mu_groups is None:
            mu_groups = {i: 0.0 for i in range(8)}
        self.mu_values_ = mu_groups

        if data_context is None:
            data_context = {}

        # Use L-BFGS with unrestricted KRR as warm start.
        alpha_krr_warm = _cholesky_solve(K, y, n, lambda_stat)
        self.alpha_ = self._fit_lbfgs(
            K, y, n, lambda_stat, mu_groups, data_context, alpha_krr_warm
        )

        return self

    def _fit_lbfgs(
        self,
        K: np.ndarray,
        y: np.ndarray,
        n: int,
        lambda_stat: float,
        mu_groups: dict[int, float],
        data_context: dict,
        alpha_init: np.ndarray,
    ) -> np.ndarray:
        """L-BFGS optimization for non-quadratic penalties."""

        # Pre-filter to active restrictions only (skip zero-mu)
        active = self._active_restrictions(mu_groups)

        # If no active restrictions, warm start IS the solution
        if not active:
            return alpha_init

        # Pre-compute K @ alpha products that are reused
        # Cache K as contiguous array for fast matmul
        K_c = np.ascontiguousarray(K)

        def objective(alpha):
            f_hat = K_c @ alpha
            # Data fit: ||y - Kα||²
            residual = y - f_hat
            loss = np.dot(residual, residual)
            # RKHS penalty: nλ α^T K α
            loss += n * self.lambda_stat_ * np.dot(alpha, K_c @ alpha)
            # Structural penalties (active only)
            for r, mu_g in active:
                try:
                    loss += mu_g * r.penalty(f_hat, self.X_train_, data_context)
                except Exception:
                    continue
            return loss

        def gradient(alpha):
            f_hat = K_c @ alpha
            K_alpha = K_c @ alpha
            # Data fit gradient: -2K^T(y - Kα)
            residual = y - f_hat
            grad = -2.0 * K_c @ residual
            # RKHS penalty gradient: 2nλKα
            grad += 2.0 * n * self.lambda_stat_ * K_alpha
            # Structural penalty gradients (active only)
            for r, mu_g in active:
                try:
                    g_r = r.penalty_gradient(f_hat, self.X_train_, data_context)
                    grad += mu_g * K_c @ g_r
                except Exception:
                    continue
            return grad

        result = minimize(
            objective,
            alpha_init,
            jac=gradient,
            method='L-BFGS-B',
            options={'maxiter': 500, 'ftol': 1e-10, 'gtol': 1e-6},
        )

        return result.x

    def predict(self, X_new: np.ndarray) -> np.ndarray:
        """Predict on new data."""
        K_new = gaussian_rbf(X_new, self.X_train_, sigma=self.sigma_used_)
        return K_new @ self.alpha_

    def get_multiplier_values(self) -> dict:
        """Return the effective μ_j values for each restriction."""
        if self.mu_values_ is None:
            return {}
        result = {}
        for r in self.restrictions:
            g_idx = self.groups.get(r.family, 0)
            mu_g = self.mu_values_.get(g_idx, 0.0)
            result[r.name] = mu_g
        return result

    def get_penalty_values(
        self,
        X: np.ndarray | None = None,
        data_context: dict | None = None,
    ) -> dict:
        """Evaluate each penalty at the current fit."""
        if self.alpha_ is None:
            return {}
        if X is None:
            X = self.X_train_
        if data_context is None:
            data_context = {}
        f_hat = gaussian_rbf(X, self.X_train_, sigma=self.sigma_used_) @ self.alpha_
        result = {}
        for r in self.restrictions:
            try:
                result[r.name] = r.penalty(f_hat, X, data_context)
            except Exception:
                result[r.name] = np.nan
        return result

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        data_context: dict | None = None,
        n_draws: int = 200,
        **kwargs,
    ) -> dict:
        """Random search CV over λ_stat and grouped μ parameters."""
        from code.estimation.cv import random_search_cv

        n_groups = len(set(self.groups.values()))
        param_space = {
            'log_lambda': (-6, 2),
        }
        for g in range(n_groups):
            param_space[f'log_mu_{g}'] = (-4, 2)

        def fit_and_predict(params, train_idx, val_idx):
            lambda_stat = 10.0 ** params['log_lambda']
            mu_groups = {}
            for g in range(n_groups):
                mu_groups[g] = 10.0 ** params.get(f'log_mu_{g}', -4)

            X_tr, y_tr = X[train_idx], y[train_idx]
            X_val = X[val_idx]

            # Build data context for training subset
            dc_tr = {}
            if data_context:
                for k, v in data_context.items():
                    if isinstance(v, np.ndarray) and len(v) == len(y):
                        dc_tr[k] = v[train_idx]

            model = TheoryKRR(
                restrictions=self.restrictions,
                sigma=self.sigma,
                groups=self.groups,
            )
            model.fit(X_tr, y_tr, lambda_stat, mu_groups, dc_tr)
            return model.predict(X_val)

        best_params, best_mse = random_search_cv(
            fit_and_predict, X, y, cv_splits, param_space, n_draws
        )

        # Fit final model with best params
        self.lambda_stat_ = 10.0 ** best_params['log_lambda']
        best_mu = {}
        for g in range(n_groups):
            best_mu[g] = 10.0 ** best_params.get(f'log_mu_{g}', -4)

        self.fit(X, y, self.lambda_stat_, best_mu, data_context)
        return {'params': best_params, 'cv_mse': best_mse}
