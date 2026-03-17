"""
Generate Table 1: Summary Statistics (split into 1a, 1b, 1c-1g).

- Table 1a: Returns + sample coverage
- Table 1b: Macroeconomic state variables
- Tables 1c--1g: All firm characteristics (ranked), ~50 per table
"""
import numpy as np
import pandas as pd
from pathlib import Path

from code.utils.data_loader import load_panel, get_characteristic_cols, get_macro_cols


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

CHARS_PER_TABLE = 50  # max characteristics per table page


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


def _fmt_pct(x, decimals=1):
    if pd.isna(x):
        return '---'
    return f'{x:.{decimals}f}'


def _make_char_table(char_stats: list[dict], table_num: str, start_idx: int,
                     total_chars: int, out_dir: Path) -> str:
    """Generate a single characteristics summary table."""
    suffix = chr(ord('c') + (start_idx // CHARS_PER_TABLE))
    label = f'tab:summary_chars_{suffix}'
    caption = (
        f'Summary Statistics: Firm Characteristics (Ranked), '
        f'Part~{start_idx // CHARS_PER_TABLE + 1}'
    )

    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(f'\\caption{{{caption}}}')
    lines.append(f'\\label{{{label}}}')
    lines.append(r'\scriptsize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{0.85}')
    lines.append(r'\begin{tabular}{lrrrr}')
    lines.append(r'\toprule')
    lines.append(r'Characteristic & $N$ & Coverage (\%) & Mean & Std \\')
    lines.append(r'\midrule')

    for row in char_stats:
        name = row['name'].replace('_', r'\_')
        lines.append(
            f'{name:<40s} & {_fmt(row["n"], 0)} & {_fmt_pct(row["coverage"])} '
            f'& {_fmt(row["mean"], 3)} & {_fmt(row["std"], 3)} \\\\'
        )

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    if start_idx == 0:
        lines.append(r'\begin{minipage}{\textwidth}')
        lines.append(r'\vspace{2pt}')
        lines.append(r'\scriptsize\setstretch{0.85}')
        lines.append(
            r"\textit{Notes:} Summary statistics for all " + str(total_chars) +
            r" firm characteristics used as predictors. "
            r"All characteristics are cross-sectionally ranked to $[0,1]$ each month "
            r"(mean $\approx 0.50$, std $\approx 0.29$ for uniformly available variables). "
            r"$N$ is the number of non-missing stock-month observations; "
            r"Coverage is $N$ as a percentage of total stock-month observations in the panel. "
            r"Characteristics are sourced from the Open Source Asset Pricing (OSAP) dataset "
            r"of \citet{jensen2023machine}, CRSP, and Compustat."
        )
        lines.append(r'\end{minipage}')

    lines.append(r'\end{table}')

    path = out_dir / f'table_1{suffix}.tex'
    path.write_text('\n'.join(lines), encoding='utf-8')
    return str(path)


def generate(output_path: str = 'paper/tables/table_1.tex') -> str:
    """Generate Tables 1a--1g. Returns the path of table_1a."""
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load panel
    print('  Loading panel...')
    df = load_panel()
    df['excess_ret_pct'] = (df['RET'] - df['rf']) * 100
    total_obs = len(df)

    # ================================================================
    #  Table 1a: Returns + sample coverage
    # ================================================================
    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Summary Statistics: Returns and Sample Coverage}')
    lines.append(r'\label{tab:summary}')
    lines.append(r'\scriptsize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{0.9}')
    lines.append(r'\begin{tabular}{lrrrrrr}')
    lines.append(r'\toprule')
    lines.append(r' & $N$ & Mean & Std & P5 & P50 & P95 \\')
    lines.append(r'\midrule')
    lines.append(r"\multicolumn{7}{l}{\textit{Panel A: Monthly excess returns}} \\")

    valid = df['excess_ret_pct'].dropna()
    lines.append(
        f'Excess return (\\%)'
        f' & {_fmt(len(valid), 0)} & {_fmt_signed(valid.mean())} & {_fmt(valid.std())}'
        f' & {_fmt_signed(valid.quantile(0.05))} & {_fmt_signed(valid.median())}'
        f' & {_fmt_signed(valid.quantile(0.95))} \\\\'
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

    # Add total char count summary
    char_cols = get_characteristic_cols(df)
    macro_cols = get_macro_cols(df)
    lines.append(r'\\[2pt]')
    lines.append(r"\multicolumn{7}{l}{\textit{Panel C: Predictor counts}} \\")
    lines.append(f'Firm characteristics & \\multicolumn{{5}}{{l}}{{{len(char_cols)}}} \\\\')
    lines.append(f'Macroeconomic variables & \\multicolumn{{5}}{{l}}{{{len(macro_cols)}}} \\\\')
    lines.append(f'Total predictors & \\multicolumn{{5}}{{l}}{{{len(char_cols) + len(macro_cols)}}} \\\\')

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{2pt}')
    lines.append(r'\scriptsize\setstretch{0.85}')
    lines.append(
        r"\textit{Notes:} Panel~A reports the distribution of monthly excess returns (\%) "
        r"across all stock-month observations (July 1963--December 2023). "
        r"Panel~B reports the average number of stocks per month within each decade. "
        r"Panel~C reports the number of predictors used by all models."
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
        mn = monthly_scaled.mean()
        sd = monthly_scaled.std()
        ac1 = monthly.autocorr(lag=1)
        lines.append(
            f'{display_name}'
            f' & {t} & {_fmt_signed(mn)} & {_fmt(sd)}'
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

    # ================================================================
    #  Tables 1c--1g: All firm characteristics (ranked)
    # ================================================================
    print(f'  Computing statistics for {len(char_cols)} characteristics...')
    char_stats = []
    for col in sorted(char_cols):
        if col not in df.columns:
            continue
        s = df[col].dropna()
        n = len(s)
        if n == 0:
            continue
        char_stats.append({
            'name': col,
            'n': n,
            'coverage': n / total_obs * 100,
            'mean': s.mean(),
            'std': s.std(),
        })

    # Sort by coverage (most available first), then alphabetically
    char_stats.sort(key=lambda x: (-x['coverage'], x['name']))

    # Split into pages
    char_table_paths = []
    for i in range(0, len(char_stats), CHARS_PER_TABLE):
        batch = char_stats[i:i + CHARS_PER_TABLE]
        p = _make_char_table(batch, '', i, len(char_stats), out_dir)
        char_table_paths.append(p)
        print(f'  -> {p}')

    print(f'  Generated {len(char_table_paths)} characteristic tables '
          f'({len(char_stats)} variables)')

    return str(path_1a)
