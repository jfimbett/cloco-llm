"""
Linear baseline models for return prediction.

Historical mean, OLS, Ridge, Lasso, Elastic Net — all with a common
fit/predict/tune interface for uniform treatment in the runner.
"""
import numpy as np
from sklearn.linear_model import Ridge, Lasso, ElasticNet, LinearRegression
from sklearn.preprocessing import StandardScaler


class HistoricalMean:
    """Predict the training-sample mean for all observations."""

    def __init__(self):
        self.mean_ = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], self.mean_)

    def tune(self, X, y, cv_splits, **kwargs):
        """No hyperparameters to tune."""
        self.fit(X, y)
        return {}


class OLSModel:
    """Pooled OLS on characteristics."""

    def __init__(self):
        self.model_ = LinearRegression()
        self.scaler_ = StandardScaler()

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        X_sc = self.scaler_.fit_transform(X)
        self.model_.fit(X_sc, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_sc = self.scaler_.transform(X)
        return self.model_.predict(X_sc)

    def tune(self, X, y, cv_splits, **kwargs):
        """No hyperparameters to tune."""
        self.fit(X, y)
        return {}


class RidgeModel:
    """Ridge regression with LOYO cross-validation for λ."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.model_ = None
        self.scaler_ = StandardScaler()

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        X_sc = self.scaler_.fit_transform(X)
        self.model_ = Ridge(alpha=self.alpha)
        self.model_.fit(X_sc, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_sc = self.scaler_.transform(X)
        return self.model_.predict(X_sc)

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        alpha_grid: np.ndarray | None = None,
        **kwargs,
    ) -> dict:
        """LOYO CV over alpha grid."""
        if alpha_grid is None:
            alpha_grid = np.logspace(-4, 4, 30)

        best_alpha = self.alpha
        best_mse = np.inf

        for alpha in alpha_grid:
            mse_folds = []
            for train_idx, val_idx in cv_splits:
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X[train_idx])
                X_val = scaler.transform(X[val_idx])
                model = Ridge(alpha=alpha)
                model.fit(X_tr, y[train_idx])
                pred = model.predict(X_val)
                mse_folds.append(np.mean((y[val_idx] - pred) ** 2))
            avg_mse = np.mean(mse_folds)
            if avg_mse < best_mse:
                best_mse = avg_mse
                best_alpha = alpha

        self.alpha = best_alpha
        self.fit(X, y)
        return {'alpha': best_alpha, 'cv_mse': best_mse}


class LassoModel:
    """Lasso regression with LOYO cross-validation for λ."""

    def __init__(self, alpha: float = 0.001):
        self.alpha = alpha
        self.model_ = None
        self.scaler_ = StandardScaler()

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        X_sc = self.scaler_.fit_transform(X)
        self.model_ = Lasso(alpha=self.alpha, max_iter=10000)
        self.model_.fit(X_sc, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_sc = self.scaler_.transform(X)
        return self.model_.predict(X_sc)

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        alpha_grid: np.ndarray | None = None,
        **kwargs,
    ) -> dict:
        if alpha_grid is None:
            alpha_grid = np.logspace(-6, 0, 30)

        best_alpha = self.alpha
        best_mse = np.inf

        for alpha in alpha_grid:
            mse_folds = []
            for train_idx, val_idx in cv_splits:
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X[train_idx])
                X_val = scaler.transform(X[val_idx])
                model = Lasso(alpha=alpha, max_iter=10000)
                model.fit(X_tr, y[train_idx])
                pred = model.predict(X_val)
                mse_folds.append(np.mean((y[val_idx] - pred) ** 2))
            avg_mse = np.mean(mse_folds)
            if avg_mse < best_mse:
                best_mse = avg_mse
                best_alpha = alpha

        self.alpha = best_alpha
        self.fit(X, y)
        return {'alpha': best_alpha, 'cv_mse': best_mse}


class ElasticNetModel:
    """Elastic Net with LOYO CV for (α, l1_ratio)."""

    def __init__(self, alpha: float = 0.001, l1_ratio: float = 0.5):
        self.alpha = alpha
        self.l1_ratio = l1_ratio
        self.model_ = None
        self.scaler_ = StandardScaler()

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        X_sc = self.scaler_.fit_transform(X)
        self.model_ = ElasticNet(
            alpha=self.alpha, l1_ratio=self.l1_ratio, max_iter=10000
        )
        self.model_.fit(X_sc, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_sc = self.scaler_.transform(X)
        return self.model_.predict(X_sc)

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        alpha_grid: np.ndarray | None = None,
        l1_grid: np.ndarray | None = None,
        **kwargs,
    ) -> dict:
        if alpha_grid is None:
            alpha_grid = np.logspace(-6, 0, 15)
        if l1_grid is None:
            l1_grid = np.array([0.1, 0.3, 0.5, 0.7, 0.9])

        best_alpha = self.alpha
        best_l1 = self.l1_ratio
        best_mse = np.inf

        for alpha in alpha_grid:
            for l1 in l1_grid:
                mse_folds = []
                for train_idx, val_idx in cv_splits:
                    scaler = StandardScaler()
                    X_tr = scaler.fit_transform(X[train_idx])
                    X_val = scaler.transform(X[val_idx])
                    model = ElasticNet(alpha=alpha, l1_ratio=l1, max_iter=10000)
                    model.fit(X_tr, y[train_idx])
                    pred = model.predict(X_val)
                    mse_folds.append(np.mean((y[val_idx] - pred) ** 2))
                avg_mse = np.mean(mse_folds)
                if avg_mse < best_mse:
                    best_mse = avg_mse
                    best_alpha = alpha
                    best_l1 = l1

        self.alpha = best_alpha
        self.l1_ratio = best_l1
        self.fit(X, y)
        return {'alpha': best_alpha, 'l1_ratio': best_l1, 'cv_mse': best_mse}
