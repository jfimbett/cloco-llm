"""
Generate Figure: Temporal Evolution of Theory Family Importance.

Reads output/cv_window_results.json and produces a figure showing
how the optimal μ_g for each theory family varies across test years.

Two panels:
  (a) Stacked area chart of normalized μ shares
  (b) Heatmap of raw μ values (log scale)

Outputs: paper/figures/theory_importance.pdf
"""
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path


GROUP_ORDER = [
    'consumption', 'production', 'intermediary', 'information',
    'demand', 'volatility', 'behavioral', 'macro',
]

GROUP_COLORS = {
    'consumption': '#1f77b4',
    'production': '#ff7f0e',
    'intermediary': '#2ca02c',
    'information': '#d62728',
    'demand': '#9467bd',
    'volatility': '#8c564b',
    'behavioral': '#e377c2',
    'macro': '#7f7f7f',
}

GROUP_LABELS = {
    'consumption': 'Consumption',
    'production': 'Production',
    'intermediary': 'Intermediary',
    'information': 'Information',
    'demand': 'Demand',
    'volatility': 'Volatility',
    'behavioral': 'Behavioral',
    'macro': 'Macro-finance',
}


def generate(output_path: str = 'paper/figures/theory_importance.pdf') -> str:
    """Generate the theory importance figure."""
    json_path = Path('output/cv_window_results.json')
    if not json_path.exists():
        print(f'  [SKIP] {json_path} not found — run estimation first')
        return ''

    with open(json_path) as f:
        windows = json.load(f)

    if not windows:
        print('  [SKIP] No window results')
        return ''

    # Extract years and μ values
    years = []
    mu_matrix = {g: [] for g in GROUP_ORDER}

    for w in sorted(windows, key=lambda x: x.get('test_year', 0)):
        year = w.get('test_year', w.get('test_start', 0) // 100)
        mu_groups = w.get('mu_groups', {})
        years.append(year)
        for g in GROUP_ORDER:
            mu_matrix[g].append(mu_groups.get(g, 0.0))

    years = np.array(years)
    n_windows = len(years)

    if n_windows < 2:
        print('  [SKIP] Need at least 2 windows')
        return ''

    # Build matrix (n_groups × n_windows)
    mu_raw = np.array([mu_matrix[g] for g in GROUP_ORDER])  # (8, T)

    # ── Figure with two panels ──
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), height_ratios=[1.2, 1],
                                     sharex=True, gridspec_kw={'hspace': 0.08})

    # ── Panel (a): Stacked area of normalized μ shares ──
    mu_total = mu_raw.sum(axis=0)
    mu_total[mu_total == 0] = 1.0  # avoid division by zero
    mu_share = mu_raw / mu_total  # (8, T)

    colors = [GROUP_COLORS[g] for g in GROUP_ORDER]
    labels = [GROUP_LABELS[g] for g in GROUP_ORDER]

    ax1.stackplot(years, mu_share, labels=labels, colors=colors, alpha=0.85)
    ax1.set_ylabel('Share of total $\\mu$')
    ax1.set_ylim(0, 1)
    ax1.set_title('(a) Theory family importance over time (normalized)')
    ax1.legend(loc='center left', bbox_to_anchor=(1.01, 0.5), fontsize=8)

    # Shade NBER recessions (approximate)
    for start, end_ in [(1990, 1991), (2001, 2001), (2007, 2009), (2020, 2020)]:
        if start >= years[0] and start <= years[-1]:
            ax1.axvspan(start, end_ + 1, alpha=0.15, color='grey')
            ax2.axvspan(start, end_ + 1, alpha=0.15, color='grey')

    # ── Panel (b): Heatmap of raw μ values ──
    mu_display = mu_raw.copy()
    mu_display[mu_display == 0] = np.nan  # NaN for zero (will show as white)

    im = ax2.imshow(mu_display, aspect='auto', cmap='YlOrRd',
                     norm=mcolors.LogNorm(vmin=1e-4, vmax=10),
                     extent=[years[0]-0.5, years[-1]+0.5, len(GROUP_ORDER)-0.5, -0.5])
    ax2.set_yticks(range(len(GROUP_ORDER)))
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.set_xlabel('Test year')
    ax2.set_title('(b) Raw $\\mu_g$ values (log scale; white = inactive)')

    cbar = fig.colorbar(im, ax=ax2, shrink=0.8, pad=0.12)
    cbar.set_label('$\\mu_g$')

    plt.tight_layout()

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches='tight', dpi=150)
    plt.close(fig)
    print(f'  -> {output_path}')
    return output_path


if __name__ == '__main__':
    generate()
