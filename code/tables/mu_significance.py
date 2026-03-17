"""
Generate Table 12: Per-Window μ_g Significance.

Reads output/cv_window_results.json and shows which restriction groups
have non-zero μ_g in each rolling window for the Theory-KRR (λ=λ*) model.
Only active groups (μ_g > 0) are shown; cells show μ_g values.
"""
import json
from pathlib import Path


GROUP_ORDER = [
    'consumption', 'production', 'intermediary', 'information',
    'demand', 'volatility', 'behavioral', 'macro',
]

GROUP_SHORT = {
    'consumption': 'Cons.',
    'production': 'Prod.',
    'intermediary': 'Interm.',
    'information': 'Info.',
    'demand': 'Demand',
    'volatility': 'Vol.',
    'behavioral': 'Behav.',
    'macro': 'Macro',
}


def _fmt_mu(val: float) -> str:
    """Format μ value: empty if zero, formatted if active."""
    if val < 1e-6:
        return ''
    if val >= 10:
        return f'${val:.0f}$'
    elif val >= 1:
        return f'${val:.1f}$'
    elif val >= 0.01:
        return f'${val:.2f}$'
    else:
        return f'${val:.1e}$'


def generate(output_path: str = 'paper/tables/table_12.tex') -> str:
    """Generate Table 12: per-window μ_g significance."""
    json_path = Path('output/cv_window_results.json')

    if json_path.exists():
        with open(json_path) as f:
            windows = json.load(f)
    else:
        windows = []

    windows = sorted(windows, key=lambda x: x.get('test_year', 0))

    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Cross-Validated Theory Multipliers $\hat{\mu}_g$ by Rolling Window}')
    lines.append(r'\label{tab:mu_significance}')
    lines.append(r'\footnotesize')

    # Column spec: l for year + 8 c columns for groups
    col_spec = 'l' + 'c' * len(GROUP_ORDER)
    lines.append(f'\\begin{{tabular}}{{{col_spec}}}')
    lines.append(r'\toprule')

    # Header
    header = 'Test Year & ' + ' & '.join(GROUP_SHORT[g] for g in GROUP_ORDER) + r' \\'
    lines.append(header)
    lines.append(r'\midrule')

    # Data rows
    for w in windows:
        year = w.get('test_year', w.get('test_start', 0) // 100)
        mu_groups = w.get('mu_groups', {})

        cells = [str(year)]
        for g in GROUP_ORDER:
            val = mu_groups.get(g, 0.0)
            cells.append(_fmt_mu(val))

        lines.append(' & '.join(cells) + r' \\')

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    # Notes
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{4pt}')
    lines.append(r'\footnotesize')
    lines.append(
        r"\textit{Notes:} Each cell reports the cross-validated group-level multiplier "
        r"$\hat{\mu}_g$ for the Theory-KRR ($\lambda=\lambda^*$) specification. "
        r"Empty cells indicate $\hat{\mu}_g = 0$ (group inactive in that window). "
        r"Multipliers are selected by coordinate descent on the validation sample "
        r"as described in Section~\ref{sub:cv_strategy}."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    tex = '\n'.join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(tex, encoding='utf-8')
    return output_path
