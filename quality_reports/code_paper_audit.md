# Code-Paper Consistency Audit — 2026-03-17 (v3, post-coauthor fixes)

## Summary
- Categories passed: 8 / 12
- Categories partial: 4 / 12
- Categories failed: 0 / 12
- **Overall score: 83 / 100**

## Category Scores

| # | Category | Score | Key Issue |
|---|----------|-------|-----------|
| 1 | Sample split | PASS | All dates, windows, rebalancing match |
| 2 | Baseline models | PASS | 8 baselines + 2 Theory-KRR variants match paper |
| 3 | Kernel and bandwidth | PASS | Gaussian RBF + median heuristic match |
| 4 | Theory restrictions | PASS | 56 restrictions in 8 groups match |
| 5 | Penalty functional forms | PARTIAL | Structure correct; can't verify all 56 formulas |
| 6 | Hyperparameter selection | PARTIAL | CD grid size/stages differ from paper |
| 7 | Evaluation metrics | PARTIAL | L-S portfolio is equal-weighted, paper says value-weighted |
| 8 | Nystrom approximation | PASS | m=500, eigendecomposition, Cholesky all match |
| 9 | Parallelization | PASS | GPU kernels + threaded CD match paper |
| 10 | Output files | PASS | All required CSV/JSON files produced |
| 11 | Reproducibility | PASS | Random.seed!(42), deterministic pipeline |
| 12 | Undocumented behavior | PARTIAL | L-BFGS vs Newton step; no joint θ estimation |

---

## Detailed Findings

### Category 1: Sample Split Protocol
**Paper says:** OOS years 1987–2023, 12-year validation window, expanding training from July 1963, annual rebalancing. For τ=1987: train=1963–1974, val=1975–1986. Re-estimate on train+val before OOS prediction.
**Code does:** `OOS_START_YEAR=1987`, `VAL_YEARS=12`, `val_start=(test_year-12)*100+1`, `train_df=panel[yyyymm < val_start]`. Re-fits on `vcat(train_df, val_df)` before test prediction (line 891).
**Verdict:** PASS

### Category 2: Baseline Models
**Paper says (Section 5.2):** OLS, Ridge (20 log-spaced λ), Lasso, Elastic net (α=0.5), Polynomial-2 (Ridge/Lasso/EN), Standard KRR = 8 baselines. Two Theory-KRR variants: λ=0 (at least one μ>0) and λ=λ*.
**Code does:** `all_models=["ols","ridge","lasso","elastic_net","ridge_poly2","lasso_poly2","en_poly2","krr","best_tikrr","tikrr_lam0"]`. Ridge: 20 log-spaced values. EN: α=0.5. Poly-2: `poly_features_deg2()`. tikrr_lam0 enforces ≥1 active μ.
**Verdict:** PASS

### Category 3: Kernel and Bandwidth
**Paper says:** Gaussian RBF k(x,x')=exp(-||x-x'||²/(2σ²)), σ=median pairwise distance.
**Code does:** `gaussian_rbf`: gamma=1/(2σ²), K=exp(-gamma*sq_dists). `median_heuristic`: computes median of pairwise Euclidean distances (subsample 5000).
**Verdict:** PASS

### Category 4: Theory Restrictions
**Paper says:** 56 restrictions in 8 families: Consumption(13), Production(10), Intermediary(8), Information(6), Demand(6), Volatility(2), Behavioral(6), Macro(5).
**Code does:** `build_all_restrictions()` returns 56 `RestrictionDef` objects with matching counts and family assignments. `FAMILY_TO_GROUP` maps 8 families to groups 0–7.
**Verdict:** PASS

### Category 5: Penalty Functional Forms
**Paper says:** Type A (Euler), Type B (production FOC), Type C (demand-system) with specific formulas.
**Code does:** Each restriction has `penalty_fn(f_hat, X, dc)` and `gradient_fn(f_hat, X, dc)`. Monthly aggregation handles time-series dilution.
**Verdict:** PARTIAL
**Issues:** Cannot verify all 56 penalty/gradient pairs match paper formulas without a deep line-by-line audit of `restrictions_julia.jl` (1265 lines). Structure and types are correct.

### Category 6: Hyperparameter Selection
**Paper says:** (a) λ_stat from KRR CV. (b) CD over 8 groups, 16 candidates: {0}∪{10^u: u∈linspace(-4,1,15)}. (c) Up to 3 cycles, early stop. (d) Each eval uses Newton-like correction. Total ≤384 evals.
**Code does:** (a) λ CV over 5 values. (b) Stage 1 coarse: 8 candidates; stage 2 fine: 11 candidates (adaptive). (c) 2 stages (not 3 cycles). (d) L-BFGS with maxiter=15 (not single Newton step).
**Verdict:** PARTIAL
**Issues:**
1. Grid size: paper=16, code=8/11. Fix: align paper eq. (4.6) with actual adaptive grid.
2. Cycle count: paper=3, code=2. Fix: update paper.
3. Eval method: paper=Newton step, code=L-BFGS. Fix: update Section 4.4 and Appendix B.

### Category 7: Evaluation Metrics
**Paper says:** R²_OOS, SR with VW decile portfolios, DM test (NW HAC, 6 lags).
**Code does:** R²_OOS correct. SR uses individual stock decile sorts (equal-weighted). DM in `dm_pairwise.py` with NW HAC, 6 lags, Bartlett kernel.
**Verdict:** PARTIAL
**Issues:**
1. **L-S weighting:** Paper says "value-weighted," code uses `mean()` (equal-weighted). Fix: use VW returns, or update paper.
2. **Linear model Sharpe proxy:** Ridge/Lasso/EN stock predictions use OLS coefficients. Fix: store and reuse fitted coefficients.

### Category 8: Nystrom Approximation
**Paper says:** m=500, Z=K_nm K_mm^{-1/2} via eigendecomposition, β=(Z'Z+nλI)^{-1}Z'y.
**Code does:** `NYSTROM_M=500`. Eigendecomposition with numerical stability. Cholesky solve.
**Verdict:** PASS

### Category 9: Parallelization
**Paper says:** GPU for kernels, multi-threaded CD, parallel ablation.
**Code does:** `gaussian_rbf_gpu` with CuArray. `Threads.@threads` in CD. GPU detection with fallback.
**Verdict:** PASS

### Category 10: Output Files
**Code produces:** `cv_results.csv`, `cv_window_results.json`, `oos_predictions.csv`. Python generators for Tables 10, 11, 12, DM, and figures.
**Verdict:** PASS

### Category 11: Reproducibility
**Code:** `Random.seed!(42)` at start. All stochastic components seeded.
**Verdict:** PASS

### Category 12: Undocumented Behavior
**Code features not in paper:**
1. L-BFGS (maxiter=15) instead of Newton step for μ config evaluation
2. Adaptive CD refinement (coarse→fine) vs paper's fixed 16-point grid
3. OLS proxy for linear model stock-level Sharpe predictions
4. Only 7 chars for managed portfolio sorts, all ~220 as features (paper doesn't specify sort chars)

**Paper claims not in code:**
1. Joint estimation of θ (Approach 1) — code uses calibrated parameters
2. Newton step with discrete step-size selection (eq. 4.7)
3. 16 candidates per group in CD

**Verdict:** PARTIAL

---

## Discrepancy List (priority order)

### Must Fix (referee would flag)
| # | Paper ref | Code ref | Issue | Fix |
|---|-----------|----------|-------|-----|
| 1 | empirical.tex:142 | Julia:1098 | L-S portfolio: paper=VW, code=EW | Add VW using market equity weights, or update paper |
| 2 | estimation.tex:153-161 | Julia:738 | Paper says "Newton-like correction," code uses L-BFGS | Update paper Sec 4.4 + Appendix B to describe L-BFGS |
| 3 | estimation.tex:77 | N/A | Paper says "joint estimation (Approach 1)" baseline, code uses calibration | Change paper to "calibration (Approach 3)" or implement joint est. |

### Should Fix
| # | Paper ref | Code ref | Issue | Fix |
|---|-----------|----------|-------|-----|
| 4 | estimation.tex:124 | Julia:739 | CD grid: paper=16 candidates, code=8+11 adaptive | Align paper eq. (4.6) with actual implementation |
| 5 | estimation.tex:128 | Julia:750 | CD cycles: paper=3, code=2 stages | Update paper to "2 stages (coarse + fine)" |
| 6 | estimation.tex:130 | N/A | Paper says ≤384 evals, actual max ≈176 | Update total eval count |
| 7 | N/A | Julia:1068 | Linear model Sharpe uses OLS proxy | Store/reuse actual Ridge/Lasso/EN coefficients |

### Minor
| # | Paper ref | Code ref | Issue | Fix |
|---|-----------|----------|-------|-----|
| 8 | Appendix B | Julia:505 | "Newton-like" language throughout appendix | Update to "L-BFGS" |
| 9 | N/A | Julia:69 | 7 chars for portfolio sorts, ~220 as features | Clarify in paper which chars define quintile sorts |
