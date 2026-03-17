"""
Generate Figures: Temporal Evolution of Theory Family Importance.

Reads output/cv_window_results.json and produces two separate figures:
  (a) Stacked area chart of normalized μ shares → theory_importance_area.png
  (b) Heatmap of raw μ values (log scale) → theory_importance_heatmap.png
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

# NBER recession dates (approximate)
RECESSIONS = [(1990, 1991), (2001, 2001), (2007, 2009), (2020, 2020)]


def _load_data():
    """Load window results and return (years, mu_raw) or None."""
    json_path = Path('output/cv_window_results.json')
    if not json_path.exists():
        print(f'  [SKIP] {json_path} not found — run estimation first')
        return None

    with open(json_path) as f:
        windows = json.load(f)

    if not windows or len(windows) < 2:
        print('  [SKIP] Need at least 2 windows')
        return None

    years = []
    mu_matrix = {g: [] for g in GROUP_ORDER}
    for w in sorted(windows, key=lambda x: x.get('test_year', 0)):
        year = w.get('test_year', w.get('test_start', 0) // 100)
        mu_groups = w.get('mu_groups', {})
        years.append(year)
        for g in GROUP_ORDER:
            mu_matrix[g].append(mu_groups.get(g, 0.0))

    years = np.array(years)
    mu_raw = np.array([mu_matrix[g] for g in GROUP_ORDER])
    return years, mu_raw


def generate_stacked_area(output_path: str = 'paper/figures/theory_importance_area.png') -> str:
    """Generate stacked area chart of normalized μ shares."""
    result = _load_data()
    if result is None:
        return ''
    years, mu_raw = result

    mu_total = mu_raw.sum(axis=0)
    mu_total[mu_total == 0] = 1.0
    mu_share = mu_raw / mu_total

    colors = [GROUP_COLORS[g] for g in GROUP_ORDER]
    labels = [GROUP_LABELS[g] for g in GROUP_ORDER]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.stackplot(years, mu_share, labels=labels, colors=colors, alpha=0.85)
    ax.set_ylabel('Share of total $\\mu$')
    ax.set_ylim(0, 1)
    ax.set_xlabel('Test year')
    ax.set_title('Theory family importance over time (normalized)')
    ax.legend(loc='center left', bbox_to_anchor=(1.01, 0.5), fontsize=8)

    for start, end_ in RECESSIONS:
        if start >= years[0] and start <= years[-1]:
            ax.axvspan(start, end_ + 1, alpha=0.15, color='grey')

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f'  -> {output_path}')
    return output_path


def generate_heatmap(output_path: str = 'paper/figures/theory_importance_heatmap.png') -> str:
    """Generate heatmap of raw μ values on log scale."""
    result = _load_data()
    if result is None:
        return ''
    years, mu_raw = result

    labels = [GROUP_LABELS[g] for g in GROUP_ORDER]
    mu_display = mu_raw.copy()
    mu_display[mu_display == 0] = np.nan

    fig, ax = plt.subplots(figsize=(10, 3.5))
    im = ax.imshow(mu_display, aspect='auto', cmap='YlOrRd',
                   norm=mcolors.LogNorm(vmin=1e-4, vmax=10),
                   extent=[years[0]-0.5, years[-1]+0.5, len(GROUP_ORDER)-0.5, -0.5])
    ax.set_yticks(range(len(GROUP_ORDER)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Test year')
    ax.set_title('Raw $\\mu_g$ values (log scale; white = inactive)')

    for start, end_ in RECESSIONS:
        if start >= years[0] and start <= years[-1]:
            ax.axvspan(start, end_ + 1, alpha=0.15, color='grey')

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label('$\\mu_g$')

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f'  -> {output_path}')
    return output_path


def generate(output_path: str = None) -> str:
    """Generate both figures. Returns path of the area chart."""
    p1 = generate_stacked_area()
    p2 = generate_heatmap()
    return p1 or p2


if __name__ == '__main__':
    generate()
