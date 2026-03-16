# Editor Review — Literature Collection for "Theories as Regularizers"
**Date:** 2026-03-14
**Mode:** Lit Critic (Phase 1 — Discovery, ENCOURAGING severity)
**Score:** 82/100
**Decision:** PASS

## Executive Summary

The combined literature collection (82 existing references + 25 gap-filling papers = 107 total) provides strong coverage of the core strands needed for this paper. The gap-filling search successfully identified the most critical missing papers -- particularly Kozak-Nagel-Santosh (2020), Bryzgalova-Huang-Julliard (2023), Kelly-Malamud-Zhou (2024), and Freyberger-Neuhierl-Weber (2020) -- whose absence would have been immediately noticed by any referee at a top finance journal. The frontier map and positioning guide are well-constructed and correctly identify the paper's unique contribution. Several gaps remain, mostly in the transfer learning / domain adaptation strand and in RKHS theory foundations, but none are fatal at the Discovery phase.

## Issues Found

### 1. Transfer Learning / Domain Adaptation Strand Thin — Severity: Medium — Deduction: -5

The annotated bibliography includes Chen-Cheng-Liu-Tang (2026) as the sole transfer learning reference. The paper claims to be the "function-space analog of the LLM-Lasso" and the "economic-theory counterpart to transfer learning." A referee will expect to see references to the broader transfer learning and domain adaptation literature as applied to econometrics/finance. Missing papers include:

- **Pan and Yang (2010)** "A Survey on Transfer Learning" (IEEE TKDE) -- the canonical survey that defines the taxonomy (inductive, transductive, unsupervised) your positioning implicitly invokes.
- **Horel and Giesecke (2021)** "Significance Tests for Neural Network Classifiers" (Information Sciences) or similar work on structured regularization in deep learning for finance -- connects your penalization approach to the neural net literature.

This is not a severe gap because the paper's core positioning is in asset pricing and kernel methods, not in the ML transfer learning literature per se. But one or two well-chosen references from the broader domain adaptation literature would preempt a referee asking "why do you call this transfer learning without citing the transfer learning literature?"

### 2. RKHS / Kernel Theory Foundations Missing from Gap-Fill — Severity: Medium — Deduction: -5

The existing bib includes Babii-Ghysels-Striaukas (2024) and Singh-Vijaykumar (2023/2025) for structural kernel econometrics and KRR inference. The gap-fill search adds Filipovic-Pasricha (2022) for GPR in finance. However, foundational RKHS references are absent from both the existing bib and the gap-fill:

- **Scholkopf and Smola (2002)** "Learning with Kernels" (MIT Press) -- the standard RKHS/kernel methods textbook. If you invoke the representer theorem, you cite this book.
- **Wahba (1990)** "Spline Models for Observational Data" (SIAM) -- the foundational reference for reproducing kernel Hilbert spaces in statistics and the representer theorem.
- **Kimeldorf and Wahba (1971)** "Some Results on Tchebycheffian Spline Functions" (JMAA) -- the original representer theorem proof.

These are textbook references that take 3 lines in the bibliography. Their absence would look odd to an econometrics referee who works with RKHS methods.

### 3. Cheng-Liao (2015) Referenced in Frontier Map But Not in Bibliography — Severity: Low — Deduction: -3

The frontier map (line 20) references "Cheng-Liao 2015" as part of the penalized GMM strand. This paper does not appear in either `paper/references.bib` or `quality_reports/literature/theories-as-regularizers/references.bib`. This is likely Cheng, Liao (2015) "Select the Valid and Relevant Moments: An Information-Based LASSO for GMM with Many Moments" (Journal of Econometrics). If it is cited in the frontier map, it needs a BibTeX entry.

### 4. Working Paper Ratio Acceptable But Worth Monitoring — Severity: Low — Deduction: -2

Across the combined 107 entries, approximately 11 in the existing bib are working papers (Bianchi-Rubesam-Tamoni 2024; Chen 2025; Bybee-Kelly-Manela-Xiu 2025; Babii-Ghysels-Striaukas 2024; Singh-Vijaykumar 2025; Bryzgalova-Pelger-Zhu 2023; Gabaix-Koijen-Richmond-Yogo 2024; Gabaux-Koijen 2021; Escanciano et al. 2016; Bekaert-Engstrom 2010; plus 3 in the gap-fill: Chen-Cheng-Liu-Tang 2026, Filipovic-Pasricha 2022, Filipovic-Pelger-Ye 2024). That is roughly 14/107 = 13%, well under the 50% threshold. However, several of the most important references for the paper's contribution (Babii-Ghysels-Striaukas, Singh-Vijaykumar, Chen-Cheng-Liu-Tang, LLM-Lasso) are working papers. This is acceptable because the paper sits at a frontier where published work does not yet exist, but it should be noted: if these papers are rejected or substantially revised, the positioning may need updating.

### 5. No Fama-French (2015/2018) in Existing Bib — Severity: Low — Deduction: -3

The existing bibliography includes Hou-Xue-Zhang (2015) for production-based factor models but does not include Fama-French (2015) "A Five-Factor Model" (JFE) or Fama-French (2018) "Choosing Factors" (JFE). These are among the most cited papers in the cross-section of returns literature. Any paper that discusses "the factor zoo" or ranks economic models against each other will be expected to reference the Fama-French factor models explicitly. The Barillas-Shanken (2018) and Barillas-Kan-Robotti-Shanken (2020) entries in the gap-fill discuss Fama-French models but do not substitute for citing the original papers.

## Score Breakdown

- Starting: 100
- Transfer learning / domain adaptation strand thin: -5
- RKHS / kernel theory foundations missing: -5
- Cheng-Liao (2015) referenced but no BibTeX: -3
- Working paper concentration at the frontier: -2
- Missing Fama-French (2015/2018): -3
- **Final: 82/100**

## Required Actions

1. **Add 1-2 transfer learning references.** At minimum, add Pan and Yang (2010) to the bibliography as a background reference. If a finance-specific domain adaptation paper exists (beyond Chen et al. 2026), add it.

2. **Add RKHS foundational references.** Add Scholkopf and Smola (2002) and either Wahba (1990) or Kimeldorf and Wahba (1971). These are standard textbook citations that take 30 seconds each.

3. **Create a BibTeX entry for Cheng and Liao (2015)** or remove the reference from the frontier map. Do not leave a cited paper without a corresponding BibTeX entry.

4. **Add Fama and French (2015) and optionally Fama and French (2018).** These are standard references in any paper that discusses the cross-section of returns. The existing bib has the investment-based counterpart (Hou-Xue-Zhang 2015) but not the Fama-French originals.

5. **No other action required.** The remaining gaps (working paper ratio, geographic scope) are acceptable at this phase and severity level.

## What Was Done Well

1. **The gap-filling search identified the right papers.** Kozak-Nagel-Santosh (2020), Bryzgalova-Huang-Julliard (2023), and Kelly-Malamud-Zhou (2024) are precisely the papers whose absence would have been most damaging. Finding and annotating these was the most important task of this search.

2. **Proximity scoring is well-calibrated.** The 5/5 scores for Kozak-Nagel-Santosh and Bryzgalova-Huang-Julliard are correct -- these are the closest existing papers to your contribution. The 4/5 scores for Filipovic-Pasricha, Kelly-Malamud-Zhou, Chen-Cheng-Liu-Tang, and Freyberger-Neuhierl-Weber are appropriate: all are directly related but differ in estimator, data, or constraint type.

3. **The frontier map correctly identifies the novelty.** The statement that "no existing paper ranks entire economic theory families by out-of-sample predictive value" in the RKHS is accurate and well-supported by the literature review. The three-strand intersection (kernel methods + economic constraints + non-isotropic shrinkage) is clearly articulated.

4. **Scooping risk assessment is realistic.** The Chen-Cheng-Liu-Tang (2026) risk is correctly rated Medium-High (not High) because the method and domain differ. The Bryzgalova-Huang-Julliard (2023) risk is correctly rated Medium because the framework is linear and Bayesian rather than nonparametric and frequentist. The Filipovic-Pasricha (2022) risk is correctly rated Low-Medium as a no-restriction baseline.

5. **Positioning guide differentiators are sharp.** The 5-paper positioning table clearly articulates what is different about this paper relative to each competitor. The recommended framings for addressing scooping risks in the paper text are practical and persuasive.

6. **BibTeX entries are complete.** All 25 gap-filling entries have full citation information (volume, pages, DOI, URL). No truncated or placeholder entries.

7. **The existing bibliography is remarkably comprehensive.** 82 entries covering consumption, production, intermediary, demand-system, behavioral, learning, option-implied, and macro-finance models is an excellent foundation. The structural model coverage is a strength.

---

**Reviewer:** Academic Editor (Lit Critic mode)
**Severity level applied:** Encouraging (Discovery phase)
**Next step:** Librarian addresses the 4 actionable items above. No full re-review required -- a quick verification that the BibTeX entries have been added is sufficient.
