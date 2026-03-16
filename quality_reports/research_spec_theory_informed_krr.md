# Research Specification: Theory-Informed Kernel Ridge Regression for Asset Pricing

**Date:** 2026-03-14
**Researcher:** Amandri (Juan F. Imbet, Paris Dauphine University - PSL)

## Project Type
empirical+theory

## Recommended Pipeline

```
/lit-review "theory-informed regularization asset pricing"
/identify_reducedform "KRR with structural penalties"
/data-analysis [dataset]
/draft-paper [section]
/econometrics-check paper/main.tex
/review-code code/
/proofread paper/main.tex
/create-talk beamer
```

## Research Question

Can model-implied structural restrictions from economic theory — Euler equations, production-based conditions, intermediary constraints, demand-system equilibria — improve out-of-sample return forecasting when incorporated as soft penalties in a kernel ridge regression framework, where each restriction enters with its own Lagrange multiplier so that even misspecified theories contribute only to the extent the data support them?

## Motivation

Purely statistical ML methods (Gu, Kelly, Xiu 2020) dominate return prediction but ignore economic theory entirely. Meanwhile, structural models encode deep knowledge about the return-generating process but are individually misspecified. Recent work shows theory and statistics contain complementary information (Bianchi, Rubesam, Tamoni 2024), and that even misspecified structural models improve ML predictions via transfer learning (Chen et al. 2025).

The innovation is to use 50-60 *genuine model-implied restrictions* — not reduced-form shape constraints — as soft penalties in kernel ridge regression. Each restriction comes from a specific economic model (habit, long-run risk, intermediary capital, demand systems, etc.) and enters with its own multiplier $\mu_j$. Cross-validation drives $\mu_j \to 0$ for misspecified models and $\mu_j > 0$ for helpful ones. This is the function-space, economic-theory analog of the LLM-Lasso, which showed that structured prior knowledge from text improves penalized estimation in parameter space.

The estimated multiplier vector $(\mu_1, \ldots, \mu_J)$ provides, for the first time, an empirically calibrated ranking of economic theories by their marginal out-of-sample forecasting value — answering which models actually help predict returns beyond agnostic statistical shrinkage.

## Hypothesis

Theory-Informed KRR with heterogeneous structural penalties will produce higher out-of-sample Sharpe ratios and $R^2_{OOS}$ than standard KRR with homogeneous RKHS-norm regularization, particularly in small samples and during periods of market stress. The estimated $\mu_j$ will reveal that consumption-based and intermediary restrictions contribute the most marginal forecasting value.

## Empirical Strategy

- **Method:** Kernel Ridge Regression with J heterogeneous structural penalties, cross-validated via grouped multipliers
- **Estimator:**
  $$\hat{f} = \arg\min_{f \in \mathcal{H}} \frac{1}{n}\sum_{i,t}(R_{i,t+1} - f(\mathbf{X}_{i,t}))^2 + \lambda_{\text{stat}}\|f\|_{\mathcal{H}}^2 + \sum_{j=1}^{J}\mu_j C_j(f)$$
- **Structural penalties $C_j(f)$:** 50-60 restrictions from 8 model families (consumption Euler, production, intermediary, learning, demand-system, option-implied, behavioral, macro-finance)
- **Cross-validation:** 9-dimensional (1 $\lambda_{\text{stat}}$ + 8 group-level $\mu_{\text{group}}$), leave-one-year-out temporal CV, 200 random draws
- **Benchmarks:** Historical mean, OLS, Ridge, Lasso, Elastic Net, standard KRR, neural net (Gu-Kelly-Xiu)
- **Evaluation metrics:** $R^2_{OOS}$ (Campbell-Thompson), out-of-sample Sharpe ratio, certainty equivalent return
- **Robustness:** Ablation by restriction group, subsample analysis (crises vs. calm), bias-variance decomposition, sensitivity to pre-estimated SDF parameters

## Theoretical Model

- **Model type:** Penalized function estimation in RKHS with economic-model-implied constraints
- **Core mechanism:** Each economic model implies a functional restriction $C_j(f)$ on the mapping from state variables to expected returns. These enter as soft penalties with individual multipliers $\mu_j$. The representer theorem (extending Babii-Ghysels-Striaukas) ensures the solution lies in the span of kernel evaluations even with structural penalties.
- **Main predictions:**
  1. Theory-informed penalization outperforms agnostic RKHS-norm shrinkage (generalization of LLM-Lasso result from parameter space to function space)
  2. The nesting structure: $\mu_j = 0 \ \forall j$ recovers standard KRR; $\lambda_{\text{stat}} = 0$ with single $\mu_j$ recovers constrained GMM
  3. Cross-validated $\mu_j$ reveals marginal OOS value of each economic theory
- **Structural parameters:** Pre-estimated from macro/firm data or calibrated from literature (risk aversion $\gamma$, discount factor $\delta$, habit persistence $b$, adjustment cost parameters, etc.)

## Data

- **Primary dataset:** Custom panel built from CRSP monthly returns + Compustat fundamentals
- **Key variables:**
  - Returns: Monthly excess returns (CRSP)
  - Firm characteristics: 37+ characteristics (size, B/M, momentum, profitability, investment, etc.)
  - Macro state variables: consumption growth (NIPA), intermediary capital ratio (He-Kelly-Manela), term spread, default spread, cay (Lettau-Ludvigson), VRP (Bollerslev-Tauchen-Zhou), sentiment (Baker-Wurgler)
  - Option-implied: Implied volatility, skewness, kurtosis from OptionMetrics (if feasible)
- **Sample:** US equities, monthly frequency, ~1960-2023 (training starts after sufficient burn-in)
- **Unit of observation:** Security-month
- **Data assembly:** User will provide CRSP/Compustat access; panel construction is part of the project scope

## Expected Results

1. Theory-Informed KRR will outperform standard KRR by 10-30% in Sharpe ratio and 1-3 percentage points in $R^2_{OOS}$
2. Consumption-based Euler restrictions (especially habit and long-run risk) and intermediary restrictions will have the largest $\mu_j$ — these models capture the most relevant economic mechanisms for return prediction
3. Behavioral restrictions may show value during crisis periods but not in calm markets
4. Production-based restrictions will help most for the cross-section (firm-level variation) rather than aggregate prediction
5. The improvement will be largest in volatile periods and smaller samples, consistent with Chen et al. (2025) transfer learning findings

## Contribution

This paper makes three contributions. First, it introduces a unified framework for incorporating 50-60 distinct model-implied structural restrictions into ML-based return prediction, going beyond reduced-form shape constraints (Bryzgalova et al. 2023) to genuine economic model implications. Second, it establishes the formal connection between theory-informed penalization in function space and the LLM-Lasso in parameter space, showing that structured prior knowledge improves regularization whether the priors come from text or economic theory. Third, the estimated multiplier vector provides the first empirical ranking of economic theories by their marginal out-of-sample forecasting value, answering which models actually help predict returns beyond agnostic statistical methods.

## Open Questions

1. **Computational feasibility of 60 individual $\mu_j$:** Grouped CV (8 groups) is manageable, but individual $\mu_j$ estimation may require additional structure (hierarchical penalties, adaptive weighting)
2. **Pre-estimation bias:** How sensitive are results to the first-stage SDF parameter estimates? Need systematic sensitivity analysis
3. **Nonparametric Euler restriction (#13):** Elegant theoretically but may be hard to implement as a tractable penalty — may need to defer
4. **Option-implied restrictions:** Require OptionMetrics data which may limit sample coverage (post-1996 only)
5. **Conference submission timeline:** Paper draft needed by ~2026-03-21; may need to prioritize 20-30 highest-impact restrictions for initial version
6. **Interaction between restrictions:** Do restrictions from the same model family (e.g., multiple consumption Euler variants) provide redundant information, or does each variant add marginal value?
