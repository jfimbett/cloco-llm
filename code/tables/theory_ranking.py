"""
Generate Table 11: Temporal Variation in Optimal Theory Family.

Reads output/cv_window_results.json and formats per-window best configurations.
"""
import json
import pandas as pd
from pathlib import Path


# Map config keys to display names
_CONFIG_DISPLAY = {
    'krr_only': 'Standard KRR',
    'all_0.001': 'All groups ($\\mu = 0.001$)',
    'all_0.01': 'All groups ($\\mu = 0.01$)',
    'all_0.1': 'All groups ($\\mu = 0.1$)',
    'all_1.0': 'All groups ($\\mu = 1.0$)',
    'all_10.0': 'All groups ($\\mu = 10.0$)',
    'cons_only': 'Consumption',
    'prod_only': 'Production',
    'inter_only': 'Intermediary',
    'info_only': 'Information',
    'demand_only': 'Demand systems',
    'vol_only': 'Volatility',
    'behav_only': 'Behavioral',
    'macro_only': 'Macro-finance',
    'cons_inter': 'Consumption + Intermediary',
    'top4': 'Top 4 groups',
    'no_cons': 'No consumption',
    'no_prod': 'No production',
    'no_inter': 'No intermediary',
    'no_behav': 'No behavioral',
}

# Map multiplier keys to readable names (supports both old restriction-level
# and new group-level keys from Julia output)
_MULT_DISPLAY = {
    # Group-level keys (from Julia run_estimation_julia.jl)
    'consumption': 'Consumption',
    'production': 'Production',
    'intermediary': 'Intermediary',
    'information': 'Information',
    'demand': 'Demand',
    'volatility': 'Volatility',
    'behavioral': 'Behavioral',
    'macro': 'Macro-finance',
    # Restriction-level keys (from Python run_cv_estimation.py)
    'invest_mono': 'Investment',
    'profit_mono': 'Profitability',
    'leverage_effect': 'Leverage',
    'roa_mono': 'ROA',
    'gp_mono': 'Gross profit',
    'bm_mono': 'Book-to-market',
    'mom_mono': 'Momentum',
    'rev_mono': 'Reversal',
    'size_mono': 'Size',
    'vol_mono': 'Volatility',
}


def _period_str(start: int, end: int) -> str:
    """Format yyyymm integers as 'YYYY--YYYY'."""
    y0 = start // 100
    y1 = end // 100
    return f'{y0}--{y1}'


def generate(output_path: str = 'paper/tables/table_11.tex') -> str:
    """Generate Table 11 and write to output_path."""
    json_path = Path('output/cv_window_results.json')

    if json_path.exists():
        with open(json_path) as f:
            windows = json.load(f)
    else:
        windows = []

    lines = []
    lines.append(r'\begin{table}[H]')
    lines.append(r'\centering')
    lines.append(r'\caption{Temporal Variation in Optimal Theory Family}')
    lines.append(r'\label{tab:theory_ranking}')
    lines.append(r'\small')
    lines.append(r'\begin{tabular}{llll}')
    lines.append(r'\toprule')
    lines.append(r'OOS Period & Best Theory Family & Top Restrictions & Val.\ MSE gain (\%) \\')
    lines.append(r'\midrule')

    if not windows:
        lines.append(r'--- & --- & --- & --- \\')
    else:
        for w in windows:
            period = _period_str(w['test_start'], w['test_end'])
            config = w.get('best_config', '---')
            display_config = _CONFIG_DISPLAY.get(config, config)

            # Top restrictions from top_multipliers
            top_mults = w.get('top_multipliers', {})
            top_names = [_MULT_DISPLAY.get(k, k) for k in list(top_mults.keys())[:3]]
            top_str = ', '.join(top_names) if top_names else '---'

            # Val MSE gain %
            krr_mse = w.get('krr_val_mse', 0)
            best_mse = w.get('best_val_mse', 0)
            if krr_mse > 0 and best_mse > 0:
                gain = (krr_mse - best_mse) / krr_mse * 100
                gain_str = f'{gain:.3f}'
            else:
                gain_str = '---'

            lines.append(f'{period}  & {display_config} & {top_str} & {gain_str} \\\\')

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    # Notes
    lines.append(r'\begin{minipage}{\textwidth}')
    lines.append(r'\vspace{4pt}')
    lines.append(r'\footnotesize')
    lines.append(
        r"\textit{Notes:} Each row reports the best-performing $\mu$ configuration "
        r"for the indicated test year, selected by coordinate descent on the "
        r"12-year validation sample. Val.\ MSE gain is the percentage reduction "
        r"in validation MSE relative to standard KRR ($\mu_j = 0$ for all $j$). "
        r"The evaluation follows the rolling three-way split of "
        r"\citet{gu2020empirical} with annual rebalancing."
    )
    lines.append(r'\end{minipage}')
    lines.append(r'\end{table}')

    tex = '\n'.join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(tex, encoding='utf-8')
    return output_path
