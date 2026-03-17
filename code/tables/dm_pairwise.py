"""
Generate Table: Pairwise Diebold-Mariano Test Statistics.

Reads output/oos_predictions.csv (per-observation OOS predictions)
and computes pairwise DM test statistics with Newey-West HAC standard errors.
Lower-triangular matrix with significance stars.
"""
import numpy as np
import pandas as pd
from pathlib import Path


# Model display order (must match oos_performance._MODEL_ORDER keys)
_MODEL_ORDER = [
    ('ols', 'OLS'),
    ('ridge', 'Ridge'),
    ('lasso', 'Lasso'),
    ('elastic_net', 'EN'),
    ('ridge_poly2', 'Ridge-P2'),
    ('lasso_poly2', 'Lasso-P2'),
    ('en_poly2', 'EN-P2'),
    ('krr', 'KRR'),
    ('tikrr_lam0', r'T-KRR($\lambda{=}0$)'),
    ('best_tikrr', r'T-KRR($\lambda{=}\lambda^*$)'),
]


def _dm_statistic(e_row: np.ndarray, e_col: np.ndarray, nlags: int = 6) -> float:
    """Diebold-Mariano test statistic. Positive means row model is better than column."""
    d = e_col ** 2 - e_row ** 2  # positive = row is better
    n = len(d)
    if n < nlags + 2:
        return np.nan
    dbar = d.mean()
    # Newey-West HAC variance
    gamma0 = np.var(d, ddof=0)
    v = gamma0
    for lag in range(1, nlags + 1):
        gl = np.mean((d[lag:] - dbar) * (d[:-lag] - dbar))
        w = 1.0 - lag / (nlags + 1)  # Bartlett kernel
        v += 2 * w * gl
    v = max(v, 1e-20)
    return dbar / np.sqrt(v / n)


def _stars(t_stat: float) -> str:
    """Significance stars based on normal approximation."""
    if np.isnan(t_stat):
        return ''
    at = abs(t_stat)
    if at >= 2.576:
        return '***'
    elif at >= 1.960:
        return '**'
    elif at >= 1.645:
        return '*'
    return ''


def generate(output_path: str = 'paper/tables/table_dm.tex') -> str:
    """Generate pairwise DM test table."""
    csv_path = Path('output/oos_predictions.csv')
    if not csv_path.exists():
        print(f'  [SKIP] {csv_path} not found — run estimation first')
        return ''

    df = pd.read_csv(csv_path)
    realized = df['realized'].values

    # Filter to models present in the data
    models = [(key, label) for key, label in _MODEL_ORDER if key in df.columns]
    n_models = len(models)

    if n_models < 2:
        print('  [SKIP] Need at least 2 models for DM test')
        return ''

    # Compute errors
    errors = {}
    for key, _ in models:
        errors[key] = realized - df[key].values

    # Compute pairwise DM statistics (lower triangular: row vs column)
    dm_matrix = np.full((n_models, n_models), np.nan)
    for i in range(n_models):
        for j in range(i):
            dm_matrix[i, j] = _dm_statistic(errors[models[i][0]], errors[models[j][0]])

    # Build LaTeX table
    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Pairwise Diebold-Mariano Test Statistics}')
    lines.append(r'\label{tab:dm_pairwise}')
    lines.append(r'\small')

    # Column spec: l + n_models c columns (but last column header not needed)
    col_spec = 'l' + 'c' * (n_models - 1)
    lines.append(f'\\begin{{tabular}}{{{col_spec}}}')
    lines.append(r'\toprule')

    # Header row (column models, skip last since it has no entries below it)
    header = ' & '.join([label for _, label in models[:-1]])
    lines.append(f'& {header} \\\\')
    lines.append(r'\midrule')

    # Data rows (skip first model since it has no entries)
    for i in range(1, n_models):
        row_label = models[i][1]
        cells = []
        for j in range(n_models - 1):
            if j < i:
                t = dm_matrix[i, j]
                if np.isnan(t):
                    cells.append('---')
                else:
                    stars = _stars(t)
                    cells.append(f'${t:.2f}${stars}')
            else:
                cells.append('')
        line = row_label + ' & ' + ' & '.join(cells) + ' \\\\'
        lines.append(line)

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    # Notes
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{4pt}')
    lines.append(r'\footnotesize')
    lines.append(
        r"\textit{Notes:} Each cell reports the Diebold-Mariano test statistic "
        r"for equal predictive accuracy between the row model and the column model. "
        r"Positive values indicate the row model has lower squared prediction error. "
        r"Newey-West standard errors with 6 lags. "
        r"$^{*}$~$p<0.10$, $^{**}$~$p<0.05$, $^{***}$~$p<0.01$ (two-sided)."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    tex = '\n'.join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(tex, encoding='utf-8')
    return output_path
