# Domain Profile

## Field

**Primary:** Empirical Asset Pricing / Financial Econometrics
**Adjacent subfields:** Machine Learning in Finance, Structural Finance, Financial Economics Theory

---

## Target Journals (ranked by tier)

| Tier | Journals |
|------|----------|
| Top-5 | Econometrica, RFS, JF, JFE, REStud |
| Top field | RFS, Management Science, JFQA, JFE |
| Strong field | Journal of Econometrics, Journal of Business & Economic Statistics, Journal of Applied Econometrics |
| Specialty | Journal of Empirical Finance, Journal of Financial Data Science, Quantitative Finance |

---

## Common Data Sources

| Dataset | Type | Access | Notes |
|---------|------|--------|-------|
| CRSP Monthly Stock File | Panel (security-month) | WRDS | Returns, prices, shares outstanding; universe of US equities |
| Compustat Annual/Quarterly | Panel (firm-period) | WRDS | Fundamentals: assets, investment, profitability, leverage |
| Kenneth French Data Library | Panel (portfolio-month) | Public | Factor returns, sorted portfolio returns, RF rate |
| NIPA (BEA) | Time series | Public | Aggregate consumption (nondurable + services), GDP components |
| He-Kelly-Manela Intermediary Factor | Time series | Public | Intermediary capital ratio, leverage factor |
| FRED | Time series | Public | Macro state variables: term spread, default spread, inflation, T-bill |
| OptionMetrics | Panel (option-month) | WRDS | Implied volatility surfaces, risk-neutral moments |
| Baker-Wurgler Sentiment Index | Time series | Public | Aggregate investor sentiment |
| Lettau-Ludvigson cay | Time series | Public | Consumption-wealth ratio |

---

## Common Identification Strategies

| Strategy | Typical Application | Key Assumption to Defend |
|----------|-------------------|------------------------|
| Out-of-sample R-squared | Return prediction horse races | Expanding/rolling window respects temporal ordering; no lookahead |
| Cross-validated tuning | Hyperparameter selection for ML models | Temporal CV (leave-year-out); no future data leakage |
| Spanning tests | Does factor X add information beyond Y? | Correct specification of the test assets |
| GRS test | Joint test of alphas = 0 | Returns are i.i.d. normal (or use robust version) |
| Sharpe ratio comparison | Economic significance of predictions | Block bootstrap or HAC for inference on SR differences |
| Diebold-Mariano test | Forecast comparison | HAC standard errors for serial correlation in forecast errors |

---

## Field Conventions

- Out-of-sample evaluation is mandatory; in-sample fit alone is insufficient
- Monthly frequency is standard for cross-sectional return prediction
- Report R-squared_OOS (Campbell-Thompson), Sharpe ratios, and certainty equivalent returns
- Characteristics should be cross-sectionally ranked or standardized (percentile or z-score)
- Rolling vs expanding window: report both or justify choice
- Missing data handling must be explicit (no silent drops)
- Compare against strong benchmarks: historical mean, OLS, Ridge/Lasso, random forest, neural net
- Value-weighted and equal-weighted results both expected
- Transaction costs discussion required for portfolio-based metrics

---

## Notation Conventions

| Symbol | Meaning | Anti-pattern |
|--------|---------|-------------|
| $R_{i,t+1}$ | Excess return of asset $i$ from $t$ to $t+1$ | Don't use $r$ without specifying excess vs gross |
| $f(\cdot)$ | Conditional expected return function | Don't use $\hat{y}$ |
| $\mathcal{H}$ | RKHS (reproducing kernel Hilbert space) | Don't use $H$ without calligraphic |
| $k(\cdot, \cdot)$ | Kernel function | |
| $\lambda$ | Statistical regularization parameter | Don't mix with $\lambda$ for Lagrange multipliers |
| $\mu_j$ | Structural penalty multiplier for restriction $j$ | |
| $M_{t+1}$ | Stochastic discount factor | Don't use $m$ lowercase for SDF |
| $\mathbf{X}_{i,t}$ | Vector of characteristics/state variables | |
| $C_j(f)$ | Structural penalty function for restriction $j$ | |
| $\|\cdot\|_{\mathcal{H}}$ | RKHS norm | |

---

## Seminal References

| Paper | Why It Matters |
|-------|---------------|
| Gu, Kelly, Xiu (2020) | Benchmark: ML methods for return prediction; must beat or match |
| Babii, Ghysels, Striaukas | Structural kernel econometrics — mathematical foundation |
| Bryzgalova et al. (2023) | Linear precedent for shape-type restrictions (XS-TS-Target-PCA) |
| Chen, Cheng, Liu, Tang (2025) | Transfer learning from structural models validates misspecified-structure-still-helps |
| LLM-Lasso (2025) | Methodological template — structured priors improve penalized estimation |
| Campbell-Cochrane (1999) | External habit — canonical consumption Euler restriction |
| Bansal-Yaron (2004) | Long-run risk — canonical recursive utility restriction |
| He-Krishnamurthy (2013) | Intermediary asset pricing — canonical institutional restriction |
| Koijen-Yogo (2019) | Demand-system approach to asset pricing |
| Gabaix, Koijen, Richmond, Yogo (2024) | Asset embeddings from demand systems |
| Bianchi, Rubesam, Tamoni (2024) | Theory + statistics are complementary for prediction |
| Singh, Vijaykumar (2023/2025) | KRR inference — confidence bands and bootstrap |

---

## Field-Specific Referee Concerns

- "How is this different from just adding more features?" — Must show structural penalties are qualitatively different from adding model-implied variables as regressors
- "Overfitting with 60 penalty terms" — Must demonstrate grouped CV controls complexity; ablation analysis
- "Pre-estimated SDF parameters are noisy" — Sensitivity analysis to calibration choices
- "Why kernel and not neural net?" — Representer theorem gives tractability; convex optimization; interpretable mu_j
- "Economic significance vs statistical significance" — Sharpe ratios and CER, not just R-squared
- "Transaction costs" — Portfolio-based metrics must account for turnover
- "Data snooping" — Multiple testing correction when comparing many model configurations
- "Why not just combine forecasts (Bianchi et al.)?" — Must show unified penalization dominates simple averaging

---

## Quality Tolerance Thresholds

| Quantity | Tolerance | Rationale |
|----------|-----------|-----------|
| R-squared_OOS | Report to 2 decimal places (%) | Standard in literature |
| Sharpe ratios | Report to 2 decimal places | Annualized, with HAC standard errors |
| mu_j estimates | Report relative magnitudes | Absolute scale depends on penalty normalization |
| Bootstrap p-values | 1000+ bootstrap draws minimum | Block bootstrap with 12-month blocks |
| Rolling window | Minimum 120 months training | Standard in Gu-Kelly-Xiu |
