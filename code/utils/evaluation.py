"""
Evaluation metrics for return prediction models.

Implements R²_OOS, Sharpe ratio, certainty equivalent return,
Diebold-Mariano test, and block bootstrap inference.
"""
import numpy as np
from scipy import stats


def r2_oos(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train_mean: float,
) -> float:
    """
    Campbell-Thompson out-of-sample R².

    R²_OOS = 1 - Σ(y - ŷ)² / Σ(y - ȳ_train)²

    Parameters
    ----------
    y_true : realized returns
    y_pred : predicted returns
    y_train_mean : historical (training) mean return
    """
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_train_mean) ** 2)
    if ss_tot == 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def sharpe_ratio(
    returns: np.ndarray,
    annualize: bool = True,
) -> float:
    """
    Annualized Sharpe ratio (assumes excess returns).

    Parameters
    ----------
    returns : array of excess returns (already in excess of rf)
    annualize : multiply by sqrt(12) for monthly data
    """
    mu = np.mean(returns)
    sigma = np.std(returns, ddof=1)
    if sigma == 0:
        return 0.0
    sr = mu / sigma
    if annualize:
        sr *= np.sqrt(12)
    return float(sr)


def certainty_equivalent(
    returns: np.ndarray,
    gamma: float = 5.0,
) -> float:
    """
    Certainty equivalent return for a mean-variance investor.

    CER = μ - (γ/2) σ²

    Parameters
    ----------
    returns : array of excess returns
    gamma : risk aversion coefficient
    """
    mu = np.mean(returns)
    var = np.var(returns, ddof=1)
    return float(mu - (gamma / 2.0) * var)


def _newey_west_var(x: np.ndarray, n_lags: int) -> float:
    """Newey-West HAC variance estimator for a univariate series."""
    n = len(x)
    x_dm = x - np.mean(x)
    # Variance term
    gamma_0 = np.dot(x_dm, x_dm) / n
    # Autocovariance terms with Bartlett weights
    nw_sum = 0.0
    for j in range(1, n_lags + 1):
        weight = 1.0 - j / (n_lags + 1.0)
        gamma_j = np.dot(x_dm[j:], x_dm[:-j]) / n
        nw_sum += 2.0 * weight * gamma_j
    return (gamma_0 + nw_sum) / n


def diebold_mariano(
    e1: np.ndarray,
    e2: np.ndarray,
    h: int = 1,
    nw_lags: int = 6,
) -> tuple[float, float]:
    """
    Diebold-Mariano test for equal predictive accuracy.

    H0: E[d_t] = 0  where d_t = e1_t² - e2_t²

    Parameters
    ----------
    e1 : forecast errors from model 1
    e2 : forecast errors from model 2
    h : forecast horizon
    nw_lags : number of Newey-West lags for HAC

    Returns
    -------
    (statistic, p_value) : two-sided test
    """
    d = e1 ** 2 - e2 ** 2
    d_bar = np.mean(d)
    var_d = _newey_west_var(d, nw_lags)

    if var_d <= 0:
        return 0.0, 1.0

    dm_stat = d_bar / np.sqrt(var_d)
    p_value = 2.0 * (1.0 - stats.norm.cdf(np.abs(dm_stat)))
    return float(dm_stat), float(p_value)


def block_bootstrap_sr(
    returns: np.ndarray,
    n_boot: int = 10000,
    block_size: int = 12,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """
    Block bootstrap confidence interval for Sharpe ratio.

    Parameters
    ----------
    returns : array of excess returns
    n_boot : number of bootstrap replications
    block_size : block length (12 for monthly data)
    alpha : significance level (0.05 for 95% CI)

    Returns
    -------
    (ci_lo, ci_hi) : confidence interval bounds
    """
    n = len(returns)
    n_blocks = int(np.ceil(n / block_size))
    sr_boot = np.empty(n_boot)

    for b in range(n_boot):
        # Sample block start indices
        starts = np.random.randint(0, n - block_size + 1, size=n_blocks)
        # Concatenate blocks
        idx = np.concatenate([np.arange(s, s + block_size) for s in starts])[:n]
        boot_ret = returns[idx]
        sr_boot[b] = sharpe_ratio(boot_ret, annualize=True)

    ci_lo = float(np.percentile(sr_boot, 100 * alpha / 2))
    ci_hi = float(np.percentile(sr_boot, 100 * (1 - alpha / 2)))
    return ci_lo, ci_hi
