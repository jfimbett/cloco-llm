"""
Ensemble baseline: Random Forest for return prediction.
"""
import numpy as np
from sklearn.ensemble import RandomForestRegressor


class RandomForestModel:
    """Random Forest regressor (GKX-style configuration)."""

    def __init__(
        self,
        n_estimators: int = 300,
        max_features: float | str = 'auto',
        min_samples_leaf: int = 5,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_features = max_features
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.model_ = None

    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        max_feat = self.max_features
        if max_feat == 'auto':
            max_feat = max(1, X.shape[1] // 3)
        self.model_ = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_features=max_feat,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model_.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model_.predict(X)

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        **kwargs,
    ) -> dict:
        """Tune max_features and min_samples_leaf via LOYO CV."""
        p = X.shape[1]
        mf_grid = [max(1, p // 6), max(1, p // 3), max(1, p // 2)]
        msl_grid = [5, 10, 25]

        best_mf = max(1, p // 3)
        best_msl = 5
        best_mse = np.inf

        for mf in mf_grid:
            for msl in msl_grid:
                mse_folds = []
                for train_idx, val_idx in cv_splits:
                    model = RandomForestRegressor(
                        n_estimators=self.n_estimators,
                        max_features=mf,
                        min_samples_leaf=msl,
                        random_state=self.random_state,
                        n_jobs=-1,
                    )
                    model.fit(X[train_idx], y[train_idx])
                    pred = model.predict(X[val_idx])
                    mse_folds.append(np.mean((y[val_idx] - pred) ** 2))
                avg_mse = np.mean(mse_folds)
                if avg_mse < best_mse:
                    best_mse = avg_mse
                    best_mf = mf
                    best_msl = msl

        self.max_features = best_mf
        self.min_samples_leaf = best_msl
        self.fit(X, y)
        return {'max_features': best_mf, 'min_samples_leaf': best_msl, 'cv_mse': best_mse}
