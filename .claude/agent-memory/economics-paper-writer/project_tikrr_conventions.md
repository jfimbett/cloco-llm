---
name: Theory-KRR paper conventions
description: Notation, citation style, and structural conventions for the Imbet-Andriollo Theory-KRR asset pricing paper
type: project
---

**Paper:** Theory-Informed Kernel Ridge Regression for Asset Pricing (Imbet & Andriollo, Paris Dauphine - PSL)

**Key notation:**
- Returns: $R_{i,t+1}$ (excess return), characteristics: $\mathbf{X}_{i,t}$
- RKHS: $\Hcal$ (via \Hcal), kernel matrix: $\mathbf{K}$
- Theory-KRR objective eq label: \eqref{eq:tikrr}
- Multipliers: $\mu_j$ individual, $\bm{\mu}$ vector, $\hat{\mu}_g$ group-level
- Statistical penalty: $\lambda_{\mathrm{stat}}$
- Penalty functionals: $C_j(f)$, four types (A=Euler, B=production FOC, C=factor, D=demand)
- Pre-estimated params: $\hat{\theta}_j$
- Custom commands: \E, \R, \Hcal, \Kcal, \Fcal, \ind, \argmin, \argmax

**Citation style:** Author-year inline (natbib, plainnat). No \cite{} used yet — all citations written inline as "Author (Year)".

**Section labels:** sec:introduction, sec:framework, sec:restrictions, sec:estimation, sec:empirical, sec:results, sec:conclusion

**60 restrictions in 8 groups:** Consumption (1-13), Production (14-23), Intermediary (24-31), Learning (32-37), Demand (38-43), Options (44-49), Behavioral (50-55), Macro (56-60)

**Why:** Needed for consistent notation/style when drafting or revising any section.
**How to apply:** Match all notation, label conventions, and citation format when writing new sections or revising existing ones.
