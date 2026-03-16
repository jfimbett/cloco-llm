"""
Cross-validation utilities for KRR estimation.

LOYO (leave-one-year-out) temporal CV splits,
random search over grouped penalty parameters,
and grid search for baselines.
"""
import numpy as np
from typing import Callable


def loyo_cv_splits(
    yyyymm: np.ndarray,
    min_train: int = 240,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Leave-one-year-out temporal CV splits.

    For each year in the data (after min_train months), hold out
    that year's observations and train on all prior months.

    Parameters
    ----------
    yyyymm : array of yyyymm values (e.g., 196307, 202312)
    min_train : minimum number of training months

    Returns
    -------
    list of (train_indices, val_indices) tuples
    """
    months = np.sort(np.unique(yyyymm))
    if len(months) < min_train + 12:
        # Not enough data — use 5-fold temporal splits
        n = len(months)
        fold_size = max(12, n // 5)
        splits = []
        for i in range(0, n - fold_size, fold_size):
            train_months = months[:i + fold_size]
            val_months = months[i + fold_size:i + 2 * fold_size]
            if len(val_months) == 0:
                continue
            train_idx = np.where(np.isin(yyyymm, train_months))[0]
            val_idx = np.where(np.isin(yyyymm, val_months))[0]
            if len(train_idx) > 0 and len(val_idx) > 0:
                splits.append((train_idx, val_idx))
        return splits

    # Standard LOYO: leave out each year, train on all prior
    years = np.sort(np.unique(yyyymm // 100))

    splits = []
    for year in years:
        year_months = months[(months // 100) == year]
        prior_months = months[months < year_months[0]]

        if len(prior_months) < min_train:
            continue

        train_idx = np.where(np.isin(yyyymm, prior_months))[0]
        val_idx = np.where(np.isin(yyyymm, year_months))[0]

        if len(train_idx) > 0 and len(val_idx) > 0:
            splits.append((train_idx, val_idx))

    return splits


def random_search_cv(
    fit_predict_fn: Callable,
    X: np.ndarray,
    y: np.ndarray,
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
    param_space: dict[str, tuple[float, float]],
    n_draws: int = 200,
    seed: int = 42,
) -> tuple[dict, float]:
    """
    Random search cross-validation.

    Parameters
    ----------
    fit_predict_fn : callable(params, train_idx, val_idx) -> predictions
    X : feature matrix
    y : targets
    cv_splits : list of (train_idx, val_idx)
    param_space : dict of parameter_name → (lo, hi) for Uniform sampling
    n_draws : number of random parameter draws
    seed : random seed

    Returns
    -------
    (best_params, best_mse) tuple
    """
    rng = np.random.RandomState(seed)
    best_params = None
    best_mse = np.inf

    for draw in range(n_draws):
        # Sample parameters
        params = {}
        for name, (lo, hi) in param_space.items():
            params[name] = rng.uniform(lo, hi)

        # Evaluate across CV folds
        mse_folds = []
        try:
            for train_idx, val_idx in cv_splits:
                pred = fit_predict_fn(params, train_idx, val_idx)
                mse = np.mean((y[val_idx] - pred) ** 2)
                mse_folds.append(mse)
        except Exception:
            continue

        avg_mse = np.mean(mse_folds)
        if avg_mse < best_mse:
            best_mse = avg_mse
            best_params = params.copy()

        if (draw + 1) % 50 == 0:
            print(f"  CV draw {draw+1}/{n_draws}, best MSE so far: {best_mse:.6f}")

    return best_params, best_mse


def grid_search_cv(
    model,
    X: np.ndarray,
    y: np.ndarray,
    param_grid: dict[str, np.ndarray],
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[dict, float]:
    """
    Grid search cross-validation for baseline models.

    Parameters
    ----------
    model : model with fit/predict interface
    X, y : training data
    param_grid : dict of parameter_name → array of values
    cv_splits : list of (train_idx, val_idx)

    Returns
    -------
    (best_params, best_mse) tuple
    """
    from itertools import product

    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())

    best_params = {}
    best_mse = np.inf

    for combo in product(*param_values):
        params = dict(zip(param_names, combo))

        mse_folds = []
        for train_idx, val_idx in cv_splits:
            # Set parameters
            for name, val in params.items():
                setattr(model, name, val)
            model.fit(X[train_idx], y[train_idx])
            pred = model.predict(X[val_idx])
            mse_folds.append(np.mean((y[val_idx] - pred) ** 2))

        avg_mse = np.mean(mse_folds)
        if avg_mse < best_mse:
            best_mse = avg_mse
            best_params = params.copy()

    # Fit final model with best params
    for name, val in best_params.items():
        setattr(model, name, val)
    model.fit(X, y)

    return best_params, best_mse
