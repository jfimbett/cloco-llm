# Data Sources — Theory-Informed KRR

Place raw data files in `data/raw/`. Processed panels go in `data/processed/`.

---

## Priority 1: Core Panel (Required)

| # | Dataset | Source | Files Needed | Variables | Frequency | Coverage |
|---|---------|--------|-------------|-----------|-----------|----------|
| 1 | **CRSP Monthly Stock File** | WRDS | `crsp_monthly.csv` | permno, date, ret, retx, prc, shrout, cfacpr, cfacshr, exchcd, shrcd | Monthly | 1960–2024 |
| 2 | **Compustat Annual Fundamentals** | WRDS | `compustat_annual.csv` | gvkey, datadate, at, ceq, sale, revt, cogs, xsga, xrd, capx, ppegt, ppent, dp, ib, oibdp, dltt, dlc, che, invt, act, lct, csho, prcc_f, sic | Annual | 1960–2024 |
| 3 | **CRSP-Compustat Link** | WRDS | `ccm_link.csv` | gvkey, lpermno, linkdt, linkenddt, linktype, linkprim | — | — |
| 4 | **Kenneth French Factors** ✅ | [French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | `ff_factors_monthly.csv` | Mkt-RF, SMB, HML, RMW, CMA, RF, Mom | Monthly | 1963–2026 |

---

## Priority 2: Firm Characteristics (Required for Cross-Section)

| # | Dataset | Source | Files Needed | Purpose |
|---|---------|--------|-------------|---------|
| 5 | **Jensen, Kelly, Pedersen (2023) characteristics** | [Open Source AP](https://www.openassetpricing.com/) or replicate from CRSP/Compustat | `firm_characteristics.csv` | 37+ standardized characteristics: size, B/M, momentum (2-12), reversal, investment, profitability, accruals, beta, idiovol, illiquidity, turnover, etc. |
| 6 | **Compustat Quarterly** | WRDS | `compustat_quarterly.csv` | atq, ceqq, saleq, ibq — for timely accounting ratios |

---

## Priority 3: Macro State Variables (Required for SDF Pre-Estimation)

| # | Dataset | Source | Files Needed | Variables |
|---|---------|--------|-------------|-----------|
| 7 | **NIPA Consumption** ✅ | [BEA](https://www.bea.gov/) / FRED | `nipa_consumption.csv` | Real per-capita nondurable consumption + services (seasonally adjusted, monthly or quarterly) |
| 8 | **FRED Macro Series** ✅ | [FRED](https://fred.stlouisfed.org/) | `fred_macro.csv` | TB3MS (3m T-bill), GS10 (10y yield), AAA, BAA (credit spreads), CPIAUCSL (CPI), INDPRO (industrial production), UNRATE |
| 9 | **He-Kelly-Manela Intermediary Factor** ✅ | [Manela website](https://apps.olin.wustl.edu/faculty/manela/hkm/intermediatoryassetpricing.html) | `hkm_intermediary.csv` | Intermediary capital ratio, intermediary capital risk factor |
| 10 | **Lettau-Ludvigson cay** ⚠️ | [Ludvigson website](https://www.sydneyludvigson.com/cay) | `cay.csv` | cay (consumption-wealth ratio) — *website 404; provide manually* |
| 11 | **Baker-Wurgler Sentiment** ⚠️ | [Wurgler website](http://people.stern.nyu.edu/jwurgler/) | `sentiment.csv` | Sentiment index (orthogonalized and raw) — *JS-heavy site; provide manually* |
| 12 | **Gilchrist-Zakrajsek EBP** ✅ | [FRED: BAAFFM](https://fred.stlouisfed.org/) | `ebp.csv` | Excess bond premium (BAAFFM series) |
| 13 | **Welch-Goyal Predictors** ✅ | [Goyal website](https://sites.google.com/view/agoyal145) | `welch_goyal.csv` | dp, dy, ep, bm, ntis, tbl, lty, ltr, tms, dfy, dfr, svar, ik |

---

## Priority 4: Variance and Volatility

| # | Dataset | Source | Files Needed | Variables |
|---|---------|--------|-------------|-----------|
| 14 | ~~OptionMetrics Volatility Surface~~ | ~~WRDS~~ | — | *Dropped: no access. Restrictions 44, 46, 47, 48 (risk-neutral density, IV surface, higher moments, jump risk) removed from paper.* |
| 15 | **VIX** ✅ | CBOE / FRED | `vix.csv` | Daily/monthly VIX |
| 16 | **Variance Risk Premium** | Construct from VIX + CRSP daily | `vrp.csv` | VRP = VIX²/12 - RV (Bollerslev-Tauchen-Zhou). RV from CRSP daily returns. |
| 16b | **CRSP Daily** ✅ | WRDS | `crsp_daily.csv` | 98.5M rows, used for realized variance construction |

---

## Priority 5: Pre-Estimated Model Parameters (Can Calibrate from Literature)

These don't need raw data if we calibrate from published estimates. But if you want to re-estimate:

| # | What | Source | Notes |
|---|------|--------|-------|
| 17 | Risk aversion γ, discount factor δ | GMM on consumption Euler | γ ∈ {2, 5, 10, 20}, δ ≈ 0.99 — grid from literature |
| 18 | Habit persistence b (Campbell-Cochrane) | Calibrated: b = 0.97, S̄ from steady state | Campbell-Cochrane (1999) Table I |
| 19 | Long-run risk parameters (Bansal-Yaron) | Calibrated from BY (2004) Table II | μ_c, ρ, φ_e, σ̄, ν_1 |
| 20 | Adjustment cost parameters | Compustat investment data, GMM | Convex: a ∈ [1, 10]; see Cooper-Haltiwanger (2006) |
| 21 | Adrian-Etula-Muir leverage betas | Pre-estimated regressions on broker-dealer leverage | AEM (2014) replication |

---

## Data Assembly Notes

- **Merge key:** CRSP permno ↔ Compustat gvkey via CCM link (primary link, LC/LU types)
- **Filters:** Exclude financials (SIC 6000-6999) and utilities (SIC 4900-4999) unless studying those sectors
- **Share code filter:** CRSP shrcd ∈ {10, 11} (ordinary common shares)
- **Exchange filter:** exchcd ∈ {1, 2, 3} (NYSE, AMEX, NASDAQ)
- **Minimum price:** Exclude stocks with |prc| < $5 (or $1 for robustness)
- **Characteristics:** Cross-sectionally rank to [0, 1] each month (standard in GKX 2020)
- **Missing data:** Require at least 15 non-missing characteristics per stock-month
- **Returns:** Winsorize at 0.1% and 99.9% tails

---

## File Naming Convention

Place in `data/raw/` with these names. The data pipeline in `code/data_pipeline/` will process them into `data/processed/panel_monthly.parquet`.

## Auto-Download Script

```bash
python code/data_pipeline/download_public_data.py          # download (skips existing)
python code/data_pipeline/download_public_data.py --force   # re-download all
```

Downloads 7 public datasets (✅ marked above). Two datasets (⚠️) require manual download.
