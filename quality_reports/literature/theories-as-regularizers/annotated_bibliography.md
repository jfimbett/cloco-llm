# Annotated Bibliography — Theories as Regularizers
**Project:** Theory-Informed KRR for Asset Pricing (Imbet & Andriollo, Paris Dauphine - PSL)
**Search Date:** 2026-03-14
**Scope:** Gap-filling search only. The 80+ papers already in `paper/references.bib` are excluded.

---

## DIRECTLY RELATED (Proximity 4–5)

---

### [Kozak, Nagel, Santosh 2020] Shrinking the Cross-Section
**Journal/Source:** Journal of Financial Economics, vol. 135(2), pp. 271–292
**Proximity Score:** 5/5
**Summary:** Constructs a robust stochastic discount factor (SDF) that summarizes the joint explanatory power of a large number of cross-sectional stock return predictors. The key innovation is an economically motivated prior on SDF coefficients that shrinks contributions of low-variance principal components (PCs) of candidate characteristic-based factors. The paper proves that a characteristics-sparse SDF cannot adequately span the cross-section of expected returns, but a small number of high-eigenvalue PCs can. The penalty structure is motivated by arbitrage arguments — low-variance PCs require implausibly large Sharpe ratios if priced, so they should be shrunk more heavily. This is structurally the closest paper to "Theories as Regularizers": both impose economically motivated, heterogeneous (non-isotropic) penalties in high-dimensional return prediction.
**Identification:** Ridge-type shrinkage with PC-based, economically calibrated priors; out-of-sample evaluation.
**Data:** CRSP monthly returns; 50 characteristics, 1963–2015.
**Key Result:** Isotropic shrinkage (standard ridge/LASSO) is dominated by PC-weighted shrinkage; sparse factor models (e.g., Fama-French 5) cannot span the SDF.

---

### [Bryzgalova, Huang, Julliard 2023] Bayesian Solutions for the Factor Zoo: We Just Ran Two Quadrillion Models
**Journal/Source:** Journal of Finance, vol. 78(1), pp. 487–557
**Proximity Score:** 5/5
**Summary:** Proposes a Bayesian framework for analyzing the full universe of linear asset pricing models formed by subsets of a large factor set. Develops a novel prior on risk prices that is heterogeneous across factors — flat priors for well-identified factors, informative priors for weakly identified or spurious factors — and produces a Bayesian model averaging SDF (BMA-SDF). Analyzes 2.25 quadrillion candidate models and finds the BMA-SDF dominates existing models in- and out-of-sample. Highly related because it ranks theories/factors by their data-model complementarity, imposes structured (non-uniform) shrinkage motivated by identification strength, and produces an empirical ranking of economic models.
**Identification:** Bayesian model averaging; structured priors based on factor identification strength (correlation with test assets).
**Data:** 51 candidate factors from the zoo literature; 25 Fama-French test portfolios; 1970–2017.
**Key Result:** BMA-SDF outperforms all individual factor models in- and out-of-sample; many zoo factors are redundant or weakly identified.

---

### [Freyberger, Neuhierl, Weber 2020] Dissecting Characteristics Nonparametrically
**Journal/Source:** Review of Financial Studies, vol. 33(5), pp. 2326–2377
**Proximity Score:** 4/5
**Summary:** Proposes a nonparametric method to study which characteristics provide incremental information for the cross-section of expected returns, using adaptive group LASSO to select characteristics and estimate the selected characteristic-return relationships nonparametrically. The method can handle many characteristics simultaneously and allows for flexible functional forms. Finds that many previously identified return predictors do not provide incremental information once nonlinearities are accounted for, and documents significant nonlinear characteristic-return relationships. Closely related because it applies penalized nonparametric estimation to the cross-section of returns, though it does not impose economic structural constraints as penalties.
**Identification:** Adaptive group LASSO; nonparametric sieve estimation; out-of-sample evaluation.
**Data:** CRSP/Compustat; 62 characteristics; 1964–2016.
**Key Result:** Approximately one-third of commonly studied characteristics are selected; significant nonlinearities documented; equal-weighted R2_OOS of 1.6%.

---

### [Filipovic, Pasricha 2022] Empirical Asset Pricing via Ensemble Gaussian Process Regression
**Journal/Source:** arXiv:2212.01048 [q-fin.RM]; v3 March 2026
**Proximity Score:** 4/5
**Summary:** Proposes an ensemble machine learning approach using Gaussian Process Regression (GPR) — which is mathematically equivalent to kernel ridge regression with a specific kernel — for forecasting conditional stock returns. Evaluates across a broad sample of US equities (1962–2016). The Bayesian framework allows incorporation of prediction uncertainty into portfolio construction. Claims to be the first to systematically apply GPR to cross-sectional return prediction. Directly related as the closest existing application of kernel/RKHS methods specifically to the same prediction problem; no structural economic restrictions are imposed (the gap our paper fills).
**Identification:** Ensemble GPR with out-of-sample evaluation; uncertainty-aware portfolio construction.
**Data:** CRSP monthly returns; 1962–2016.
**Key Result:** Ensemble GPR dominates existing ML models statistically and economically in out-of-sample R2 and Sharpe ratio; prediction-uncertainty-adjusted portfolios outperform equal- and value-weighted benchmarks and the S&P 500.

---

### [Kelly, Malamud, Zhou 2024] The Virtue of Complexity in Return Prediction
**Journal/Source:** Journal of Finance, vol. 79(1), pp. 459–503
**Proximity Score:** 4/5
**Summary:** Theoretically and empirically establishes that complex (overparameterized) models systematically outperform simple models in return prediction. Proves that simple models with few parameters severely understate return predictability relative to complex models where the number of parameters exceeds observations. Empirically documents the virtue of complexity in US equity return prediction, providing a theoretical foundation for the ML approach in general and for kernel methods (which are infinite-dimensional) specifically. Related because it establishes the theoretical rationale for high-complexity (RKHS) estimators; the paper it motivates is exactly our setting.
**Identification:** Theoretical (random matrix theory); empirical out-of-sample evaluation on CRSP.
**Data:** CRSP; 1963–2021.
**Key Result:** Complex models (neural nets, kernel methods) provide substantially higher out-of-sample R2 than simple models; benign overfitting documented in equity returns.

---

### [Chen, Cheng, Liu, Tang 2026] Teaching Economics to the Machines
**Journal/Source:** NBER Working Paper No. 34713, January 2026
**Proximity Score:** 4/5
**Summary:** Proposes theory-guided transfer learning that pre-trains neural networks on synthetic data from structural economic models, then fine-tunes on empirical data. Applied to option pricing, the hybrid model substantially outperforms both pure structural and purely data-driven benchmarks, with especially large gains in small samples and under market instability. Introduces a "data-model complementarity" metric to compare structural models. This is the closest existing paper in spirit — theory informs ML learning — but uses pre-training/transfer learning rather than penalization in the RKHS. The conceptual contribution overlaps with ours (misspecified theory still helps), though the implementation is entirely different.
**Identification:** Transfer learning (pre-training on structural model synthetic data, fine-tuning on empirical data); out-of-sample comparison.
**Data:** OptionMetrics implied volatility data; synthetic data from Black-Scholes and Heston models.
**Key Result:** Theory-guided ML outperforms both structural and purely data-driven approaches; model complementarity metric diagnoses theory quality.

---

## SAME METHOD, DIFFERENT CONTEXT (Proximity 3)

---

### [Barillas, Shanken 2018] Comparing Asset Pricing Models
**Journal/Source:** Journal of Finance, vol. 73(2), pp. 715–754
**Proximity Score:** 3/5
**Summary:** Derives a Bayesian asset pricing test computed from the standard GRS F-statistic. Develops a procedure to compute posterior model probabilities for all possible pricing models based on subsets of candidate factors. Applied to recent factor models (Hou-Xue-Zhang, Fama-French 5), finding these are dominated by models including momentum and updated value/profitability. Related because our paper produces an empirical ranking of economic theories by out-of-sample forecasting value — Barillas-Shanken do a related exercise for linear factor models via Bayesian model selection.
**Identification:** Bayesian model comparison; closed-form posterior probability from GRS F-statistic; diffuse priors on betas and residual covariance.
**Data:** 25 and 100 Fama-French portfolios; US equities; 1972–2013.
**Key Result:** Models including momentum and monthly-updated value/profitability factors dominate recent competing specifications.

---

### [Barillas, Kan, Robotti, Shanken 2020] Model Comparison with Sharpe Ratios
**Journal/Source:** Journal of Financial and Quantitative Analysis, vol. 55(6), pp. 1840–1874
**Proximity Score:** 3/5
**Summary:** Develops asymptotically valid tests of model comparison when the extent of model mispricing is gauged by the squared Sharpe ratio improvement. Substitutes mimicking portfolios for non-traded factors and accounts for estimation error in portfolio weights. Extends the GRS test to non-nested model comparisons. Related because our paper ranks structural restrictions/models by their contribution to out-of-sample prediction — this paper provides the formal testing framework for doing so in terms of Sharpe ratios.
**Identification:** Asymptotic inference on Sharpe ratio differences; HAC standard errors; mimicking portfolio construction.
**Data:** 25 Fama-French portfolios; various factor models; 1963–2012.
**Key Result:** A variant of Fama-French (2018) 6-factor model with monthly-updated value spread emerges as dominant.

---

### [Kan, Robotti, Shanken 2013] Pricing Model Performance and the Two-Pass Cross-Sectional Regression Methodology
**Journal/Source:** Journal of Finance, vol. 68(6), pp. 2617–2649
**Proximity Score:** 3/5
**Summary:** Derives the asymptotic distribution of cross-sectional regression R2 and develops tests for comparing model fit between two competing beta pricing models, accounting for model misspecification and estimation error. Finds that large R2 differences are often not statistically significant. Related because our paper uses penalty weights (mu_j) to rank structural restrictions by predictive value — this paper develops the formal statistical framework for comparing model fit metrics.
**Identification:** Asymptotic distribution of cross-sectional R2; Hansen-Jagannathan distance; tests for equal R2 between non-nested models.
**Data:** 25 Fama-French portfolios; 1963–2010.
**Key Result:** Many commonly used models are statistically indistinguishable in cross-sectional fit; ICAPM-type model performs best.

---

### [Feng, Giglio, Xiu 2020] Taming the Factor Zoo: A Test of New Factors
**Journal/Source:** Journal of Finance, vol. 75(3), pp. 1327–1370
**Proximity Score:** 3/5
**Summary:** Proposes a model-selection method to evaluate the marginal contribution of any new factor to asset pricing, above and beyond what a high-dimensional set of existing factors explains. Accounts for model selection error unlike standard approaches. Finds most proposed new factors are redundant relative to a core set of existing factors. Related because our paper implicitly does a similar exercise for structural restrictions rather than observable factors — we rank theories by their incremental predictive value.
**Identification:** LASSO-based model selection; double-selection (Belloni-Chernozhukov-Hansen) to account for model selection mistakes; out-of-sample evaluation.
**Data:** 150+ candidate factors; CRSP/Compustat; 1967–2017.
**Key Result:** Most new proposed factors are redundant; profitability has statistically significant incremental explanatory power.

---

### [Harvey, Liu, Zhu 2016] ...and the Cross-Section of Expected Returns
**Journal/Source:** Review of Financial Studies, vol. 29(1), pp. 5–68
**Proximity Score:** 3/5
**Summary:** Addresses the multiple testing problem in factor discovery. Documents 316 factors proposed in the literature by 2012 and develops a framework for adjusting significance thresholds over time given data-snooping concerns. Argues that a newly discovered factor should clear a t-ratio of 3.0 rather than 2.0. Related as a foundational reference for the factor zoo problem that our theory-ranking exercise helps address.
**Identification:** Multiple testing corrections (Bonferroni, Benjamini-Hochberg, Bayesian); time series of historical significance thresholds.
**Data:** Literature survey of 316 factors; various datasets.
**Key Result:** The significance threshold for new factors should be t > 3.0 given the accumulated data mining in the literature.

---

### [Giglio, Xiu 2021] Asset Pricing with Omitted Factors
**Journal/Source:** Journal of Political Economy, vol. 129(7), pp. 1947–1990
**Proximity Score:** 3/5
**Summary:** Proposes a three-pass method to estimate the risk premium of an observable factor even when not all factors in the true model are observed. Bias from omitted factors in standard two-pass regressions is eliminated by exploiting the factor structure among test assets. Related because our structural restrictions effectively impose constraints that help identify the true SDF structure even when the true model is unknown — this paper formalizes the omitted factor problem that our approach sidesteps.
**Identification:** Three-pass estimation; principal components to control for latent factors; asymptotic theory.
**Data:** 25 Fama-French portfolios; 1963–2016.
**Key Result:** Standard estimators are significantly biased when factors are omitted; three-pass method recovers consistent risk premium estimates.

---

### [Gospodinov, Kan, Robotti 2019] Too Good to Be True? Fallacies in Evaluating Risk Factor Models
**Journal/Source:** Journal of Financial Economics, vol. 132(2), pp. 451–471
**Proximity Score:** 3/5
**Summary:** Demonstrates that spurious factors (those uncorrelated with test asset returns) lead to perfect model fit in cross-sectional regressions — models with useless factors achieve arbitrarily high R2 and pass specification tests with probability approaching the nominal size. Related as a key reference for why naive model comparison via in-sample fit is misleading; our approach uses out-of-sample criteria and cross-validated penalty weights to guard against this problem.
**Identification:** Asymptotic theory for misspecified models with irrelevant factors; Monte Carlo simulations.
**Data:** Monte Carlo; empirical illustrations with US equities.
**Key Result:** Spurious factors are selected with high probability in cross-sectional regressions; perfect fit is achievable with useless factors.

---

### [Gu, Kelly, Xiu 2021] Autoencoder Asset Pricing Models
**Journal/Source:** Journal of Econometrics, vol. 222(1), pp. 429–450
**Proximity Score:** 3/5
**Summary:** Retrofits autoencoder neural networks to asset pricing, allowing latent factors and factor exposures to depend nonlinearly on asset characteristics. Imposes the no-arbitrage restriction as a constraint in the learning algorithm. The economic restriction (no-arbitrage) allows the autoencoder to detect the underlying SDF structure where off-the-shelf prediction fails. Closely related because it uses an economic constraint (no-arbitrage) embedded in a nonlinear estimator to improve prediction — the same conceptual approach as our paper, but via autoencoder rather than kernel ridge regression.
**Identification:** Autoencoder neural network with no-arbitrage criterion; out-of-sample evaluation.
**Data:** CRSP/Compustat; 94 characteristics; 1962–2019.
**Key Result:** Autoencoder with no-arbitrage restriction outperforms benchmark factor models and unconstrained ML methods in out-of-sample pricing errors.

---

## SAME CONTEXT, DIFFERENT METHOD (Proximity 3)

---

### [Filipovic, Pelger, Ye 2022] Shrinking the Term Structure
**Journal/Source:** NBER Working Paper No. 32472 (2024); Swiss Finance Institute Research Paper 22-61; R&R Review of Finance
**Proximity Score:** 3/5
**Summary:** Proposes a framework to explain the factor structure in the full cross-section of Treasury bond returns, unifying non-parametric curve estimation with cross-sectional factor modeling. Identifies smoothness as a fundamental principle of the term structure of returns. Directly related because it applies RKHS/kernel smoothing methods to financial cross-sections (bond returns) and imposes economic structure (yield curve smoothness) as a constraint on the estimator — an analogous application to ours for equity returns.
**Identification:** Kernel-based nonparametric curve estimation; factor structure for bond returns; smoothness penalties.
**Data:** Treasury bond returns; CRSP bond data.
**Key Result:** Smoothness is a fundamental principle; the framework unifies curve fitting and factor modeling for Treasury bonds.

---

### [Lewellen, Nagel, Shanken 2010] A Skeptical Appraisal of Asset Pricing Tests
**Journal/Source:** Journal of Financial Economics, vol. 96(2), pp. 175–194
**Proximity Score:** 3/5
**Summary:** Documents that standard asset pricing tests using characteristic-sorted portfolios lack power because the portfolios have a strong factor structure driven by the same characteristics used to sort them. Proposes improvements: include portfolios sorted on independent characteristics, impose restrictions on risk premia from theory (e.g., zero-beta rate close to risk-free rate), and report confidence intervals. Related as the key reference for why theory-based restrictions (as imposed in our paper) improve the credibility and power of asset pricing tests.
**Identification:** Cross-sectional regression; Monte Carlo power analysis; critique of standard test design.
**Data:** 25 and 100 Fama-French portfolios; US equities; 1964–2004.
**Key Result:** Standard tests have very low power to distinguish true from false models; small cross-sectional R2 differences are not statistically significant.

---

## THEORETICAL FOUNDATIONS (Proximity 1–2)

---

### [Cochrane 2011] Presidential Address: Discount Rates
**Journal/Source:** Journal of Finance, vol. 66(4), pp. 1047–1108
**Proximity Score:** 2/5
**Summary:** AFA Presidential Address surveying the field's shift from average returns to discount rate variation as the central organizing question. Documents that all price-dividend variation corresponds to discount-rate variation, and discusses how this shapes portfolio theory, cost of capital, and macro-finance. Provides the intellectual motivation for studying structural models of the SDF, which are the source of our penalty restrictions.
**Identification:** Theoretical synthesis; empirical documentation of discount rate variation.
**Data:** Survey; US equities and macroeconomic aggregates.
**Key Result:** Discount rate variation dominates cash-flow news in driving equity returns; understanding SDFs is central to finance.

---

### [Ferson, Nallareddy, Xie 2013] The "Out-of-Sample" Performance of Long-Run Risk Models
**Journal/Source:** Journal of Financial Economics, vol. 107(3), pp. 537–556
**Proximity Score:** 2/5
**Summary:** Studies the ability of long-run risk models (Bansal-Yaron type) to explain out-of-sample asset returns during 1931–2009. Finds that long-run risk models perform relatively well on the momentum effect, with cointegrated versions outperforming stationary specifications. Directly relevant as the first systematic out-of-sample evaluation of structural consumption models — a precursor to our systematic cross-model ranking by out-of-sample fit.
**Identification:** Out-of-sample R2 evaluation; simulation from calibrated structural models; time-series consumption data.
**Data:** CRSP; NIPA aggregate consumption; 1931–2009.
**Key Result:** Long-run risk models have modest out-of-sample explanatory power; cointegration improves fit.

---

## METHODS PAPERS (Proximity 1–3)

---

### [Caner 2009] LASSO-Type GMM Estimator
**Journal/Source:** Econometric Theory, vol. 25(1), pp. 270–290
**Proximity Score:** 2/5
**Summary:** Proposes the first LASSO-type GMM estimator by adding a penalty term (with exponent < 1 to avoid asymptotic bias) to the GMM objective function. The estimator has the oracle property: it consistently selects correct moment conditions and achieves the efficiency of the GMM estimator using only valid moments. Related as the foundational reference for penalized GMM — the direct antecedent of our approach of adding structural restriction penalties to the kernel ridge regression objective.
**Identification:** Penalized GMM; LASSO-type penalty; oracle property theory.
**Data:** Monte Carlo; no primary empirical application.
**Key Result:** LASSO-type GMM consistently selects valid moments; achieves oracle efficiency.

---

### [Caner, Zhang 2014] Adaptive Elastic Net for Generalized Methods of Moments
**Journal/Source:** Journal of Business and Economic Statistics, vol. 32(1), pp. 30–47
**Proximity Score:** 2/5
**Summary:** Extends adaptive elastic net from linear regression to the GMM setting, allowing many structural parameters and instruments with collinearity. The method simultaneously performs model selection and parameter estimation in nonlinear moment condition models, with the oracle property. Related as a direct methodological precursor for penalized structural estimation — our approach adds elastic-net-type penalties from structural restrictions to the kernel estimator.
**Identification:** Adaptive elastic net GMM; oracle property; high-dimensional GMM.
**Data:** Monte Carlo; application to wage equations.
**Key Result:** Method achieves consistent variable selection and oracle-efficient parameter estimation in high-dimensional GMM.

---

### [Chernozhukov, Escanciano, Ichimura, Newey, Robins 2022] Locally Robust Semiparametric Estimation
**Journal/Source:** Econometrica, vol. 90(4), pp. 1501–1535
**Proximity Score:** 2/5
**Summary:** Provides a general construction of locally robust (orthogonal) moment functions for GMM, where first-step nonparametric estimation has no local effect on the identifying moments. Using orthogonal moments reduces model selection and regularization bias — crucial when first steps use machine learning. Directly relevant because our structural restrictions enter as penalized moment conditions; the orthogonalization results here inform how to ensure valid inference in our setting.
**Identification:** Locally robust moment construction; influence function adjustment; asymptotic theory.
**Data:** Theory paper; no primary empirical application.
**Key Result:** Adding influence function adjustments to GMM moments eliminates first-order bias from nonparametric first steps; debiased ML estimators are root-n consistent.

---

### [Ichimura, Newey 2022] The Influence Function of Semiparametric Estimators
**Journal/Source:** Quantitative Economics, vol. 13(1), pp. 29–61
**Proximity Score:** 2/5
**Summary:** Derives the influence function of semiparametric estimators that depend on nonparametric first steps, generalizing the Von Mises/Hampel calculation. Provides explicit influence functions for estimators satisfying exogenous or endogenous orthogonality conditions, generalizing the omitted variable bias formula. Useful for understanding the asymptotic behavior of our kernel ridge regression estimator when structural restrictions enter as soft constraints.
**Identification:** Influence function derivation; Gateaux derivative calculus; semiparametric efficiency bounds.
**Data:** Theory paper; no primary empirical application.
**Key Result:** Influence function equals a Gateaux derivative evaluated at a point mass; explicit formulas for common semiparametric models.

---

### [Kelly, Xiu 2023] Financial Machine Learning
**Journal/Source:** Foundations and Trends in Finance, vol. 13(3-4), pp. 205–363; also NBER WP 31502
**Proximity Score:** 2/5
**Summary:** Comprehensive survey of machine learning methods in financial markets, covering return prediction, factor models, portfolio choice, and SDF estimation. Provides the authoritative reference for situating our paper within the ML asset pricing literature. Discusses kernel methods, neural networks, and regularization in the context of financial applications.
**Identification:** Survey; covers OLS, LASSO/ridge, neural nets, kernel methods, and their financial applications.
**Data:** Survey across many datasets.
**Key Result:** ML methods systematically outperform linear benchmarks for return prediction; economic constraints improve generalization.

---

### [Giglio, Kelly, Xiu 2022] Factor Models, Machine Learning, and Asset Pricing
**Journal/Source:** Annual Review of Financial Economics, vol. 14, pp. 337–368
**Proximity Score:** 2/5
**Summary:** Surveys methodological contributions at the intersection of factor models and machine learning for asset pricing. Organized by primary objectives: estimating expected returns, latent factors, risk exposures, risk premia, and the SDF. Discusses a variety of asymptotic inference schemes. Provides essential context for situating our kernel-based approach within the broader ML factor model literature.
**Identification:** Survey; covers two-pass regression, principal components, LASSO, neural nets, kernel methods.
**Data:** Survey.
**Key Result:** ML methods subsume and extend classical factor models; economically motivated regularization improves out-of-sample performance.

---

## DATA AND MEASUREMENT (Proximity 2–3)

---

### [Menkveld et al. 2024] Nonstandard Errors
**Journal/Source:** Journal of Finance, vol. 79(3), pp. 2339–2390
**Proximity Score:** 2/5
**Summary:** Studies variation across 164 research teams testing six hypotheses on the same data sample, finding that "non-standard errors" — variation from researcher-specific choices in the evidence-generating process — are on par with standard errors. Has direct implications for how robust our theory-ranking exercise needs to be to researcher-specific implementation choices in computing structural restrictions.
**Identification:** Multi-team empirical study; 164 teams, same data; non-standard error quantification.
**Data:** Six financial datasets; 343 coauthors.
**Key Result:** Non-standard errors are sizeable; researcher choices in specification generate as much variation as sampling uncertainty.

---

## SCOOPING RISKS AND RECENT WORKING PAPERS (2024–2026)

---

### [Chen, Cheng, Liu, Tang 2026] Teaching Economics to the Machines — see full entry above
**Proximity Score:** 4/5 — Scooping Risk: Medium
**Overlap:** Theory informs ML; pre-training on structural model synthetic data; out-of-sample evaluation; "data-model complementarity" metric ranks theories. Differs from our paper: uses transfer learning/pre-training rather than penalization; applies to option pricing not equity cross-section; uses neural nets not KRR. Must be addressed head-on.

---

### [Filipovic, Pasricha 2022] Ensemble Gaussian Process Regression — see full entry above
**Proximity Score:** 4/5 — Scooping Risk: Low-Medium
**Overlap:** Uses kernel (GPR/KRR) methods for cross-sectional return prediction on CRSP. Differs: no structural restrictions imposed; ensemble approach rather than penalization; no theory-ranking exercise.

---

### [Bryzgalova, Huang, Julliard 2023] Bayesian Solutions for the Factor Zoo — see full entry above
**Proximity Score:** 5/5 — Scooping Risk: Medium
**Overlap:** Structured, heterogeneous shrinkage of factor contributions; empirical ranking of economic models by data-model fit; Bayesian model averaging. Differs: linear SDF framework (not nonparametric/kernel); observable factors (not structural restrictions from Euler equations); no RKHS.

---
