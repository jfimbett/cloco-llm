---
name: Theory-KRR Paper Conventions
description: Notation, style, and structural conventions for Theory-Informed KRR for Asset Pricing paper (Imbet & Andriollo)
type: project
---

Paper: "Theory-Informed Kernel Ridge Regression for Asset Pricing"
Authors: Juan F. Imbet, Amedeo Andriollo (Paris Dauphine University - PSL)

**Notation conventions established in framework.tex:**
- Returns: $R_{i,t+1}$ (excess), $R_{i,t+1}^{\mathrm{gross}}$ (gross)
- Characteristics: $\mathbf{X}_{i,t} \in \R^p$
- Stacked index: $s = (i,t)$, total $n = NT$
- RKHS: $\Hcal$ with kernel $k$, norm $\|f\|_{\Hcal}$
- Statistical penalty: $\lambda_{\mathrm{stat}}$
- Theory multipliers: $\mu_j$, grouped as $\mu_{g(j)}^{\mathrm{group}}$
- Kernel matrix: $\mathbf{K}$, coefficient vector: $\bm{\alpha}$
- Custom commands: \E, \R, \Hcal, \Kcal, \Fcal, \ind, \argmin, \argmax

**Penalty types:** A (Euler), B (Production FOC), C (Factor structure), D (Demand-system)
**60 restrictions in 8 families**

**Style:** author-year natbib citations (parenthetical), active voice, no hedging. Label conventions: eq:, sub:, tab:, prop:, def:, rem:, sec:

**Why:** Ensures notation consistency across sections drafted in different sessions.
**How to apply:** Match all symbols, label prefixes, and citation style exactly when drafting new sections.
