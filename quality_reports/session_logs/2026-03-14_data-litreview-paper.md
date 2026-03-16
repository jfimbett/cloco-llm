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

## Next Steps
- Design LaTeX shells for GKX-aligned results tables (model horse race, DM matrix, restriction importance)
- Run estimation in TEST_MODE to verify end-to-end pipeline
- Fill table shells with test-mode results
