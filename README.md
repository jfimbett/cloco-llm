# Theories as Regularizers: Theory-Informed Kernel Ridge Regression for Asset Pricing

> **Code, data pipeline, and paper for "Theories as Regularizers" — embedding economic theory into nonparametric return prediction via structured penalty functions in a kernel ridge regression framework.**

[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai/code)
[![Julia](https://img.shields.io/badge/Julia-1.10+-9558B2?logo=julia)](https://julialang.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)

---

## Paper

**Theories as Regularizers: Embedding Economic Structure into Nonparametric Return Prediction**

*Juan F. Imbet* — Paris Dauphine University – PSL

**Abstract:** Machine learning methods for cross-sectional return prediction typically ignore economic theory, treating it as a source of features rather than structure. We propose Theory-Informed Kernel Ridge Regression (Theory-KRR), which embeds 56 structural restrictions from 8 theory families — consumption, production, intermediary, information, demand, volatility, behavioral, and macro — as penalty functions in a reproducing kernel Hilbert space. Each restriction penalizes deviations from theory-implied relationships (Euler equations, monotonicity, sign restrictions) with group-specific multipliers selected via coordinate descent cross-validation. The method nests plain KRR (all penalties off) and progressively activates theory channels that improve out-of-sample prediction.

---

## Quick Start

### Prerequisites

- **Julia 1.10+** with packages: `CUDA`, `Optim`, `Parquet2`, `DataFrames`, `GLMNet`, `ProgressMeter`
- **Python 3.10+** for data pipeline and table generation
- **LaTeX** (TeX Live / MiKTeX) for paper compilation

### Run

```bash
# 1. Build the data panel (downloads public data, merges with WRDS extracts)
python -m code.data_pipeline.download_public_data
python -m code.data_pipeline.build_panel

# 2. Run estimation (TEST_MODE=true in .env for fast iteration)
julia --threads=auto code/run_estimation_julia.jl

# 3. Generate tables and figures
python -m code.generate_tables

# 4. Compile paper
latexmk -pdf -cd paper/main.tex
```

### Configuration

All settings live in `.env` (gitignored):

```bash
TEST_MODE=true                   # true: subsample data for fast iteration
TEST_MAX_STOCKS_PER_MONTH=200    # stocks per month in test mode
TEST_MAX_ROLLING_WINDOWS=10      # OOS windows in test mode (last N years)
USE_GPU=true                     # GPU acceleration for kernel computation
```

---

## Method Overview

### Theory-KRR Objective

The estimator minimizes a penalized loss in the Nystrom-approximated RKHS:

```
L(β) = ||y - Zβ||² + nλ||β||² + Σⱼ μⱼ Cⱼ(Zβ)
```

where `Z` is the Nystrom feature matrix (n × m), `λ` is the statistical regularization, and each `Cⱼ` is a structural penalty derived from economic theory with group multiplier `μⱼ`.

### 56 Restrictions across 8 Theory Families

| Family | # | Examples |
|--------|---|---------|
| Consumption | 13 | Euler equations (CAPM, habit, LRR, Epstein-Zin), consumption-beta pricing |
| Production | 10 | Investment/profitability monotonicity, q-theory, asset growth |
| Intermediary | 8 | HKM capital ratio, intermediary Euler, sentiment, leverage cycle |
| Information | 6 | Forecast dispersion, ambiguity aversion, rational inattention |
| Demand | 6 | Market clearing, demand elasticity, inelastic markets, asset embeddings |
| Volatility | 2 | VIX premium, realized volatility |
| Behavioral | 6 | Momentum, reversal, disposition effect, overreaction |
| Macro | 5 | Term spread, default spread, risk-free rate, macro factor R² |

### Estimation Pipeline

1. **GKX-style 3-way split**: Train | Validation (12yr) | Test (1yr), annual rebalancing, OOS from 1987
2. **Managed portfolios**: Quintile-sorted portfolios on 7 characteristics (+ market EW) — ~36 per month
3. **Nystrom approximation** (m=500): Reduces n×n kernel to n×m features — O(nm²) instead of O(n³)
4. **λ cross-validation**: Search λ ∈ {1e-6, ..., 1e-2} via plain KRR validation MSE
5. **μ coordinate descent**: For each of 8 groups, search μ via L-BFGS eval on validation set
6. **Final fit**: L-BFGS on train+val with selected (λ, μ), predict on test year
7. **Horse race**: Compare against historical mean, OLS, Ridge, Lasso, Elastic Net, plain KRR

---

## Repository Structure

```
theories-as-regularizers/
├── paper/
│   ├── main.tex                    # Paper (single source of truth)
│   ├── sections/                   # Introduction, framework, empirical, estimation, results
│   ├── tables/                     # Auto-generated LaTeX tables
│   ├── figures/                    # Generated figures
│   ├── appendix/                   # Proofs, computational details
│   └── references.bib
│
├── code/
│   ├── run_estimation_julia.jl     # Main estimation: GKX protocol, all models, OOS evaluation
│   ├── restrictions_julia.jl       # 56 structural penalties with analytical gradients
│   ├── generate_tables.py          # LaTeX table generation from estimation output
│   ├── data_pipeline/
│   │   ├── download_public_data.py # Downloads FF factors, NIPA, FRED, HKM, VIX, etc.
│   │   └── build_panel.py          # Merges CRSP/Compustat/JKP into monthly panel
│   ├── tables/                     # Per-table generators (summary stats, OOS, theory ranking)
│   ├── figures/                    # Figure generators (theory importance over time)
│   └── utils/
│       └── data_loader.py          # Panel loader with TEST_MODE subsampling
│
├── data/
│   ├── raw/                        # Downloaded public datasets
│   └── processed/
│       └── panel_monthly.parquet   # Analysis-ready panel (~1.8M rows × 277 cols)
│
├── output/                         # Estimation outputs
│   ├── cv_results.csv              # Aggregate OOS metrics (R²_OOS, SR, DM) per model
│   └── cv_window_results.json      # Per-window results (μ values, MSEs, configs)
│
├── .env                            # Configuration (TEST_MODE, GPU, API keys)
├── CLAUDE.md                       # Claude Code project instructions
└── quality_reports/                # Session logs, audit reports
```

---

## Data

### Panel Construction

The monthly panel merges:
- **CRSP** monthly stock file (returns, prices, shares outstanding)
- **Compustat** annual/quarterly (fundamentals: assets, investment, profitability)
- **JKP firm characteristics** (pre-computed characteristics from Jensen-Kelly-Pedersen)
- **Kenneth French** factors and risk-free rate
- **NIPA** consumption (nondurable + services, monthly)
- **FRED** macro variables (term spread, default spread, T-bill, TED, breakeven inflation)
- **He-Kelly-Manela** intermediary capital ratio and risk factor
- **Baker-Wurgler** investor sentiment
- **Lettau-Ludvigson** cay (consumption-wealth ratio)
- **CBOE** VIX and realized variance

Final panel: ~1.8M stock-months, 228 ranked characteristics, 37 macro variables.

### WRDS Access Required

CRSP, Compustat, and JKP characteristics require [WRDS](https://wrds-www.wharton.upenn.edu/) access. All other data sources are public and downloaded automatically.

---

## Key Design Decisions

- **Monthly aggregation for time-series penalties**: Macro variables are constant within each month across managed portfolios. Penalties aggregate predicted returns to monthly means before computing correlations/Euler errors, avoiding ~35x gradient dilution.
- **L-BFGS evaluation** (not Newton approximation): Each candidate μ is evaluated by running 15 L-BFGS iterations warm-started from the KRR solution — true objective, no stale gradients.
- **Nystrom always on**: Even in test mode, the m×m approximation is faster than the full n×n kernel.
- **Julia for estimation**: JIT compilation + native threads + CUDA.jl for GPU kernel computation.

---

## Lineage

The research workflow infrastructure is built on [**clo-author**](https://hsantanna88.github.io/clo-author/) by Hugo Sant'Anna, itself a fork of [**claude-code-my-workflow**](https://github.com/pedrohcgs/claude-code-my-workflow) by Pedro H.C. Sant'Anna (Emory University). Extended for financial economics research with project-type-aware pipelines, theory/structural agents, and field-specific scoring.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
