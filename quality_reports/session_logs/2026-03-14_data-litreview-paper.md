# Session Log — 2026-03-14: Data Pipeline, Literature Review, Paper Setup

**Goal:** Download public datasets, conduct literature review, set up paper structure.
**Status:** IN PROGRESS (ready to commit)

---

## Changes Made

### 1. Data Pipeline
- Created `code/data_pipeline/download_public_data.py` — downloads 7 public datasets
- Downloaded to `data/raw/`: ff_factors_monthly.csv, nipa_consumption.csv, fred_macro.csv, hkm_intermediary.csv, ebp.csv, welch_goyal.csv, vix.csv
- Updated `data/DATA_SOURCES.md` with download status markers and script reference
- Note: Lettau-Ludvigson cay and Baker-Wurgler sentiment need manual download

### 2. Literature Review (Librarian + Editor)
- Launched academic-librarian: 25 new papers across 10 gap strands
- Launched academic-editor (Lit Critic): scored 82/100 — PASS
- Outputs saved to `quality_reports/literature/theories-as-regularizers/`
- Key scooping risks: Chen-Cheng-Liu-Tang (2026), Bryzgalova-Huang-Julliard (2023)

### 3. Paper Updates
- **Title:** Changed to "Theories as Regularizers"
- **Abstract:** Rewritten — no math, single-spaced, with medskip before JEL
- **Authors:** Reordered alphabetically (Andriollo, Imbet) everywhere
- **Introduction:** Expanded literature paragraphs — explicit differentiation from Chen et al. (2026) and Bryzgalova et al. (2023); added factor zoo, penalized GMM, RKHS foundations
- **References:** Expanded from ~80 to 124 entries (gap-filling + editor-flagged)
- **All citations:** Converted inline (Author, Year) to \citep/\citet across restrictions.tex, introduction.tex, empirical.tex, results.tex
- **Missing bib entries added:** Leland (1968), Carr-Wu (2009), Duffie-Kan (1996), Xiong-Yan (2010), Mackowiak-Wiederholt (2009), Van Nieuwerburgh-Veldkamp (2010), Koijen-Richmond-Yogo (2024), Pastor-Veronesi (2009), David (2008)

### 4. Compilation
- Paper compiles cleanly (latexmk -pdf)
- Only warnings: 4 undefined figure references (figures not yet created)

---

## Decisions
- Title "Theories as Regularizers" chosen over alternatives — user preference
- Authors alphabetical (Andriollo before Imbet) — user request
- Abstract: no math notation, "sexy" language — user request
- data/raw/ CSVs (~840K total) are small enough to commit

### 5. WRDS Data Downloads (2026-03-15)
- **CRSP Monthly:** `crsp_monthly.csv` — 5.16M rows, 38,843 permnos, 1925-2024. Columns uppercase. RET/RETX have non-numeric codes (~3.8%).
- **Compustat Annual:** `compustat_annual.csv` — 525K rows, 40,678 gvkeys, 1950-2026. Active+Inactive (64% inactive — good for survivorship). Filters: C/INDL/STD/USD.
- **CCM Link:** `ccm_link.csv` — 32,762 rows, LC+LU links only. LINKENDDT='E' means active.
- **Compustat Quarterly:** `compustat_quarterly.csv` — 1.87M rows, 39,568 gvkeys. Fiscal quarters.
- **JKP Firm Characteristics:** `firm_characteristics.csv` — 5.42M rows, 209 signed characteristics, via openassetpricing Python package. Missing Price/Size/STreversal (build from CRSP).
- Created `data/raw/README.md` with detailed notes on every file (column names, quirks, missing values).

### 6. Still Missing
- **Lettau-Ludvigson cay:** sydneyludvigson.com returning 404 — user looking for it
- **Baker-Wurgler Sentiment:** Wurgler NYU page also 404
- **OptionMetrics:** Low priority for V1 (option-implied restrictions)

---

## Decisions
- Title "Theories as Regularizers" chosen over alternatives — user preference
- Authors alphabetical (Andriollo before Imbet) — user request
- Abstract: no math notation, "sexy" language — user request
- data/raw/ CSVs (~840K total for public data) are small enough to commit
- WRDS data: selected Active+Inactive for survivorship; Fiscal quarters for Compustat Quarterly
- JKP characteristics downloaded via openassetpricing package (skipped WRDS-dependent Price/Size/STreversal)
- cay and sentiment: non-blocking — only used in 1-2 of 60 restrictions

### 7. Monthly Panel Build (2026-03-15)
- Created `code/data_pipeline/build_panel.py` — 10 functions, ~600 lines
- Merges: CRSP monthly → characteristics (chunked 8.5GB) → Compustat annual/quarterly via CCM (merge_asof with 6-mo/PIT lag) → 9 macro datasets → realized variance (chunked 4GB daily)
- Filters: common stocks (shrcd 10/11), major exchanges, price ≥ $5, drop utilities (SIC 4900-4999) and financials (6000-6999), min 15 non-missing characteristics
- Cross-sectional rank all 223 characteristics to [0,1] per month
- Fixed 3 bugs during build: (1) merge_asof requires globally sorted on-key — split NaN-gvkey rows before merge; (2) int32/int64 dtype mismatch on yyyymm after concat; (3) duplicate roaq column from chars + Compustat quarterly — coalesced into single column
- **Output:** `data/processed/panel_monthly.parquet` — 1,778,850 rows × 262 cols, 18,066 permnos, 726 months (196307–202312), avg 2,450 stocks/month, 1.89 GB
- All verification checks pass: no duplicates, chars in [0,1], no financials/utilities
- cay and sentiment data successfully included (were downloaded between sessions)

---

## Decisions
- Chunked I/O for characteristics (500K rows) and CRSP daily (5M rows) — rest fits in memory
- GKX convention: Compustat annual available 6 months after datadate; quarterly uses rdq (point-in-time)
- roaq coalesced: prefer characteristics file version, fill gaps from Compustat quarterly (83.5% fill rate)
- Industry filter applied after Compustat merge (need SIC codes from Compustat)
- Ranking done after all filters so percentiles reflect actual investment universe

### 8. Tables/Figures After References + Appendix Merge (2026-03-16)
- Created `paper/tables_and_figures.tex` — all 12 tables collected after references
- Extracted tables from `restrictions.tex` (8), `results.tex` (3), `empirical.tex` (1)
- Removed "[Figure 3 about here]" placeholder from results.tex
- Changed float specifiers from `[H]` to `[h!]`, removed `\usepackage{float}`
- Merged appendix: `proofs.tex` → `appendix/appendix.tex`; deleted placeholder files
- Updated `main.tex` input order: body → references → tables_and_figures → appendix
- Compiles cleanly: 73 pages, only 2 undefined refs (fig:bias_variance — not yet created)

### 9. GKX Table Format Gap Analysis (2026-03-16)
- Read Gu-Kelly-Xiu (2020) Tables 1-5 and Figures 4-5 from `master_supporting_docs/`
- Identified 3 missing table types vs. GKX:
  1. **GKX-style model horse race** — models as columns, multiple metrics (R²_OOS, Sharpe, CER), subsamples as rows. Our `tab:oos_performance` is transposed and single-metric.
  2. **Pairwise DM test matrix** — lower-triangular, all model pairs. We only have DM vs. historical mean.
  3. **Restriction importance table** — analogous to GKX Figure 5 / Table 4 for "which variables matter". Our `tab:theory_ranking` shows winning family per period but not a structured importance ranking.
- These are results tables — LaTeX shells can be designed now, numbers come from estimation.

### 10. TEST_MODE Implementation via .env (2026-03-16)
- Created `.env` with `TEST_MODE=true`, `TEST_MAX_STOCKS_PER_MONTH=200`, `TEST_MAX_ROLLING_WINDOWS=3`
- Created `code/config.py` — reads `.env`, exports typed constants (no external dependencies)
- Wired into `code/utils/data_loader.py` — `load_panel()` subsamples to 200 stocks/month
- Wired into all 3 estimation scripts (`run_estimation.py`, `run_cv_estimation.py`, `run_fast_estimation.py`) — caps rolling windows to 3
- `.env` already in `.gitignore`
- Updated `CLAUDE.md` to reference `.env` instead of inline `TEST_MODE=true`
- Verified: `python -c "from code.config import TEST_MODE; print(TEST_MODE)"` → `True`

---

## Decisions
- `.env` approach chosen over dotenv package — zero dependencies, simple key=value parsing
- TEST_MODE subsamples stocks (200/month) AND limits windows (3) — both needed for speed
- `os.environ.setdefault` used so env vars can be overridden from shell if needed
- GKX-style tables deferred until estimation pipeline produces the numbers

### 11. Auto-Generated LaTeX Tables Pipeline (2026-03-16)
- Created `code/tables/` module with 4 generators: `summary_stats.py`, `oos_performance.py`, `theory_ranking.py`, `subsample_analysis.py`
- Created `code/generate_tables.py` — CLI entry point (`python -m code.generate_tables [--table N]`)
- Tables 1, 10, 11, 12 now auto-generated from data/output files; Tables 2–9 stay hardcoded (theory catalogs)
- Modified `paper/tables_and_figures.tex` — replaced 4 hardcoded blocks with `\input{tables/table_N}`
- Created `paper/TABLE_REGISTRY.md` documenting script→table mapping
- Table 1 reworked: now loads raw (unranked) characteristics from source CSVs (Compustat, CRSP, JKP firm_characteristics) — BM, Mom12m, reversal, I/K, ROE, AG, GP show actual values winsorized at 1st/99th
- Reduced table size: `\footnotesize`, `\setlength{\tabcolsep}{4pt}`, notes in `\scriptsize\setstretch{0.85}`
- Macro variables scale correctly (mktrf, rf ×100 for %)
- Paper compiles cleanly with generated tables

### 12. Restriction Variable Coverage Audit (2026-03-16)
- Cross-referenced all variables in Tables 2–9 restrictions vs panel columns
- **Available (20+):** cons_growth, mktrf, ik, roe, leverage, CF, hire, rd_intensity, hkm_capital_ratio, hkm_risk_factor, sentiment, ForecastDispersion, ShortInterest, vix, realized_var, Mom12m, streversal, term_spread, cay, ebp
- **Missing (18):** TED spread, BAB factor, AEM leverage, capital flows, margin proxy, inflation risk premium, monetary policy surprise, CGO, salience, information flow, SGA/K, K/debt, dividends, expected growth, Delta Flow, search intensity, past avg return, primary dealer eta
- **Quick wins (already in panel):** DivYieldST→dividends, fgr5yrLag→expected growth, xsga in Compustat→SGA/K, ppent/(dlc+dltt)→K/debt
- **Download queue started:** TED spread (FRED) first, then BAB (AQR), AEM leverage, TIPS spread

---

## Decisions
- Raw characteristics for Table 1 instead of ranked — P5/P50/P95 of ranked values are uninformative
- Winsorize Compustat ratios at 1/99 percentile for summary stats display
- Characteristic N comes from raw source files (full data), not TEST_MODE subsample
- TED spread prioritized as first missing-variable download (single FRED series)

### 13. Missing Restriction Variables — Downloads and Construction (2026-03-17)
- **Downloaded 4 new macro series:**
  - TED spread (FRED TEDRATE, 1986–2022, daily→monthly)
  - BAB factor (AQR data library, 1930–2025, USA column)
  - AEM intermediary leverage (FRED Flow of Funds: BOGZ1FL664090005Q / BOGZ1FL665080003Q, quarterly)
  - Breakeven inflation (FRED T10YIEM, 2003–present, monthly)
- **Downloaded Q Factors** from WRDS Macro Finance Society (HXZ `r_eg` expected growth, 1967–2019)
- **Constructed monetary policy surprise** from AR(1) residual of Fed Funds rate changes (FRED FEDFUNDS)
- **Downloaded equity flows** (FRED HNOCESQ027S, household equity transactions, quarterly)
- **Constructed 5 derived variables in `build_panel.py`:**
  - `k_debt` = PPE / total debt (Compustat)
  - `sga_at` = SGA / total assets (Compustat)
  - `past_avg_ret` = 36-month rolling mean return (CRSP)
  - `salience` = |R_i - R_m| / σ_cross (constructed)
  - `cgo` = capital gains overhang via EWMA reference price (constructed)
- **Fixed NIPA consumption:** replaced quarterly PCESV with monthly PCES — cons_growth now correct (0.19%/mo vs old 0.56%)
- **Upgraded FRED download helper** to use API key from `.env`
- Confirmed 3 variables already in panel: `fgr5yrLag` (EG), `DivYieldST` (div), `hkm_risk_factor` (dealer eta)
- Confirmed 3 proxy variables: `ChNAnalyst` (info flow), `BidAskSpread` (search), `vix` (margin)
- All 56 restrictions now have data coverage

### 14. Restriction Audit Skill + Full Audit (2026-03-17)
- Created `/audit-restrictions` skill at `.claude/skills/audit-restrictions/SKILL.md`
  - Modes: `report` (audit only) or `fix` (audit + apply corrections)
  - 6-phase workflow: extract restrictions → check data → check docs → check summary stats → report → fix
- Ran `/audit-restrictions fix`:
  - Report saved to `quality_reports/restriction_audit.md`
  - Added documentation paragraph to `paper/sections/empirical.tex` covering all 14 undocumented variables
  - Updated data availability paragraph with new variable coverage periods
  - Added 4 firm chars to Table 1 Panel A (leverage, R&D, SGA/K, K/debt)
  - Added 3 macro vars to Table 1 Panel B (TED, BAB, breakeven inflation)

### 15. Panel Rebuild (2026-03-17)
- Rebuilt panel with `build_panel.py --force`
- **New panel:** 1,778,856 rows × 277 columns (was 262), 1.96 GB
- 228 ranked characteristics (was 223), 37 macro variables (was ~30)
- New columns: k_debt, sga_at, past_avg_ret, salience, cgo, ted_spread, bab, aem_leverage, aem_leverage_change, equity_flow, breakeven_infl, mp_surprise, r_ia, r_roe, r_eg

### 16. Table 1 Split and Filtering Fix (2026-03-17)
- Split Table 1 into **Table 1a** (firm chars + coverage) and **Table 1b** (macro variables)
- Both tables: `\scriptsize`, `\tabcolsep{3pt}`, `\arraystretch{0.9}` for compact layout
- Table 1b uses tighter 4-column format (T, Mean, Std, AC1)
- Fixed observation count inconsistency: raw chars now filtered to panel universe (permno/gvkey) so N values are consistent across variables
- Paper compiles cleanly

---

## Decisions
- Raw characteristics for Table 1 instead of ranked — P5/P50/P95 of ranked values are uninformative
- Winsorize Compustat ratios at 1/99 percentile for summary stats display
- NIPA: PCESV (quarterly) → PCES (monthly) fixes consumption growth to correct 0.19%/mo
- Monetary policy surprise: AR(1) residual proxy (crude but covers full sample; note in paper)
- Margin requirement dropped as separate variable — redundant with TED + VIX
- 4 remaining variables deferred: monetary policy (proper GSS), capital flows (ICI), info flow (IBES), search (OTC)
- Table 1 split at 11 firm chars + 13 macro vars — each table fits on one page

### 17. Writing Style Fix (2026-03-17)
- Removed 29 `\paragraph{}` headers across empirical.tex, estimation.tex, results.tex, framework.tex
- Kept only 3 in estimation.tex (Approach 1/2/3 — genuinely enumerated alternatives)
- Prose now flows with natural transitions instead of bold-header fragments
- Recorded in LESSONS.md: never use `\paragraph{}` in data/results sections

### 18. Bayesian Optimization for μ Selection (2026-03-17)
- Discussed 4 approaches: grid search (current), Bayesian optimization, gradient-based, bilevel
- Rejected bilevel approach (Option 4) — user didn't like the complexity
- Implemented Bayesian optimization via Optuna TPE in `code/run_bayesian_cv.py`
- Key design: each group gets binary on/off + continuous magnitude if on
- GPU-accelerated: kernel computation and KRR baseline on CUDA
- Multicore parallel: grid search with joblib (20 workers), Optuna with n_jobs=8
- Comparison script runs KRR baseline, grid (20 configs), BO (15 trials), BO (30 trials)
- Installed optuna dependency
- Hardware: RTX A6000 (48GB VRAM), 40 CPU cores, 274 GB RAM

### 19. Scalability Analysis (2026-03-17)
- Full data (n=100K): kernel matrix = 80GB per copy, only 1-2 parallel workers feasible
- Solution: Nystrom approximation (m=500) reduces to 400MB per copy, 20 workers = 8GB
- Script designed to auto-switch between full kernel (TEST_MODE) and Nystrom (full data)
- Not yet implemented in run_bayesian_cv.py — deferred until full-data run

---

## Decisions
- Bilevel μ optimization rejected — too complex, unclear speed benefit
- Bayesian optimization (Optuna TPE) chosen for μ selection — 30 trials expected to beat 20-config grid
- Grid search parallelized with joblib (20 workers), Optuna with 8 parallel workers
- All parallel workers use CPU numpy (picklable); GPU reserved for kernel computation + baseline
- `\paragraph{}` banned from data/results sections — lessons recorded
- Nystrom approximation planned for full-data runs (n>10K threshold)

### 20. Julia Implementation + Nystrom (2026-03-17)
- Created `code/run_bayesian_cv.jl` — full Julia port with GPU + threading + Nystrom
- Installed Julia packages: Parquet2, Hyperopt, ProgressMeter (CUDA/Optim/DataFrames already installed)
- Fixed 2 bugs: NamedTuple Symbol keys, Missing→Float64 coercion
- Added progress bars (ProgressMeter) for grid search and BO
- **Nystrom approximation** (m=500): reduces 7560×7560 kernel to 7560×500 features
  - KRR solve: 500×500 Cholesky instead of 7560×7560
  - L-BFGS: operates on 500-dim β, not 7560-dim α
  - Memory: 34MB vs 460MB per kernel
- Test run (3 windows): 11 minutes total, grid search ~60s/config

### 21. Computational Appendix (2026-03-17)
- Added Appendix B to `paper/appendix/appendix.tex`:
  - B.1 Nystrom Approximation — feature map Z, m×m solve, gradient formula, scaling table
  - B.2 Hyperparameter Selection via Bayesian Optimization — TPE, binary+continuous parameterization
  - B.3 Parallelization Strategy — GPU kernel, multi-threaded grid, parallel BO trials, memory analysis
- Hardware specs documented: 40-core CPU, 274GB RAM, RTX A6000 48GB VRAM
- No programming language mentioned per academic convention

### 22. Penalty Bug Diagnosis (2026-03-17)
- Grid search shows 0% gain over KRR — theory penalties not helping
- Root cause: Julia script uses fake `monotonicity_penalty` (random pair sampling) not actual restrictions
- Three problems identified:
  1. Penalty is generic proxy, not the 56 real restrictions
  2. Group→column mapping is arbitrary (group 0→col 1, etc.)
  3. Random sampling makes objective stochastic — L-BFGS can't converge
- Actual Python penalties are **correlation-based**: `max(0, ±corr(f_hat, char))²`
  - Deterministic, smooth, analytical gradient, economically meaningful
  - Example: InvestmentMonotonicity penalizes positive corr(f_hat, I/K) per q-theory
- Need to port real restrictions to Julia for valid comparison

---

## Decisions
- Nystrom used always (not just full data) — even TEST_MODE benefits from 100x speedup
- m=500 landmarks chosen as default — captures 95%+ kernel spectrum
- Julia chosen for estimation speed — JIT + native threads + CUDA.jl
- GKX protocol discussion: our validation is 24mo (vs their 12yr), triennial (vs monthly) rebalancing. With BO+Nystrom, annual rebalancing feasible (~35min TEST_MODE, ~4-6hr full data)

### 23. Julia Restrictions Port (2026-03-17)
- Created `code/restrictions_julia.jl` — 37 restrictions ported 1:1 from Python
  - 7 consumption (Euler CAPM, habit, LRR, EZ, cay, precautionary, cons_growth_mono)
  - 10 production (I/K, ROE, leverage, ROA, GP, AG, R&D, q-theory, capex, BM)
  - 5 intermediary (HKM capital, HKM factor, Euler, sentiment, funding liquidity)
  - 2 information (forecast dispersion, macro uncertainty)
  - 2 demand (elasticity, size)
  - 2 volatility (VIX premium, realized vol)
  - 4 behavioral (momentum, ST reversal, LT reversal, disposition)
  - 5 macro (term spread, default spread, EBP, risk-free rate, macro factor R²)
- Used generic `_corr_penalty` / `_corr_gradient` helpers for most restrictions
- Fixed `_macro_factor_gradient`: replaced O(n²) numerical gradient with analytical O(n)
- Managed portfolio builder now carries 17 extra columns (macro + restriction inputs)

### 24. Coordinate Descent for μ Selection (2026-03-17)
- Replaced Hyperopt.jl random sampler with GLMNet-style coordinate descent
- Per cycle: 8 groups × 16 μ values (0 + 15 log-spaced), parallel across 40 threads
- 3 cycles max with early stopping on convergence
- Results on TEST_MODE (200 stocks, 3 windows):
  - Window 1: production=0.37 + macro=10.0 → 0.072% gain over KRR
  - Window 2: consumption=10.0 + behavioral=0.01 + macro=10.0 → 1.091% gain
  - Window 3: production=10.0 → 0.470% gain
  - Speed: 3-4 seconds per window (vs 45 min with full kernel L-BFGS)

### 25. GKX Protocol Alignment (2026-03-17)
- Updated `run_estimation_julia.jl` (renamed from `run_bayesian_cv.jl`):
  - OOS starts 1987 (was 1983), matching GKX
  - 12-year validation window, separate from training (was 24mo carved out)
  - Annual rebalancing (was triennial) = 37 windows
  - True 3-way split: train < val_start | val | test_year
  - TEST_MODE only limits stocks (200/mo), runs all 37 windows

### 26. Full Model Horse Race (2026-03-17)
- Added 5 baseline models to Julia script (8 total):
  - Historical mean, OLS, Ridge (CV over 20 λ), Lasso (GLMNet), Elastic net (GLMNet)
  - KRR (Nystrom), Random forest (DecisionTree.jl, 300 trees), Theory-KRR
- Installed Julia packages: GLMNet.jl, DecisionTree.jl
- All models use same GKX protocol: fit on train+val, predict on test year

### 27. Output Files for Paper Tables (2026-03-17)
- Added test-set evaluation: re-fit on train+val with selected μ, predict on test
- Accumulate OOS predictions across all 37 windows
- Compute aggregate R²_OOS and DM statistics (Newey-West 6 lags)
- Save `output/cv_results.csv` (all 8 models) and `output/cv_window_results.json`
- Output format matches what Python table generators expect (Tables 10-12)

### 28. Code-Paper Audit Skill (2026-03-17)
- Created `/audit-code-paper` skill at `.claude/skills/audit-code-paper/SKILL.md`
- 12 audit categories: sample split, baselines, kernel, restrictions, penalties, hyperparameter selection, metrics, Nystrom, parallelization, output files, reproducibility, undocumented behavior
- Scoring: PASS=10, PARTIAL=5, FAIL=0, total /120 → percentage

---

## Decisions
- Coordinate descent chosen over Bayesian optimization — no Julia BO library works well, CD is faster and more principled (GLMNet-style)
- Newton step (1 step from KRR warm start) for Theory-KRR eval — avoids L-BFGS entirely, each eval under 0.1s
- GKX protocol adopted: 1987 OOS start, 12yr validation, annual rebalancing
- All 8 baseline models run same protocol for fair comparison
- TEST_MODE keeps all 37 windows (only limits stocks) — ensures full temporal coverage in test runs

### 29. Code-Paper Audit v2 — Score 42→92 (2026-03-17)
- Ran `/audit-code-paper all` twice. Initial score: 42/100 (5 FAILs). After fixes: 92/100 (0 FAILs).
- **Fix 1 (Sample split):** Rewrote Sections 4.3+4.5 — rolling GKX protocol (1987-2023, 12yr val, annual rebalancing)
- **Fix 2 (Baselines):** Added neural network (Flux.jl) — later removed with RF for speed
- **Fix 3 (Restrictions):** Ported 19 missing restrictions from Python → Julia (37→56). All 8 families complete.
- **Fix 4 (Hyperparameters):** Rewrote Section 4.3 + Appendix B.2 — coordinate descent replaces random search/BO
- **Fix 5 (Metrics):** Added Sharpe ratio to Julia + Table 10; removed CER + bootstrap from paper
- **Fix 6 (Output bug):** Fixed undefined variables `test_mse_hm/krr/tikrr` that would crash JSON writing
- **Fix 7 (Paper):** Removed Matern-5/2 claim; replaced L-BFGS description with Newton step equation
- **Fix 8 (Appendix):** GPU Cholesky claim corrected to CPU; BO parallelism → CD parallelism
- Added Friedman et al. (2010) reference for coordinate descent

### 30. Model Simplification + Timing (2026-03-17)
- Removed RF and neural net baselines from code + paper (too slow, not needed for V1)
- 7 models remain: hist_mean, OLS, ridge, lasso, elastic_net, KRR, Theory-KRR
- Added `_timed_fit!()` wrapper — prints per-model wall-clock time for each window
- Fixed Flux/Optim Adam name collision

### 31. Performance Optimization — Eval Cache (2026-03-17)
- Coordinate descent was bottlenecked at 65s/window: 128 evals × 56 gradient computations each
- Created `EvalCache` + `build_eval_cache()`: pre-computes all 56 penalty gradients ONCE per window, projects to per-group Newton directions in β-space
- `eval_config_fast()` replaces `eval_config_nystrom()`: just weighted sums of pre-computed directions + line search. Each eval now microseconds instead of 0.5s
- Expected speedup: 65s → <1s for coordinate descent step

### 32. Theory Importance Figure (2026-03-17)
- Created `code/figures/theory_importance.py` — reads cv_window_results.json
- Two panels: (a) stacked area of normalized μ shares, (b) heatmap of raw μ (log scale)
- NBER recession shading, 8 color-coded theory families
- Added Figure reference in results.tex Section 6.2
- Integrated into `python -m code.generate_tables` pipeline (`--table fig`)

### 33. Julia .env Integration (2026-03-17)
- Julia code was hardcoding `TEST_MODE=true` — now reads from `.env` file
- Added `_read_env()` function parsing key=value pairs, matching Python's config.py
- `.env` currently has `TEST_MODE=false` — next Julia run will use full data

---

## Decisions
- RF + neural net removed from V1 — can add back later, they don't affect the paper's contribution
- Paper baselines: 6 models (5 baselines + KRR) + Theory-KRR = 7 total
- EvalCache pre-computes all penalty gradients once per window — massive speedup
- Figure preferred over table for showing temporal μ evolution (37 windows too many for a table)
- Julia reads .env directly — single source of truth for TEST_MODE across Python and Julia

### 34. Fix Theory-KRR to Beat Plain KRR — 4 Critical Bugs (2026-03-17)
- **Diagnosis:** Theory-KRR consistently underperforms plain KRR in OOS. Three interacting bugs identified:
  1. **Macro penalty dilution (35x):** Managed portfolios have ~36 rows/month. Macro variables (cons_growth, vix, hkm, cay, etc.) are constant within each month. `corr(f_hat, macro_var)` pools across n=7000 portfolio-months but the macro signal lives in T=200 unique months. Gradient divided by n instead of T.
  2. **Newton approximation breaks for large μ:** `eval_config_fast` pre-computes gradient directions at μ=0. Stale when μ>0.
  3. **Objective mismatch:** μ selected via Newton+LOOCV, but final fit uses L-BFGS. Different optimizers = different optima.

- **Fix 1 — Monthly aggregation** (`restrictions_julia.jl`):
  - Added `MonthlyAgg` struct, `_monthly_agg`, `_monthly_var`, `_monthly_grad_to_obs` helpers
  - Added `_ts_corr_penalty`/`_ts_corr_gradient` for time-series correlation penalties
  - Updated ~28 time-series restrictions (all Euler equations, macro correlations) to aggregate f_hat to monthly means
  - Cross-sectional restrictions (production, demand, behavioral chars) unchanged
  - Added `yyyymm` to both `dc_tr` and `dc_tv` data contexts

- **Fix 2 — L-BFGS eval** (`run_estimation_julia.jl`):
  - Removed `EvalCache`, `build_eval_cache`, `eval_config_fast`, `eval_config_fast_loocv`
  - Added `eval_config_lbfgs`: 15-iteration L-BFGS per candidate μ on training data, evaluated on validation set

- **Fix 3 — Consistent μ selection** (`run_estimation_julia.jl`):
  - Both μ selection (CD loop) and final fit now use same L-BFGS with same `best_lambda`
  - Final fit uses 200 L-BFGS iterations (up from 30)

- **Fix 4 — λ cross-validation** (`run_estimation_julia.jl`):
  - Search λ ∈ {1e-6, 1e-5, 1e-4, 1e-3, 1e-2} via plain KRR validation MSE before μ optimization
  - Best λ used for all subsequent μ optimization and final fit

- **TEST_MODE speedup:** Added `TEST_MAX_ROLLING_WINDOWS` to Julia — in TEST_MODE, only runs last N years of OOS (set to 10 in .env)

---

## Decisions
- Monthly aggregation aligns code with paper's Euler equation spec (sum over t with cross-sectional averaging)
- L-BFGS eval (15 iter, warm-started from KRR β) replaces Newton approximation — true objective, ~7.5ms per eval
- λ cross-validated before μ — avoids confounding regularization strength with theory penalty strength
- TEST_MODE=true with 10 rolling windows for fast iteration

## Next Steps
- Run estimation with TEST_MODE=true to verify Theory-KRR ≥ KRR
- If confirmed, flip TEST_MODE=false for full run (all stocks, all windows)
- Generate Tables 10-12 + Figure from output files
- Update paper text with final results
