# Positioning Guide — Theories as Regularizers
**Project:** Theory-Informed KRR for Asset Pricing (Imbet & Andriollo, Paris Dauphine - PSL)
**Date:** 2026-03-14

---

## Suggested Contribution Statement

"This paper proposes a kernel ridge regression estimator for cross-sectional stock return prediction in which 50–60 structural restrictions from major asset pricing theories — including consumption-based, production-based, intermediary, demand-system, and behavioral models — enter as separately cross-validated soft penalty terms. We establish that economically motivated, theory-specific regularization dominates both isotropic shrinkage and theory-free nonparametric estimation in out-of-sample prediction, and we derive the first empirical ranking of entire economic model families by their marginal contribution to cross-sectional predictability. Our results reveal which theories are data-model complementary and which are redundant once others are included, providing a systematic, nonparametric counterpart to the Bayesian factor zoo literature."

---

## Key Differentiators from the 5 Most Similar Papers

### 1. Kozak, Nagel, Santosh (2020) — Shrinking the Cross-Section
**Their paper:** Economically motivated shrinkage of SDF coefficients; the penalty is proportional to the eigenvalue of characteristic PCs, motivated by no-arbitrage bounds on Sharpe ratios. Linear SDF with characteristics-based factors.
**Differentiators for our paper:**
- Our shrinkage is *structural*: each penalty corresponds to a specific Euler equation or equilibrium condition from a named economic theory, not a statistical criterion (PC eigenvalue).
- Our estimator is nonparametric (RKHS), not a linear SDF.
- We produce a theory-level ranking (which model family is most data-consistent), not just a PC-level ranking.
- We use cross-validated penalty weights (one per restriction), not a single shrinkage parameter calibrated from theory.

### 2. Bryzgalova, Huang, Julliard (2023) — Bayesian Solutions for the Factor Zoo
**Their paper:** Bayesian model averaging over 2.25 quadrillion linear SDF models formed by subsets of 51 observable factors; heterogeneous priors based on factor identification strength.
**Differentiators for our paper:**
- We use structural restrictions (Euler equations, FOCs) as penalties, not observable factor returns.
- Our estimator is nonparametric (KRR), not a linear SDF.
- Our restriction weights are chosen by time-series cross-validation (an out-of-sample criterion), not by Bayesian posteriors.
- We produce a prediction-focused ranking (out-of-sample R2 contribution) rather than a model probability ranking (in-sample posterior).

### 3. Chen, Cheng, Liu, Tang (2026) — Teaching Economics to the Machines
**Their paper:** Theory-guided transfer learning; pre-trains neural nets on structural model synthetic data, then fine-tunes on empirical data; applied to option pricing.
**Differentiators for our paper:**
- We use soft penalization in the objective function, not pre-training; the structural content enters directly as penalty terms, not as a prior data-generating process for initialization.
- We target cross-sectional equity return prediction, not option pricing.
- Our base estimator is KRR (convex optimization, closed-form solution, representer theorem), not a neural network (non-convex, gradient descent, no closed form).
- Our framework produces a continuous structural contribution ranking (penalty weights mu_j) rather than a binary use/don't-use pre-training decision.
- KRR's convexity ensures global optima and tractable asymptotics; neural net pre-training is heuristic.

### 4. Filipovic, Pasricha (2022) — Ensemble Gaussian Process Regression
**Their paper:** Applies GPR (which is equivalent to KRR with a specific kernel) to CRSP cross-sectional return prediction; no economic constraints.
**Differentiators for our paper:**
- We add structural restrictions as penalty terms to the same base estimator (KRR = GPR).
- Our paper answers the question of whether structure adds value on top of the unconstrained kernel baseline — Filipovic-Pasricha is precisely the no-restriction benchmark against which our theory-informed version should be evaluated.
- We produce a theory ranking; they produce a portfolio performance evaluation.

### 5. Gu, Kelly, Xiu (2021) — Autoencoder Asset Pricing Models
**Their paper:** Embeds the no-arbitrage condition as a single adversarial training criterion in a neural network autoencoder.
**Differentiators for our paper:**
- We embed 50–60 *named structural restrictions* (not just no-arbitrage), each with its own penalty weight.
- Our base estimator is KRR (linear in the RKHS feature map), not an autoencoder neural network.
- Convexity of KRR allows closed-form solution and tractable inference; autoencoders require non-convex optimization with no guaranteed global optimum.
- We produce a theory-level empirical ranking; they show binary improvement from no-arbitrage vs. no constraint.

---

## Potential Target Journals

| Rank | Journal | Rationale |
|------|---------|-----------|
| 1 | **Review of Financial Studies (RFS)** | Has published both ML asset pricing (Gu-Kelly-Xiu 2020; Freyberger-Neuhierl-Weber 2020) and structural model comparisons; receptive to econometric innovation with financial application; Bryzgalova has published there. |
| 2 | **Journal of Finance (JF)** | Published Barillas-Shanken (2018), Kelly-Malamud-Zhou (2024), Bryzgalova-Huang-Julliard (2023), Feng-Giglio-Xiu (2020); all directly adjacent. High impact. Most competitive. |
| 3 | **Journal of Financial Economics (JFE)** | Published Kozak-Nagel-Santosh (2020); receptive to asset pricing methodology papers; strong empirical finance readership. |
| 4 | **Econometrica** | If the theoretical contribution (RKHS inference for multi-penalty structured estimators; asymptotic theory) is sufficiently developed, Econometrica is reachable. Published Singh-Vijaykumar-type KRR inference work. High bar. |
| 5 | **Journal of Econometrics / JBES** | Strong backup if journal-level positioning emphasizes the econometric methodology (structured penalization, CV theory) over the finance application. |

---

## Literature Gaps This Paper Fills

| Gap | How Our Paper Fills It |
|-----|----------------------|
| No existing paper ranks entire economic theory families (consumption, production, intermediary, behavioral) by out-of-sample predictive value | Our cross-validated penalty weights mu_j provide a direct ranking: theories with larger mu_j contribute more to prediction; we report a league table of theories. |
| Existing structured shrinkage (Kozak-Nagel-Santosh) is based on no-arbitrage PC eigenvalues, not named structural restrictions | Our penalties are derived from specific Euler equations and equilibrium conditions, making the restrictions interpretable and traceable to named economic models. |
| Bayesian factor zoo rankings (Bryzgalova-Huang-Julliard) are limited to observable factors in linear SDFs | We operate in the RKHS (nonlinear, nonparametric) and use structural restrictions rather than observable factor returns. |
| Kernel/GPR methods applied to equity returns (Filipovic-Pasricha) have no structural content | We augment the same base estimator with structural penalties and demonstrate whether and by how much theory adds value. |
| Theory-guided ML (Chen-Cheng-Liu-Tang) uses pre-training for options, not penalization for equity cross-section | We establish penalization as an alternative mechanism, with the advantage of convexity, closed-form solutions, and tractable asymptotics. |

---

## Risks: Papers That Must Be Addressed Head-On

### Risk 1 (High): Chen, Cheng, Liu, Tang (2026) — Teaching Economics to the Machines
**Why it must be addressed:** This is the closest paper in spirit (theory informs ML; structural restrictions guide a flexible estimator) and is a January 2026 NBER working paper — very recent. Referees will ask: "How is this different from Chen et al. (2026)?"
**Recommended framing:** Our paper and Chen et al. are complementary explorations of the same general principle. Chen et al. use pre-training (theory generates synthetic data for initialization); we use penalization (theory generates soft constraints in the objective). Penalization has three advantages: (1) convexity guarantees global optimum; (2) penalty weights mu_j are directly interpretable as theory-contribution scores; (3) cross-validated penalty selection is an out-of-sample criterion, making the theory ranking directly tied to predictive performance.

### Risk 2 (Medium): Bryzgalova, Huang, Julliard (2023) — Bayesian Factor Zoo
**Why it must be addressed:** This paper produces the closest existing empirical output to ours — an empirical ranking of economic models. Referees may ask: "This is just Bryzgalova-Huang-Julliard with a different estimator."
**Recommended framing:** The key difference is the object being ranked: Bryzgalova et al. rank observable factor portfolios in a linear SDF; we rank structural restrictions from named theoretical models in a nonparametric RKHS. The identification argument is also different: their priors are driven by factor identification strength; our penalty weights are driven by out-of-sample prediction.

### Risk 3 (Low): Filipovic, Pasricha (2022) — Ensemble Gaussian Process Regression
**Why it must be addressed:** Uses the same base estimator (GPR = KRR) on the same data; could be seen as a subset of our contribution.
**Recommended framing:** Filipovic-Pasricha is our no-restriction benchmark. We show that adding structural penalties to their estimator provides additional predictive value, making our paper an extension rather than a competitor.
