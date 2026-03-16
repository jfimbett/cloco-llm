"""
Data loading and panel management for Theory-Informed KRR.

Loads the monthly stock panel, identifies characteristic/macro columns,
produces expanding-window train/test splits, and builds managed portfolios.
"""
import numpy as np
import pandas as pd
from pathlib import Path

from code.config import TEST_MODE, TEST_MAX_STOCKS_PER_MONTH

# --- Identifier and return columns (not characteristics, not macro) ---
_ID_COLS = ['permno', 'yyyymm', 'date', 'gvkey', 'sic']
_RETURN_COLS = ['RET', 'RETX']
_PRICE_COLS = ['PRC', 'SHROUT', 'SHRCD', 'EXCHCD', 'me', 'price_char', 'size_char']

# Macro / time-series columns (constant within a month across stocks)
_MACRO_COLS = [
    'mktrf', 'smb', 'hml', 'rmw', 'cma', 'rf', 'mom',
    'tb3ms', 'term_spread', 'default_spread', 'cpiaucsl', 'indpro', 'unrate',
    'vix', 'ebp', 'sentiment', 'd12', 'e12', 'bm_wg', 'tbl', 'ntis', 'infl',
    'svar', 'cons_growth', 'hkm_capital_ratio', 'hkm_risk_factor', 'cay',
    'realized_var',
]

_NON_CHAR_COLS = set(_ID_COLS + _RETURN_COLS + _PRICE_COLS + _MACRO_COLS)


def load_panel(path: str = 'data/processed/panel_monthly.parquet') -> pd.DataFrame:
    """Load the monthly stock panel from parquet.

    When TEST_MODE is active, subsample to TEST_MAX_STOCKS_PER_MONTH random
    stocks per month for fast iteration.
    """
    df = pd.read_parquet(path)
    if TEST_MODE:
        n = TEST_MAX_STOCKS_PER_MONTH
        print(f"[TEST_MODE] Subsampling to {n} stocks per month")
        df = (
            df.groupby('yyyymm', group_keys=False)
            .apply(lambda g: g.sample(n=min(len(g), n), random_state=42))
        )
        df = df.reset_index(drop=True)
    return df


def get_characteristic_cols(df: pd.DataFrame) -> list[str]:
    """Return the list of cross-sectional characteristic columns (ranked, ~0.5 mean)."""
    return [c for c in df.columns if c not in _NON_CHAR_COLS]


def get_macro_cols(df: pd.DataFrame) -> list[str]:
    """Return macro/time-series columns present in the dataframe."""
    return [c for c in _MACRO_COLS if c in df.columns]


def expanding_window_splits(
    df: pd.DataFrame,
    min_train: int = 240,
    retrain_freq: int = 12,
    start_oos: int | None = None,
    end_oos: int | None = None,
):
    """
    Yield (train_df, test_df) tuples with expanding window, annual rebalancing.

    Parameters
    ----------
    df : DataFrame with 'yyyymm' column
    min_train : minimum number of training months
    retrain_freq : retrain every N months (12 = annual)
    start_oos : first OOS yyyymm (default: min_train months after first date)
    end_oos : last OOS yyyymm (default: last date in panel)
    """
    months = np.sort(df['yyyymm'].unique())

    if start_oos is None:
        start_oos = months[min_train]
    if end_oos is None:
        end_oos = months[-1]

    # Rebalancing dates: every retrain_freq months within OOS range
    oos_months = months[(months >= start_oos) & (months <= end_oos)]
    rebalance_dates = oos_months[::retrain_freq]

    for i, rb_date in enumerate(rebalance_dates):
        # Training: all months strictly before rb_date
        train_mask = df['yyyymm'] < rb_date
        # Test: from rb_date up to (but not including) next rebalance date
        if i + 1 < len(rebalance_dates):
            test_mask = (df['yyyymm'] >= rb_date) & (df['yyyymm'] < rebalance_dates[i + 1])
        else:
            test_mask = df['yyyymm'] >= rb_date

        train_df = df.loc[train_mask]
        test_df = df.loc[test_mask]

        if len(train_df) == 0 or len(test_df) == 0:
            continue

        yield train_df, test_df


def build_managed_portfolios(
    df: pd.DataFrame,
    n_ports: int = 37,
    chars: list[str] | None = None,
    ret_col: str = 'RET',
    weight_col: str = 'me',
) -> pd.DataFrame:
    """
    Build characteristic-sorted managed portfolios.

    For a subset of characteristics, sort stocks into quintiles each month,
    compute value-weighted portfolio returns. Returns a portfolio-level panel
    with ~n_ports rows per month.

    Parameters
    ----------
    df : stock-level panel with yyyymm, RET, me, and characteristic columns
    n_ports : target number of portfolios (selects top chars by coverage)
    chars : specific characteristics to use (default: auto-select by coverage)
    ret_col : return column name
    weight_col : weight column for value-weighting

    Returns
    -------
    DataFrame with columns: yyyymm, port_id, port_ret, and characteristic means
    """
    char_cols = chars if chars is not None else get_characteristic_cols(df)

    # Select characteristics with best coverage
    coverage = df[char_cols].notna().mean().sort_values(ascending=False)
    n_chars = max(1, (n_ports - 2) // 5)
    selected_chars = coverage.head(n_chars).index.tolist()
    macro_cols = get_macro_cols(df)

    # --- Vectorized market portfolios ---
    work = df[['yyyymm', ret_col, weight_col] + selected_chars].copy()
    work[weight_col] = work[weight_col].fillna(0)
    work[ret_col] = work[ret_col].fillna(0)

    # Macro: one row per month (first value)
    macro_present = [c for c in macro_cols if c in df.columns]
    if macro_present:
        macro_monthly = df.groupby('yyyymm')[macro_present].first().reset_index()
    else:
        macro_monthly = df[['yyyymm']].drop_duplicates()

    # Market portfolios: VW and EW
    def _vw_ret(g):
        w = g[weight_col].values
        r = g[ret_col].values
        ws = w.sum()
        return (r * w).sum() / ws if ws > 0 else r.mean()

    mkt_vw = work.groupby('yyyymm').apply(_vw_ret, include_groups=False).reset_index(name='port_ret')
    mkt_vw['port_id'] = 'MKT_VW'
    mkt_ew = work.groupby('yyyymm')[ret_col].mean().reset_index(name='port_ret')
    mkt_ew['port_id'] = 'MKT_EW'

    # Char means for market portfolios
    mkt_char_means = work.groupby('yyyymm')[selected_chars].mean().reset_index()

    mkt_vw = mkt_vw.merge(mkt_char_means, on='yyyymm')
    mkt_ew = mkt_ew.merge(mkt_char_means, on='yyyymm')

    port_frames = [mkt_vw, mkt_ew]

    # --- Quintile portfolios per characteristic ---
    for char in selected_chars:
        sub = work[work[char].notna()].copy()
        # Assign quintiles within each month
        sub['_qnt'] = sub.groupby('yyyymm')[char].transform(
            lambda x: pd.qcut(x, 5, labels=False, duplicates='drop') if len(x) >= 25 else np.nan
        )
        sub = sub.dropna(subset=['_qnt'])
        sub['_qnt'] = sub['_qnt'].astype(int)

        # VW returns within month-quintile
        def _vw_group(g):
            w = g[weight_col].values
            r = g[ret_col].values
            ws = w.sum()
            return (r * w).sum() / ws if ws > 0 else r.mean()

        qnt_ret = sub.groupby(['yyyymm', '_qnt']).apply(_vw_group, include_groups=False).reset_index(name='port_ret')
        qnt_chars = sub.groupby(['yyyymm', '_qnt'])[selected_chars].mean().reset_index()
        qnt = qnt_ret.merge(qnt_chars, on=['yyyymm', '_qnt'])
        qnt['port_id'] = char + '_Q' + (qnt['_qnt'] + 1).astype(str)
        qnt = qnt.drop(columns=['_qnt'])
        port_frames.append(qnt)

    port_df = pd.concat(port_frames, ignore_index=True)
    # Merge macro
    if macro_present:
        port_df = port_df.merge(macro_monthly, on='yyyymm', how='left')

    return port_df
