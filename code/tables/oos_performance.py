"""
Generate Table 10: Out-of-Sample Prediction Performance.

Reads output/cv_results.csv and formats the OOS R-squared and DM statistics.
Models not present in the CSV get placeholder dashes.
"""
import pandas as pd
from pathlib import Path


# Map CSV row names → (display name, section)
_MODEL_ORDER = [
    # (csv_key, display_name, section_header_or_None)
    ('hist_mean', 'Historical mean', 'Linear benchmarks'),
    ('ols', 'OLS (all predictors)', None),
    ('ridge', 'Ridge regression', None),
    ('lasso', 'Lasso', None),
    ('elastic_net', 'Elastic net', None),
    ('krr', 'Kernel ridge regression', 'Nonlinear benchmark'),
    ('best_tikrr', 'Theory-KRR (best config)', 'Theory-informed models'),
]


def _fmt(x, decimals=2):
    if pd.isna(x):
        return '---'
    val = float(x)
    s = f'{val:.{decimals}f}'
    if val < 0:
        return f'${s}$'
    return f'${s}$'


def generate(output_path: str = 'paper/tables/table_10.tex') -> str:
    """Generate Table 10 and write to output_path."""
    csv_path = Path('output/cv_results.csv')
    if csv_path.exists():
        data = pd.read_csv(csv_path, index_col=0)
    else:
        data = pd.DataFrame()

    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Out-of-Sample Prediction Performance (Managed Portfolios)}')
    lines.append(r'\label{tab:oos_performance}')
    lines.append(r'\small')
    lines.append(r'\begin{tabular}{lccc}')
    lines.append(r'\toprule')
    lines.append(r'Model & $R^2_{\text{OOS}}$ (\%) & SR (ann.) & DM vs.\ Hist.\ Mean \\')
    lines.append(r'\midrule')

    current_section = None
    for csv_key, display_name, section in _MODEL_ORDER:
        if section is not None and section != current_section:
            current_section = section
            lines.append(f'\\multicolumn{{4}}{{l}}{{\\textit{{{section}}}}} \\\\')

        if csv_key in data.index:
            row = data.loc[csv_key]
            r2 = _fmt(row.get('r2_oos_pct'))
            sr = _fmt(row.get('sharpe_ann'))
            dm = _fmt(row.get('dm_vs_hm'))
        else:
            r2 = '---'
            sr = '---'
            dm = '---'

        # Historical mean has no DM against itself
        if csv_key == 'hist_mean':
            dm = '---'

        # Add spacing before nonlinear/theory sections
        spacing = '[4pt]' if section is not None and csv_key != 'hist_mean' else ''
        lines.append(f'{display_name:<30s} & {r2} & {sr} & {dm} \\\\{spacing}')

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    # Notes
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{4pt}')
    lines.append(r'\footnotesize')
    lines.append(
        r"\textit{Notes:} $R^2_{\text{OOS}}$ is defined as "
        r"$1 - \sum_s (R_s - \hat{f}(\mathbf{X}_s))^2 / \sum_s (R_s - \bar{R})^2$, "
        r"where $\bar{R}$ is the historical mean computed using only data available at "
        r"the time of prediction. SR is the annualized Sharpe ratio of a long-short "
        r"decile portfolio sorted on predicted returns. "
        r"DM is the Diebold-Mariano test statistic for equal "
        r"predictive accuracy relative to the historical mean, using Newey-West standard "
        r"errors with 6 lags. The evaluation period is 1987--2023 following the "
        r"rolling three-way split of \citet{gu2020empirical} with 12-year validation "
        r"windows and annual rebalancing."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    tex = '\n'.join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(tex, encoding='utf-8')
    return output_path
