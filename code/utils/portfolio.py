"""
Portfolio construction and evaluation.

Decile sorts, long-short portfolios, and portfolio-level metrics
for evaluating return prediction models.
"""
import numpy as np
import pandas as pd


def decile_sort(
    df: pd.DataFrame,
    signal_col: str,
    ret_col: str = 'RET',
    weight_col: str = 'me',
    n_quantiles: int = 10,
) -> pd.DataFrame:
    """
    Sort stocks into decile portfolios each month based on a signal.

    Parameters
    ----------
    df : stock-level panel with yyyymm, signal, returns, and weights
    signal_col : column containing the sorting signal (e.g., predicted return)
    ret_col : return column
    weight_col : weight column for value-weighting
    n_quantiles : number of portfolios (10 = deciles)

    Returns
    -------
    DataFrame with columns: yyyymm, decile, ret_vw, ret_ew, n_stocks
    """
    records = []

    for yyyymm, month_df in df.groupby('yyyymm'):
        valid = month_df[[signal_col, ret_col, weight_col]].dropna()
        if len(valid) < n_quantiles * 2:
            continue

        valid = valid.copy()
        valid['decile'] = pd.qcut(
            valid[signal_col], n_quantiles, labels=False, duplicates='drop'
        )

        for dec, g in valid.groupby('decile'):
            w = g[weight_col].values
            r = g[ret_col].values
            w_sum = w.sum()
            ret_vw = (r * w).sum() / w_sum if w_sum > 0 else r.mean()
            ret_ew = r.mean()
            records.append({
                'yyyymm': yyyymm,
                'decile': int(dec),
                'ret_vw': ret_vw,
                'ret_ew': ret_ew,
                'n_stocks': len(g),
            })

    return pd.DataFrame(records)


def long_short(
    decile_returns: pd.DataFrame,
    ret_col: str = 'ret_vw',
    n_quantiles: int = 10,
) -> pd.Series:
    """
    Compute long-short (top - bottom decile) returns.

    Parameters
    ----------
    decile_returns : output of decile_sort
    ret_col : which return column to use
    n_quantiles : number of quantiles used in sorting

    Returns
    -------
    Series of monthly long-short returns indexed by yyyymm
    """
    top = decile_returns[decile_returns['decile'] == n_quantiles - 1].set_index('yyyymm')[ret_col]
    bottom = decile_returns[decile_returns['decile'] == 0].set_index('yyyymm')[ret_col]
    ls = top - bottom
    ls.name = 'ls_return'
    return ls.dropna()


def portfolio_metrics(
    ls_returns: pd.Series | np.ndarray,
    rf: np.ndarray | None = None,
    y_train_mean: float = 0.0,
    gamma: float = 5.0,
) -> dict:
    """
    Compute portfolio-level evaluation metrics.

    Parameters
    ----------
    ls_returns : long-short portfolio returns
    rf : risk-free rate series (for excess return computation)
    y_train_mean : training mean for R²_OOS
    gamma : risk aversion for CER

    Returns
    -------
    dict with keys: mean, std, sharpe, cer, t_stat, n_months
    """
    r = np.asarray(ls_returns, dtype=float)

    mu = np.mean(r)
    sigma = np.std(r, ddof=1)
    n = len(r)

    sr = (mu / sigma * np.sqrt(12)) if sigma > 0 else 0.0
    cer = mu - (gamma / 2.0) * np.var(r, ddof=1)
    t_stat = (mu / (sigma / np.sqrt(n))) if sigma > 0 else 0.0

    # Annualize
    mean_ann = mu * 12
    std_ann = sigma * np.sqrt(12)

    return {
        'mean_monthly': float(mu),
        'mean_annual': float(mean_ann),
        'std_annual': float(std_ann),
        'sharpe': float(sr),
        'cer': float(cer * 12),  # annualized
        't_stat': float(t_stat),
        'n_months': int(n),
    }
