# Frontier Map — Theories as Regularizers
**Project:** Theory-Informed KRR for Asset Pricing (Imbet & Andriollo, Paris Dauphine - PSL)
**Date:** 2026-03-14
**Scope:** Gap-filling synthesis only. The existing 80+ references are taken as a baseline.

---

## What Has Been Established

### ML Prediction Without Theory
The ML asset pricing literature (Gu-Kelly-Xiu 2020; Kelly-Pruitt-Su 2019; Chen-Pelger-Zhu 2024) has firmly established that nonlinear, high-dimensional ML methods systematically outperform linear benchmarks for cross-sectional return prediction on CRSP data. Kelly-Malamud-Zhou (2024) has further proven theoretically that complex (overparameterized) models are not penalized by the benign overfitting phenomenon and systematically outperform simpler models.

### Theory + Statistics as Complements
The emerging consensus (Bianchi-Rubesam-Tamoni 2024; Chen et al. 2025; LLM-Lasso 2025; Chen-Cheng-Liu-Tang 2026) is that incorporating economic structure into ML estimation improves out-of-sample performance, particularly in small samples and under distributional instability. The mechanisms explored include: structured priors (Kozak-Nagel-Santosh 2020), Bayesian model averaging with identification-strength-based priors (Bryzgalova-Huang-Julliard 2023), no-arbitrage adversarial training (Gu-Kelly-Xiu 2021; Chen-Pelger-Zhu 2024), and pre-training on theory-generated synthetic data (Chen-Cheng-Liu-Tang 2026).

### Factor Zoo and Model Selection
The factor zoo literature (Harvey-Liu-Zhu 2016; Feng-Giglio-Xiu 2020; Barillas-Shanken 2018; Bryzgalova-Huang-Julliard 2023) has documented severe data snooping and factor redundancy. Methods for formal model comparison (Kan-Robotti-Shanken 2013; Barillas-Kan-Robotti-Shanken 2020) and for handling spurious factors (Gospodinov-Kan-Robotti 2019; Giglio-Xiu 2021) have been developed for the linear SDF setting.

### Penalized Nonparametric Estimation
Nonparametric methods have been applied to the cross-section with economic constraints: shape-restricted nonparametric estimation via adaptive group LASSO (Freyberger-Neuhierl-Weber 2020), smoothness-penalized kernel estimation for bond returns (Filipovic-Pelger-Ye 2022), and structural penalties in kernel econometrics (Babii-Ghysels-Striaukas 2024). Penalized GMM with oracle properties has been developed (Caner 2009; Caner-Zhang 2014; Cheng-Liao 2015).

---

## Methodological Frontier

The frontier sits at the intersection of three strands:
1. **Kernel/RKHS methods for finance** — GPR applied to equity returns (Filipovic-Pasricha 2022); kernel-based term structure estimation (Filipovic-Pelger-Ye 2022); structural kernel econometrics (Babii-Ghysels-Striaukas 2024).
2. **Economic constraints in nonlinear ML** — no-arbitrage adversarial objectives (Gu-Kelly-Xiu 2021; Chen-Pelger-Zhu 2024); physics-informed neural nets for option pricing (arXiv 2023–2024); pre-training on structural synthetic data (Chen-Cheng-Liu-Tang 2026).
3. **Non-isotropic, theory-motivated shrinkage** — PC-based shrinkage motivated by no-arbitrage (Kozak-Nagel-Santosh 2020); identification-strength-based Bayesian priors (Bryzgalova-Huang-Julliard 2023); structured priors from LLM-based theory extraction (Bybee-Kelly-Manela-Xiu LLM-Lasso 2025).

**What does not yet exist:** A unified framework that (a) uses kernel ridge regression (RKHS) as the base estimator, (b) embeds 50–60 structural restrictions from multiple economic model families as separate, cross-validated soft penalty terms, and (c) produces a data-driven empirical ranking of entire economic theories (not just factors or model configurations) by their marginal contribution to out-of-sample return prediction.

---

## Data Frontier

- **CRSP monthly** remains the standard dataset for US equity cross-sections; most ML papers use 1962–2016 or similar.
- **Compustat annual/quarterly** for firm characteristics.
- **French Library** for factor returns and test portfolios.
- **NIPA/BEA** for aggregate consumption (required for consumption restriction testing).
- **He-Kelly-Manela intermediary factor** for intermediary restrictions.
- **OptionMetrics** for option-implied state variables used in Chen-Cheng-Liu-Tang (2026) type applications.
- The novel data frontier for our paper is the **construction of restriction-specific penalty terms**: for each of 50–60 structural restrictions, the implied characteristic or moment condition must be computed from the appropriate dataset. This data pipeline (linking CRSP, Compustat, NIPA, intermediary data, and option data to restriction computations) does not exist as a single integrated resource.

---

## Geographic / Contextual Gaps

- All frontier papers focus on **US equities (CRSP universe)**. International equity applications of theory-informed ML are essentially absent.
- **Bond markets:** Filipovic-Pelger-Ye (2022) applies smoothness-penalized kernel methods to Treasury bonds but does not embed structural model restrictions.
- **Options:** Chen-Cheng-Liu-Tang (2026) uses structural models for option pricing, but not for cross-sectional equity prediction.
- **Emerging markets / non-US:** no existing work on theory-informed penalized estimation outside the US equity context.

---

## Open Questions

1. **Which economic theories have positive out-of-sample value?** The Bryzgalova-Huang-Julliard (2023) ranking is over observable factors in linear SDFs; no existing paper ranks entire structural model families (consumption, production, intermediary, behavioral) by out-of-sample predictive value.
2. **Do theory restrictions improve predictability or are they just regularization?** The question of whether structural content (beyond ridge-equivalent isotropic shrinkage) provides additional predictive value is open.
3. **What is the right inferential framework for RKHS with multiple structured penalties?** Singh-Vijaykumar (2023/2025) provide inference for single-penalty KRR; the multi-penalty, cross-validated case with 50–60 penalty parameters lacks asymptotic theory.
4. **How sensitive are theory rankings to calibration noise?** Pre-estimated structural parameters (risk aversion, EIS, etc.) are noisy; the propagation of calibration uncertainty to penalty weights and theory rankings is unsolved.
5. **Does theory-informed regularization dominate theory-uninformed regularization economically?** Kelly-Malamud-Zhou (2024) shows complexity helps; the incremental value of structure over isotropic complexity is not established empirically.
6. **Robustness of model rankings to non-standard errors (Menkveld et al. 2024):** With many researcher degrees of freedom in computing 50–60 restriction types, how stable is the empirical ranking?

---

## Where This Project Fits

"Theories as Regularizers" occupies a gap at the exact intersection of nonparametric kernel methods and structural economic theory: it is the first paper to embed many structural model families simultaneously as separate soft penalties in an RKHS estimator and to derive a data-driven ranking of those theories by out-of-sample predictive value. Relative to Kozak-Nagel-Santosh (2020) and Bryzgalova-Huang-Julliard (2023), the paper moves from observable factor shrinkage to structural restriction penalization in a nonparametric RKHS. Relative to Chen-Cheng-Liu-Tang (2026), the paper uses soft penalization rather than pre-training and targets the cross-sectional equity prediction problem rather than option pricing.

---

## Scooping Risks

| Paper | Authors | Date | Overlap | Risk Level |
|-------|---------|------|---------|------------|
| Teaching Economics to the Machines | Chen, Cheng, Liu, Tang | Jan 2026 | Theory informs ML; structural restrictions improve prediction; out-of-sample evaluation; "data-model complementarity" ranks theories | **Medium-High** — Same conceptual question (theory as a guide for ML), applied to option pricing with a different method (transfer learning / pre-training). Must be addressed explicitly. Framing: our paper is complementary (RKHS + equity cross-section vs. neural net + options). |
| Bayesian Solutions for the Factor Zoo | Bryzgalova, Huang, Julliard | 2023 (JF) | Structured heterogeneous shrinkage; empirical ranking of economic models; Bayesian model averaging | **Medium** — Same empirical output (ranking of models) but linear SDF framework and observable factors, not RKHS and structural restrictions. Must be discussed as the linear-SDF precedent. |
| Ensemble Gaussian Process Regression | Filipovic, Pasricha | 2022 (arXiv, ongoing revision) | GPR/KRR applied to CRSP equity return prediction; out-of-sample evaluation | **Low-Medium** — Uses the same base estimator (GPR = KRR) on the same data, but with no structural restrictions. Our paper would dominate theirs if theory restrictions add value. Must be included as the no-restriction benchmark. |
| Shrinking the Term Structure | Filipovic, Pelger, Ye | 2022/2024 (NBER, R&R Review of Finance) | Smoothness-penalized kernel estimation for financial cross-sections | **Low** — Different asset class (bonds); smoothness restriction is a mathematical regularity condition, not a structural economic model. Methodologically related but not competing. |
