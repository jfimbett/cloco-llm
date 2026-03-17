# Restriction Data Audit — 2026-03-16

## Summary
- Total restrictions: 56
- Unique variables needed: 42
- Variables with data coverage: 38 / 42 (90%)
- Documentation gaps: 14 variables undocumented or partially documented
- Summary statistics gaps: 8 variables should be added to Table 1

## Restriction-by-Variable Matrix

| # | Restriction | Variable | Panel Col | Data Status | Paper Doc | Summary Stats |
|---|------------|----------|-----------|-------------|-----------|---------------|
| 1 | Power utility (C-CAPM) | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 2 | Epstein-Zin | Consumption growth, R_m | `cons_growth`, `mktrf` | AVAILABLE | DOCUMENTED | IN TABLE |
| 3 | External habit | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 4 | Internal habit (diff) | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 5 | Internal habit (ratio) | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 6 | Long-run risk | Consumption growth, R_m | `cons_growth`, `mktrf` | AVAILABLE | DOCUMENTED | IN TABLE |
| 7 | Long-run risk + jumps | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 8 | Rare disaster (const) | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 9 | Variable rare disaster | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 10 | Precautionary savings | Consumption growth, σ²_c | `cons_growth`, `realized_var` | AVAILABLE | DOCUMENTED | IN TABLE |
| 11 | Durable consumption | Consumption growth, R_m | `cons_growth`, `mktrf` | AVAILABLE | PARTIAL | IN TABLE |
| 12 | Heterogeneous agents | Consumption growth, σ²_cross | `cons_growth` | AVAILABLE | PARTIAL | IN TABLE |
| 13 | Nonparametric Euler | Consumption growth | `cons_growth` | AVAILABLE | DOCUMENTED | IN TABLE |
| 14 | Investment CAPM | I/K, ROE | `ik`, `roe` | AVAILABLE | DOCUMENTED | IN TABLE |
| 15 | q-theory factor | I/K, ROE, EG | `ik`, `roe`, `fgr5yrLag`/`r_eg` | AVAILABLE | PARTIAL | **SHOULD ADD** (EG) |
| 16 | Convex adjustment | I/K | `ik` | AVAILABLE | DOCUMENTED | IN TABLE |
| 17 | Nonconvex adjustment | I/K | `ik` | AVAILABLE | DOCUMENTED | IN TABLE |
| 18 | Irreversibility | I/K | `ik` | AVAILABLE | DOCUMENTED | IN TABLE |
| 19 | Financial constraints (coll.) | I/K, K/debt | `ik`, `k_debt` (new) | AVAILABLE | **UNDOCUMENTED** (k_debt) | **SHOULD ADD** |
| 20 | Financial constraints (equity) | I/K, Leverage, CF | `ik`, `leverage`, `CF` | AVAILABLE | PARTIAL (CF) | **SHOULD ADD** (Lev, CF) |
| 21 | Costly external finance | I/K, Leverage, Div | `ik`, `leverage`, `DivYieldST` | AVAILABLE | **UNDOCUMENTED** (Div) | **SHOULD ADD** (Div) |
| 22 | Labor-augmented | I/K, Hiring | `ik`, `hire` | AVAILABLE | **UNDOCUMENTED** | **SHOULD ADD** |
| 23 | Intangible capital | I/K, R&D/K, SGA/K | `ik`, `rd_intensity`, `sga_at` (new) | AVAILABLE | PARTIAL (SGA) | **SHOULD ADD** (SGA/K) |
| 24 | Intermediary capital ratio | HKM η | `hkm_risk_factor` | AVAILABLE | DOCUMENTED | IN TABLE (ratio) |
| 25 | Intermediary leverage | ΔLeverage (AEM) | `aem_leverage_change` (new) | AVAILABLE | **UNDOCUMENTED** | **SHOULD ADD** |
| 26 | Funding liquidity | TED spread | `ted_spread` (new) | AVAILABLE | **UNDOCUMENTED** | **SHOULD ADD** |
| 27 | Dealer balance sheet | Primary dealer η | `hkm_risk_factor` | AVAILABLE | DOCUMENTED | IN TABLE |
| 28 | Limits to arbitrage | Sentiment | `sentiment` | AVAILABLE | DOCUMENTED | IN TABLE |
| 29 | Slow-moving capital | Capital flows | `equity_flow` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 30 | Margin CAPM | R_m, margin proxy | `mktrf`, `vix` (proxy) | PROXY | **UNDOCUMENTED** | OK TO OMIT |
| 31 | Leverage constraints | BAB factor | `bab` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 32 | Bayesian learning | Posterior mean/var | Latent (estimated) | AVAILABLE | DOCUMENTED | N/A |
| 33 | Learning about regime | Regime probability | Latent (estimated) | AVAILABLE | DOCUMENTED | N/A |
| 34 | Parameter uncertainty | Predictive variance | Latent (estimated) | AVAILABLE | DOCUMENTED | N/A |
| 35 | Ambiguity aversion | Worst-case density | Latent (estimated) | AVAILABLE | DOCUMENTED | N/A |
| 36 | Disagreement | Forecast dispersion | `ForecastDispersion` | AVAILABLE | PARTIAL | OK TO OMIT |
| 37 | Rational inattention | Information flow | `ChNAnalyst` (proxy) | PROXY | **UNDOCUMENTED** | OK TO OMIT |
| 38 | Market clearing | Demand, supply | Characteristics + me | AVAILABLE | DOCUMENTED | N/A |
| 39 | Portfolio choice FOC | Char-based elasticities | Characteristics | AVAILABLE | DOCUMENTED | N/A |
| 40 | Inelastic markets | ΔFlow | `equity_flow` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 41 | Search frictions OTC | Search intensity, bargaining | `BidAskSpread` (proxy) | PROXY | **UNDOCUMENTED** | OK TO OMIT |
| 42 | Fire sale externalities | Fire-sale pressure | Latent (estimated) | AVAILABLE | PARTIAL | N/A |
| 43 | Short-sale constraints | Short interest, dispersion | `ShortInterest`, `ForecastDispersion` | AVAILABLE | PARTIAL | OK TO OMIT |
| 44 | Variance risk premium | VIX, realized var | `vix`, `realized_var` | AVAILABLE | DOCUMENTED | IN TABLE |
| 45 | Stochastic volatility | VIX² | `vix` | AVAILABLE | DOCUMENTED | IN TABLE |
| 46 | Prospect theory | Consumption growth, R_m | `cons_growth`, `mktrf` | AVAILABLE | DOCUMENTED | IN TABLE |
| 47 | Overconfidence | Momentum, Reversal | `Mom12m`, `streversal` | AVAILABLE | DOCUMENTED | IN TABLE |
| 48 | Disposition effect | CGO | `cgo` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 49 | Extrapolative expectations | Past avg return | `past_avg_ret` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 50 | Investor sentiment | Sentiment | `sentiment` | AVAILABLE | DOCUMENTED | IN TABLE |
| 51 | Salience theory | Salience | `salience` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 52 | Affine term structure | Yield curve state | `term_spread` | AVAILABLE | DOCUMENTED | IN TABLE |
| 53 | Inflation risk premium | IRP | `breakeven_infl` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 54 | Monetary policy | Δi_surprise | `mp_surprise` (new) | AVAILABLE | **UNDOCUMENTED** | OK TO OMIT |
| 55 | Consumption-wealth ratio | cay | `cay` | AVAILABLE | DOCUMENTED | IN TABLE |
| 56 | Credit spread / EBP | EBP | `ebp` | AVAILABLE | DOCUMENTED | IN TABLE |

## Issues Found

### Data Gaps
**No hard gaps remaining.** All 56 restrictions have data coverage (exact or proxy).

3 restrictions use proxy variables:
- **#30 Margin CAPM**: VIX as margin proxy (no direct margin data)
- **#37 Rational inattention**: `ChNAnalyst` as information flow proxy
- **#41 Search frictions**: `BidAskSpread` as search intensity proxy

### Documentation Gaps (14 variables)

The following variables are used in restrictions but **not explained in the paper's data section** (`paper/sections/empirical.tex`):

**Firm-level characteristics (need Panel A documentation):**
1. `k_debt` (K/debt collateral ratio) — restriction 19
2. `CF` (cash flow) — restriction 20
3. `DivYieldST` (dividend yield) — restriction 21
4. `hire` (hiring rate) — restriction 22
5. `sga_at` (SGA/assets) — restriction 23
6. `cgo` (capital gains overhang) — restriction 48
7. `past_avg_ret` (trailing 36-month average return) — restriction 49
8. `salience` (return salience) — restriction 51

**Macro/time-series variables (need Panel B documentation):**
9. `aem_leverage_change` (AEM intermediary leverage change) — restriction 25
10. `ted_spread` (TED spread, 3m LIBOR - T-bill) — restriction 26
11. `bab` (BAB factor) — restriction 31
12. `equity_flow` (household equity net flows) — restrictions 29, 40
13. `breakeven_infl` (10Y breakeven inflation rate) — restriction 53
14. `mp_surprise` (monetary policy surprise) — restriction 54

### Summary Statistics Gaps (8 variables)

Variables used in **3+ restrictions** that are missing from Table 1:

**Panel A additions needed:**
1. **Leverage** (`leverage`) — used in restrictions 20, 21 (and related to 19, 25)
2. **Cash flow** (`CF`) — restriction 20
3. **Dividend yield** (`DivYieldST`) — restriction 21
4. **Hiring rate** (`hire`) — restriction 22
5. **R&D intensity** (`rd_intensity`) — restriction 23 (already in panel)
6. **SGA/K** (`sga_at`) — restriction 23
7. **K/debt** (`k_debt`) — restriction 19

**Panel B additions needed:**
8. **TED spread** (`ted_spread`) — restriction 26

## Recommended Fixes

### Fix 1: Add variables to summary statistics (Table 1)
Update `code/tables/summary_stats.py` to include leverage, CF, DivYieldST, hire, rd_intensity, sga_at, k_debt in Panel A and ted_spread in Panel B.

### Fix 2: Add data documentation paragraph to paper
Add a paragraph in `paper/sections/empirical.tex` after the "Macro state variables" paragraph documenting:
- New firm-level variables: K/debt, SGA/K, CGO, past average return, salience, hiring, CF, dividends
- New macro variables: TED spread, AEM leverage, BAB factor, equity flows, breakeven inflation, monetary policy surprise
- Construction methods and data sources for each

### Fix 3: Update summary statistics text
Update the `\subsection{Summary Statistics}` text in `empirical.tex` to reference the new variables.
