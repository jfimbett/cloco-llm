---
name: Lit Review Scoring Calibration
description: Patterns and calibration notes for scoring literature reviews in ML asset pricing / financial econometrics papers
type: feedback
---

## Recurring gaps in ML asset pricing literature reviews

1. **RKHS foundational references often missing.** Papers that use kernel methods routinely omit Scholkopf-Smola (2002), Wahba (1990), Kimeldorf-Wahba (1971). Flag this whenever a paper invokes the representer theorem without citing the original.

2. **Transfer learning strand thin when papers claim theory-ML complementarity.** Papers positioned at the theory+ML intersection often cite domain-specific transfer learning work but miss the canonical survey (Pan-Yang 2010 IEEE TKDE).

3. **Fama-French factor model originals assumed but not cited.** Papers discussing the factor zoo or model comparison often reference downstream work (Barillas-Shanken, Feng-Giglio-Xiu) without citing Fama-French (2015) five-factor model or (2018) choosing factors.

4. **Working paper concentration acceptable at the frontier.** For papers at the ML+theory intersection as of 2026, a significant fraction of the most relevant references (Babii-Ghysels-Striaukas, Singh-Vijaykumar, LLM-Lasso, Chen-Cheng-Liu-Tang) are working papers. This is normal and should not be penalized heavily, but should be flagged for monitoring.

## Score calibration

- A well-executed gap-fill of 20-25 papers on top of 80+ existing refs, with correct proximity scores and good frontier identification, scores 80-85 at Discovery severity.
- Missing a single seminal paper (e.g., Kozak-Nagel-Santosh for structured shrinkage) would drop the score by 15-20 points.
- Incomplete BibTeX entries are a -5 per paper at Discovery; escalate to -10 at Execution.

**Why:** These patterns recur across ML asset pricing papers and should be checked proactively.
**How to apply:** At the start of any lit review scoring for a kernel/RKHS finance paper, check for items 1-3 above before reading the bibliography in detail.
