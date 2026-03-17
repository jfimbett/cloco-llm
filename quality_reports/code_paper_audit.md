# Code-Paper Consistency Audit — 2026-03-17 (v2)

## Summary
- Categories passed: 10 / 12
- Categories partial: 2 / 12
- Categories failed: 0 / 12
- **Overall score: 92 / 100** (above 90 threshold — ready for submission)

## Category Scores

| # | Category | Score | Note |
|---|----------|-------|------|
| 1 | Sample split | **PASS** | Rolling GKX 3-way, 1987-2023, 12yr val, annual |
| 2 | Baseline models | **PASS** | All 9 models (8 baselines + Theory-KRR) |
| 3 | Kernel & bandwidth | **PASS** | Gaussian RBF + median heuristic |
| 4 | Theory restrictions | **PASS** | 56 in 8 groups — exact match |
| 5 | Penalty forms | **PASS** | Euler + correlation + demand types consistent |
| 6 | Hyperparameter selection | **PASS** | Coordinate descent, 16 values, 3 cycles |
| 7 | Evaluation metrics | **PASS** | R²_OOS + Sharpe + DM (NW 6 lags) |
| 8 | Nystrom | **PASS** | m=500, Z=K_nm K_mm^{-1/2}, m×m solve |
| 9 | Parallelization | **PARTIAL** | GPU kernels + threaded CD; GPU Cholesky correctly noted as CPU-only |
| 10 | Output files | **PASS** | Bug fixed — cv_results.csv + cv_window_results.json both correct |
| 11 | Reproducibility | **PASS** | Seeds set, TEST_MODE documented |
| 12 | Undocumented | **PARTIAL** | Grid search (benign diagnostic); Newton step sizes undocumented |

## Fixes Applied (v1 → v2)

1. **Sample split** (FAIL→PASS): Rewrote Sections 4.3 and 4.5 to describe rolling GKX protocol
2. **Baseline models** (PARTIAL→PASS): Added neural network (Flux.jl, 32-16-8 architecture)
3. **Restrictions** (FAIL→PASS): Ported 19 missing restrictions from Python to Julia (37→56)
4. **Hyperparameter selection** (FAIL→PASS): Rewrote Section 4.3 + Appendix B.2 to describe coordinate descent
5. **Evaluation metrics** (PARTIAL→PASS): Added Sharpe ratio to Julia code + Table 10; removed CER + bootstrap from paper
6. **Output files** (FAIL→PASS): Fixed undefined variable bug (`test_mse_hm/krr/tikrr`)
7. **Parallelization** (PARTIAL→PARTIAL): Corrected appendix to state CPU Cholesky (not GPU)
8. **Undocumented** (FAIL→PARTIAL): Removed Matern-5/2 claim; replaced L-BFGS description with Newton step equation

## Remaining Minor Issues

1. Grid search over 11 predefined configs (step [e]) runs as a diagnostic but is not described in the paper — benign
2. Newton step sizes {0, 0.01, 0.05, 0.1, 0.5, 1, 2} not listed in the paper — minor detail
