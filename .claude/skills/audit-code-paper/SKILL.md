---
name: audit-code-paper
description: Audit estimation code against paper methodology. Verifies that the implementation matches what Sections 4-5 and the appendix describe — sample splits, models, metrics, restrictions, and computational details.
argument-hint: "[julia|python|all]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Agent"]
---

# Audit Code-Paper Consistency

Verify that the estimation code faithfully implements the methodology described in the paper. Produces a scored report with pass/fail per category.

## Mode

- `$ARGUMENTS` = `julia`: audit `code/run_estimation_julia.jl` + `code/restrictions_julia.jl`
- `$ARGUMENTS` = `python`: audit `code/run_cv_estimation.py` + `code/estimation/` + `code/restrictions/`
- `$ARGUMENTS` = `all` (default): audit both

## Workflow

### Phase 1: Read Paper Methodology

Read the following paper sections to extract the claimed methodology:

- `paper/sections/estimation.tex` — Section 4: kernel choice, pre-estimation, CV strategy, computation, rolling window
- `paper/sections/empirical.tex` — Section 5: data, baseline models, evaluation metrics, summary stats
- `paper/appendix/appendix.tex` — Appendix B: Nystrom, Bayesian/coordinate descent, parallelization

Extract a checklist of every methodological claim:
- Sample dates (train/val/test boundaries)
- Number and names of baseline models
- Hyperparameter grids and tuning procedures
- Evaluation metrics and their formulas
- Restriction count, grouping, penalty formulas
- Computational details (Nystrom m, kernel bandwidth, convergence criteria)

### Phase 2: Read Code Implementation

Read the estimation code files. For each methodological claim from Phase 1, find the corresponding code and verify:

1. **Does the code implement this claim?** (YES / NO / PARTIAL)
2. **Are the parameter values consistent?** (e.g., paper says 12-year validation, code uses 12)
3. **Are there code features not described in the paper?** (undocumented behavior)

### Phase 3: Category Audit (12 categories)

Score each category PASS (code matches paper) / PARTIAL (mostly matches, minor discrepancies) / FAIL (significant mismatch):

**Category 1: Sample Split Protocol**
- Paper: what dates for train/val/test?
- Code: what dates does the code use?
- Check: OOS start year, validation window length, rebalancing frequency

**Category 2: Baseline Models**
- Paper: which models are listed in Section 5.2?
- Code: which models are implemented?
- Check: same model names, same hyperparameter spaces, same tuning procedure

**Category 3: Kernel and Bandwidth**
- Paper: which kernel? how is σ set?
- Code: does the kernel function match? is median heuristic implemented correctly?

**Category 4: Theory Restrictions**
- Paper: 56 restrictions in 8 groups (Tables 2-9)
- Code: how many restrictions implemented? which groups?
- Check: restriction names, family assignments, penalty formulas match the paper

**Category 5: Penalty Functional Forms**
- Paper: Type A (Euler), Type B (production FOC), Type D (demand)
- Code: are the penalty() functions consistent with the claimed formulas?
- Check: gradient implementations are analytically correct

**Category 6: Hyperparameter Selection**
- Paper: what tuning method? (random search / coordinate descent / hierarchical)
- Code: what does the code actually do?
- Check: search space bounds, number of evaluations, convergence criteria

**Category 7: Evaluation Metrics**
- Paper: R²_OOS formula (eq. X), Sharpe ratio, CER, DM test
- Code: are these computed correctly?
- Check: HAC lags, bootstrap parameters, formula matches

**Category 8: Nystrom Approximation**
- Paper: m landmarks, feature map Z, solve β instead of α
- Code: does the implementation match Appendix B?
- Check: m value, eigendecomposition for K_mm^{-1/2}, gradient projection

**Category 9: Parallelization**
- Paper: GPU for kernels, multi-threaded grid search, parallel BO/CD
- Code: are these actually used?
- Check: CUDA calls, @threads decorators, n_jobs settings

**Category 10: Output Files**
- Paper: Tables 10-12 require specific data
- Code: does the code produce the required output files?
- Check: cv_results.csv columns, cv_window_results.json fields match what table generators expect

**Category 11: Reproducibility**
- Code: is there a random seed? are results deterministic?
- Check: seed value, any stochastic components that aren't seeded

**Category 12: Undocumented Behavior**
- Code features not described in the paper (could surprise a referee)
- Paper claims not implemented in the code (promises not kept)
- Flag both directions

### Phase 4: Generate Report

Write report to `quality_reports/code_paper_audit.md`:

```markdown
# Code-Paper Consistency Audit — [date]

## Summary
- Categories passed: X / 12
- Categories partial: Y / 12
- Categories failed: Z / 12
- Overall score: XX / 100

## Category Scores

| # | Category | Score | Key Issue |
|---|----------|-------|-----------|
| 1 | Sample split | PASS/PARTIAL/FAIL | ... |
| ... |

## Detailed Findings

### Category 1: Sample Split Protocol
**Paper says:** ...
**Code does:** ...
**Verdict:** PASS / PARTIAL / FAIL
**Issues:** ...
**Fix:** ... (if applicable)

[repeat for all 12 categories]

## Discrepancy List (for fixing)
1. [paper line] says X, but [code line] does Y → fix code/paper
2. ...
```

### Phase 5: Score Calculation

- PASS = 10 points
- PARTIAL = 5 points
- FAIL = 0 points
- Total = sum / 120 * 100

Thresholds:
- >= 90: Ready for submission
- 70-89: Minor fixes needed
- < 70: Significant alignment issues
