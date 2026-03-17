"""
Generate Table 12: Theory-KRR Validation Improvement by Subperiod.

Reads output/cv_window_results.json and groups windows by time period,
crisis vs non-crisis, and training length.
"""
import json
from pathlib import Path
from collections import Counter

# Reuse config display names
from code.tables.theory_ranking import _CONFIG_DISPLAY


def _year_from_yyyymm(yyyymm: int) -> int:
    return yyyymm // 100


def _gain_pct(w: dict) -> float | None:
    """Compute val MSE gain % for a single window."""
    krr = w.get('krr_val_mse', 0)
    best = w.get('best_val_mse', 0)
    if krr > 0 and best > 0:
        return (krr - best) / krr * 100
    return None


def _most_frequent_config(windows: list[dict]) -> str:
    """Return the most common best_config among windows."""
    configs = [w.get('best_config', '') for w in windows]
    if not configs:
        return '---'
    counter = Counter(configs)
    top = counter.most_common(3)
    names = [_CONFIG_DISPLAY.get(c, c) for c, _ in top]
    return ', '.join(names)


def _avg_gain(windows: list[dict]) -> str:
    """Compute average gain across windows, return formatted string."""
    gains = [_gain_pct(w) for w in windows]
    gains = [g for g in gains if g is not None]
    if not gains:
        return '---'
    return f'{sum(gains) / len(gains):.3f}'


def _window_indices(windows: list[dict]) -> str:
    """Format window indices as '0--5' or '6, 8'."""
    idxs = [w.get('window', 0) for w in windows]
    if not idxs:
        return '---'
    if len(idxs) <= 3:
        return ', '.join(str(i) for i in sorted(idxs))
    lo, hi = min(idxs), max(idxs)
    return f'{lo}--{hi}'


def generate(output_path: str = 'paper/tables/table_12.tex') -> str:
    """Generate Table 12 and write to output_path."""
    json_path = Path('output/cv_window_results.json')

    if json_path.exists():
        with open(json_path) as f:
            windows = json.load(f)
    else:
        windows = []

    # Classify windows
    pre2000 = [w for w in windows if _year_from_yyyymm(w['test_end']) <= 2000]
    post2000 = [w for w in windows if _year_from_yyyymm(w['test_start']) >= 2001]

    # Crisis: OOS period overlaps with dot-com (2001-2003) or GFC (2007-2009)
    def _is_crisis(w):
        s, e = _year_from_yyyymm(w['test_start']), _year_from_yyyymm(w['test_end'])
        return (s <= 2003 and e >= 2001) or (s <= 2009 and e >= 2007)

    crisis = [w for w in windows if _is_crisis(w)]
    non_crisis = [w for w in windows if not _is_crisis(w)]

    # Training length: estimate from test_start relative to 196307 (first month)
    def _train_months(w):
        return (w['test_start'] // 100 - 1963) * 12

    early_train = [w for w in windows if _train_months(w) < 300]
    late_train = [w for w in windows if _train_months(w) >= 400]

    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Theory-KRR Validation Improvement over KRR by Subperiod}')
    lines.append(r'\label{tab:subsample}')
    lines.append(r'\small')
    lines.append(r'\begin{tabular}{lccc}')
    lines.append(r'\toprule')
    lines.append(r'Subperiod & Windows & Avg.\ Val.\ MSE Gain (\%) & Best Theory Family \\')
    lines.append(r'\midrule')

    rows = [
        (f'Pre-2000 (1983--2000)', pre2000),
        (f'Post-2000 (2001--2023)', post2000),
        None,  # spacing
        ('Crisis windows', crisis),
        ('Non-crisis windows', non_crisis),
        None,  # spacing
        ('Early training ($<$300mo)', early_train),
        ('Late training ($>$400mo)', late_train),
    ]

    for row in rows:
        if row is None:
            lines[-1] = lines[-1].rstrip('\\\\') + '\\\\[4pt]'
            continue
        label, subset = row
        if not subset:
            lines.append(f'{label} & --- & --- & --- \\\\')
        else:
            wi = _window_indices(subset)
            avg = _avg_gain(subset)
            best = _most_frequent_config(subset)
            lines.append(f'{label} & {wi} & {avg} & {best} \\\\')

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    # Notes
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{4pt}')
    lines.append(r'\footnotesize')
    lines.append(
        r"\textit{Notes:} Val.\ MSE gain is the percentage reduction in validation MSE "
        r"of the best Theory-KRR configuration relative to standard KRR. Crisis windows "
        r"are those whose OOS period includes the dot-com bust (2001--2003) or the global "
        r"financial crisis (2007--2009). Improvement is measured on the temporal validation "
        r"set within each window before out-of-sample prediction."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    tex = '\n'.join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(tex, encoding='utf-8')
    return output_path
