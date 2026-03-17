"""
Generate Table 1: Summary Statistics (split into 1a and 1b).

Computes raw (unranked) firm characteristics from source files, filtered
to the same stock-month universe as the panel. Macro stats from the panel.
"""
import numpy as np
import pandas as pd
from pathlib import Path

from code.utils.data_loader import load_panel, get_macro_cols


# Display config: (display_name, raw_col, panel_col, decimals)
_CHAR_DISPLAY = [
    ('Book-to-market', 'bm_raw', 'bm', 2),
    ('Momentum 12m', 'Mom12m_raw', 'Mom12m', 2),
    ('Short-term reversal', 'strev_raw', 'streversal', 3),
    ('Investment/capital', 'ik_raw', 'ik', 2),
    ('ROE', 'roe_raw', 'roe', 2),
    ('Asset growth', 'ag_raw', 'ag', 2),
    ('Gross profitability', 'gp_raw', 'gp', 2),
    ('Leverage', 'leverage_raw', 'leverage', 2),
    ('R\\&D intensity', 'rd_raw', 'rd_intensity', 3),
    ('SGA/assets', 'sga_raw', 'sga_at', 2),
    ('K/debt (collateral)', 'k_debt_raw', 'k_debt', 2),
]

# Display names and scale factor for macro variables
_MACRO_DISPLAY = {
    'mktrf': ('Market excess return', 100),
    'rf': ('Risk-free rate (\\%)', 100),
    'term_spread': ('Term spread (\\%)', 1),
    'default_spread': ('Default spread (\\%)', 1),
    'vix': ('VIX', 1),
    'ebp': ('Excess bond premium (\\%)', 1),
    'sentiment': ('Sentiment (BW)', 1),
    'cons_growth': ('Consumption growth (\\%)', 100),
    'hkm_capital_ratio': ('HKM capital ratio', 1),
    'cay': ('$cay$', 1),
    'ted_spread': ('TED spread (\\%)', 1),
    'bab': ('BAB factor', 100),
    'breakeven_infl': ('Breakeven inflation (\\%)', 1),
}

_DECADES = [
    ('1963--1969', 196300, 196999),
    ('1970--1979', 197000, 197999),
    ('1980--1989', 198000, 198999),
    ('1990--1999', 199000, 199999),
    ('2000--2009', 200000, 200999),
    ('2010--2023', 201000, 202399),
]


def _fmt(x, decimals=2):
    if pd.isna(x):
        return '---'
    if isinstance(x, (int, np.integer)):
        return f'{x:,}'
    return f'{x:,.{decimals}f}'


def _fmt_signed(x, decimals=2):
    if pd.isna(x):
        return '---'
    rounded = round(x, decimals)
    if rounded == 0:
        return f'{0:.{decimals}f}'
    s = f'{x:.{decimals}f}'
    if x < 0:
        return f'${s}$'
    return s


def _build_raw_chars(raw_dir: Path, panel_keys: pd.DataFrame) -> dict:
    """Compute raw characteristics, filtered to panel universe.

    panel_keys: DataFrame with (permno, yyyymm, gvkey) from the panel.
    Returns dict of col_name -> Series of raw values.
    """
    raw = {}

    # --- Compustat annual ratios (matched via gvkey) ---
    print('    Compustat ratios...')
    comp = pd.read_csv(raw_dir / 'compustat_annual.csv', low_memory=False)
    comp = comp[
        (comp['indfmt'] == 'INDL') & (comp['datafmt'] == 'STD')
        & (comp['consol'] == 'C') & (comp['curcd'] == 'USD')
    ].copy()
    comp['gvkey'] = comp['gvkey'].astype(str).str.zfill(6)
    # Filter to gvkeys in the panel
    panel_gvkeys = set(panel_keys['gvkey'].dropna().unique())
    comp = comp[comp['gvkey'].isin(panel_gvkeys)].copy()

    at = comp['at'].replace(0, np.nan)
    ceq = comp['ceq'].replace(0, np.nan)
    sale = comp['sale'].replace(0, np.nan)
    ppent = comp['ppent'].replace(0, np.nan)
    total_debt = (comp['dlc'].fillna(0) + comp['dltt'].fillna(0)).replace(0, np.nan)

    comp['bm_raw'] = ceq / (comp['csho'] * comp['prcc_f']).replace(0, np.nan)
    comp['ik_raw'] = comp['capx'] / ppent
    comp['roe_raw'] = comp['ib'] / ceq
    comp['ag_raw'] = comp.groupby('gvkey')['at'].pct_change(fill_method=None)
    comp['gp_raw'] = (comp['revt'] - comp['cogs']) / at
    comp['leverage_raw'] = (comp['dlc'].fillna(0) + comp['dltt'].fillna(0)) / at
    comp['rd_raw'] = comp['xrd'].fillna(0) / sale
    comp['sga_raw'] = comp['xsga'].fillna(np.nan) / at
    comp['k_debt_raw'] = ppent / total_debt

    comp_cols = ['bm_raw', 'ik_raw', 'roe_raw', 'ag_raw', 'gp_raw',
                 'leverage_raw', 'rd_raw', 'sga_raw', 'k_debt_raw']
    for col in comp_cols:
        s = comp[col].dropna()
        if len(s) > 0:
            lo, hi = s.quantile(0.01), s.quantile(0.99)
            raw[col] = s.clip(lo, hi)

    # --- Mom12m from JKP (filtered to panel permnos) ---
    print('    Mom12m...')
    panel_permnos = set(panel_keys['permno'].unique())
    vals = []
    for chunk in pd.read_csv(
        raw_dir / 'firm_characteristics.csv',
        chunksize=500_000, low_memory=False, usecols=['permno', 'Mom12m'],
    ):
        chunk = chunk[chunk['permno'].isin(panel_permnos)]
        vals.append(chunk['Mom12m'].dropna())
    mom = pd.concat(vals)
    lo, hi = mom.quantile(0.01), mom.quantile(0.99)
    raw['Mom12m_raw'] = mom.clip(lo, hi)

    # --- Short-term reversal from CRSP (filtered to panel permnos) ---
    print('    Short-term reversal...')
    crsp = pd.read_csv(
        raw_dir / 'crsp_monthly.csv', low_memory=False,
        usecols=['PERMNO', 'RET', 'SHRCD', 'EXCHCD', 'PRC'],
    )
    crsp = crsp.rename(columns={'PERMNO': 'permno'})
    crsp['RET'] = pd.to_numeric(crsp['RET'], errors='coerce')
    crsp['PRC'] = pd.to_numeric(crsp['PRC'], errors='coerce').abs()
    crsp = crsp[
        crsp['SHRCD'].isin([10, 11]) & crsp['EXCHCD'].isin([1, 2, 3])
        & (crsp['PRC'] >= 5) & crsp['permno'].isin(panel_permnos)
    ]
    ret = crsp['RET'].dropna()
    lo, hi = ret.quantile(0.01), ret.quantile(0.99)
    raw['strev_raw'] = ret.clip(lo, hi)

    return raw


def generate(output_path: str = 'paper/tables/table_1.tex') -> str:
    """Generate Tables 1a and 1b. Returns the path of table_1a."""
    raw_dir = Path('data/raw')
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load panel for keys, returns, macro, and coverage
    print('  Loading panel...')
    df = load_panel()
    df['excess_ret_pct'] = (df['RET'] - df['rf']) * 100
    panel_keys = df[['permno', 'yyyymm', 'gvkey']].copy()

    # Build raw characteristics filtered to panel universe
    print('  Building raw characteristics...')
    raw_chars = _build_raw_chars(raw_dir, panel_keys)

    # ================================================================
    #  Table 1a: Panel A (firm chars) + Panel B (sample coverage)
    # ================================================================
    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Summary Statistics: Returns and Firm Characteristics}')
    lines.append(r'\label{tab:summary}')
    lines.append(r'\scriptsize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{0.9}')
    lines.append(r'\begin{tabular}{lrrrrrr}')
    lines.append(r'\toprule')
    lines.append(r' & $N$ & Mean & Std & P5 & P50 & P95 \\')
    lines.append(r'\midrule')
    lines.append(r"\multicolumn{7}{l}{\textit{Panel A: Monthly excess returns and firm characteristics}} \\")

    valid = df['excess_ret_pct'].dropna()
    lines.append(
        f'Excess return (\\%)'
        f' & {_fmt(len(valid), 0)} & {_fmt_signed(valid.mean())} & {_fmt(valid.std())}'
        f' & {_fmt_signed(valid.quantile(0.05))} & {_fmt_signed(valid.median())}'
        f' & {_fmt_signed(valid.quantile(0.95))} \\\\'
    )

    for display_name, col_key, panel_col, dec in _CHAR_DISPLAY:
        if col_key not in raw_chars:
            continue
        s = raw_chars[col_key]
        # Use panel N (stock-month level) for consistent observation counts
        n = df[panel_col].notna().sum() if panel_col in df.columns else len(s)
        lines.append(
            f'{display_name}'
            f' & {_fmt(n, 0)} & {_fmt_signed(s.mean(), dec)} & {_fmt(s.std(), dec)}'
            f' & {_fmt_signed(s.quantile(0.05), dec)} & {_fmt_signed(s.median(), dec)}'
            f' & {_fmt_signed(s.quantile(0.95), dec)} \\\\'
        )

    lines.append(r'\\[2pt]')
    lines.append(r"\multicolumn{7}{l}{\textit{Panel B: Sample coverage (avg.\ stocks per month by decade)}} \\")

    stocks_per_month = df.groupby('yyyymm')['permno'].nunique().reset_index(name='n_stocks')
    decade_stats = []
    for label, lo, hi in _DECADES:
        mask = (stocks_per_month['yyyymm'] >= lo) & (stocks_per_month['yyyymm'] <= hi)
        subset = stocks_per_month.loc[mask, 'n_stocks']
        avg = int(round(subset.mean())) if len(subset) > 0 else 0
        decade_stats.append((label, avg))

    for i in range(3):
        ll, lv = decade_stats[i]
        rl, rv = decade_stats[i + 3]
        lines.append(
            f'{ll} & \\multicolumn{{2}}{{l}}{{{_fmt(lv, 0)}}}'
            f' & {rl} & \\multicolumn{{2}}{{l}}{{{_fmt(rv, 0)}}} & \\\\'
        )

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{2pt}')
    lines.append(r'\scriptsize\setstretch{0.85}')
    lines.append(
        r"\textit{Notes:} Panel~A reports the distribution of monthly excess returns (\%) "
        r"and selected firm characteristics across all stock-month observations "
        r"(July 1963--December 2023). Compustat ratios are winsorized at the 1st and 99th "
        r"percentiles. Observation counts for Compustat-derived variables reflect firm-year "
        r"coverage; CRSP and OSAP variables are at the stock-month level. "
        r"Panel~B reports the average number of stocks per month within each decade."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    path_1a = out_dir / 'table_1a.tex'
    path_1a.write_text('\n'.join(lines), encoding='utf-8')

    # ================================================================
    #  Table 1b: Macroeconomic state variables
    # ================================================================
    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Summary Statistics: Macroeconomic State Variables}')
    lines.append(r'\label{tab:summary_macro}')
    lines.append(r'\scriptsize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{0.9}')
    lines.append(r'\begin{tabular}{lrrrr}')
    lines.append(r'\toprule')
    lines.append(r' & $T$ & Mean & Std & AC(1) \\')
    lines.append(r'\midrule')

    for col_name, (display_name, scale) in _MACRO_DISPLAY.items():
        if col_name not in df.columns:
            continue
        monthly = df.groupby('yyyymm')[col_name].first().dropna()
        monthly_scaled = monthly * scale
        t = len(monthly)
        mean = monthly_scaled.mean()
        std = monthly_scaled.std()
        ac1 = monthly.autocorr(lag=1)
        lines.append(
            f'{display_name}'
            f' & {t} & {_fmt_signed(mean)} & {_fmt(std)}'
            f' & {_fmt_signed(ac1)} \\\\'
        )

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{2pt}')
    lines.append(r'\scriptsize\setstretch{0.85}')
    lines.append(
        r"\textit{Notes:} Time-series summary statistics for macroeconomic state variables "
        r"at monthly frequency; AC(1) is the first-order autocorrelation. "
        r"VIX available from 1990; HKM capital ratio from 1970; Baker-Wurgler sentiment from 1965; "
        r"TED spread from 1986 to 2022 (LIBOR discontinued); breakeven inflation from 2003."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    path_1b = out_dir / 'table_1b.tex'
    path_1b.write_text('\n'.join(lines), encoding='utf-8')

    return str(path_1a)
