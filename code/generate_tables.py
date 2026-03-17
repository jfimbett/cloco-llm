"""
CLI entry point for generating LaTeX tables from estimation outputs.

Usage:
    python -m code.generate_tables           # all numerical tables
    python -m code.generate_tables --table 1  # just Table 1
    python -m code.generate_tables --table 10 # just Table 10
"""
import argparse
from pathlib import Path

from code.tables.summary_stats import generate as gen_table1
from code.tables.oos_performance import generate as gen_table10
from code.tables.theory_ranking import generate as gen_table11
from code.tables.mu_significance import generate as gen_table12
from code.tables.dm_pairwise import generate as gen_table_dm
from code.figures.theory_importance import generate as gen_fig_theory


_GENERATORS = {
    1: ('Table 1: Summary Statistics', gen_table1),
    10: ('Table 10: OOS Performance', gen_table10),
    11: ('Table 11: Theory Ranking', gen_table11),
    12: ('Table 12: Per-Window μ Significance', gen_table12),
    'dm': ('Table: Pairwise DM Tests', gen_table_dm),
    'fig': ('Figure: Theory Importance', gen_fig_theory),
}


def main():
    parser = argparse.ArgumentParser(description='Generate numerical LaTeX tables and figures')
    parser.add_argument('--table', default=None,
                        help='Generate a specific item (1, 10, 11, 12, or fig). Default: all.')
    args = parser.parse_args()

    Path('paper/tables').mkdir(parents=True, exist_ok=True)
    Path('paper/figures').mkdir(parents=True, exist_ok=True)

    if args.table is not None:
        # Try int first, then string
        try:
            key = int(args.table)
        except ValueError:
            key = args.table
        if key not in _GENERATORS:
            print(f'Unknown item {key}. Available: {list(_GENERATORS.keys())}')
            return
        items = {key: _GENERATORS[key]}
    else:
        items = _GENERATORS

    for key, (desc, gen_fn) in items.items():
        print(f'Generating {desc}...')
        path = gen_fn()
        if path:
            print(f'  -> {path}')

    print('Done.')


if __name__ == '__main__':
    main()
