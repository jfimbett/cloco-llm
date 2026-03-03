---
name: theory-model
description: Develop formal theoretical models in economics or finance by dispatching the econ-finance-theorist agent. Derives formal frameworks, proofs, equilibrium conditions, and pricing theories. Use when asked to "build a model", "formalize the intuition", "derive equilibrium", or "write the theory section".
disable-model-invocation: true
argument-hint: "[research question or intuition to formalize]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Edit", "Task", "WebSearch"]
---

# Theory Model

Develop a formal theoretical model by dispatching the **econ-finance-theorist** agent.

**Input:** `$ARGUMENTS` — the research question, economic intuition, or modeling objective to formalize.

---

## Workflow

### Step 1: Gather Context

Before launching the agent:
1. Read `paper/main.tex` if it exists — understand what the paper's empirical strategy implies about the theory
2. Read `.claude/rules/domain-profile.md` — field conventions, notation standards, seminal references
3. Read any existing strategy memos in `quality_reports/` — the theory should motivate the empirics
4. Check `quality_reports/literature/` for theoretical papers already identified

### Step 2: Launch econ-finance-theorist Agent

Delegate to the `econ-finance-theorist` agent via Task tool:

```
Prompt: Develop a formal theoretical model for [research question / intuition].

Context:
- Field: [from domain-profile.md]
- Empirical strategy: [from strategy memo if available]
- Notation conventions: [from domain-profile.md]
- Seminal theoretical references: [from frontier_map.md if available]

Deliverables:
1. Model setup — environment, agents, timing
2. Equilibrium definition and existence
3. Key propositions (with proofs or proof sketches)
4. Comparative statics linking theory to empirical predictions
5. LaTeX-ready formal write-up

Save to: quality_reports/theory_model_[date].md
Also save LaTeX section to: paper/sections/theory.tex (if paper exists)
```

### Step 3: Theory-Empirics Alignment Check

After the econ-finance-theorist returns, verify:
- [ ] Model generates at least one testable prediction that matches the paper's main estimand
- [ ] Notation in the model is consistent with `domain-profile.md` conventions
- [ ] Key assumptions are stated clearly (not buried in proofs)
- [ ] Comparative statics have the correct sign relative to reduced-form findings

If misaligned with the empirical strategy, flag for the user — the model may need adjustment or the empirical strategy memo may need updating.

### Step 4: Optional — econometrics-critic Review

For papers where the theory is central to identification (e.g., structural models, moment conditions from theory), optionally dispatch the `econometrics-critic` to verify:
- The model's moment conditions are correctly derived
- The theoretical predictions are testable given the data
- The assumptions are defensible

### Step 5: Present Results

```markdown
## Theory Model: [Research Question]
**Date:** YYYY-MM-DD
**Agent:** econ-finance-theorist

### Model Summary
[2-3 sentences: setup, key mechanism, main prediction]

### Key Propositions
1. [Proposition + intuition]

### Empirical Predictions
- [Prediction 1 → mapped to which regression/test]

### LaTeX Output
- Full model: quality_reports/theory_model_[date].md
- Paper section: paper/sections/theory.tex
```

---

## Output Location

- Full model: `quality_reports/theory_model_[date].md`
- LaTeX-ready section: `paper/sections/theory.tex` (creates or updates)
- Append entry to `quality_reports/research_journal.md`

---

## Principles

- **Theory motivates empirics.** The model should generate predictions the empirical strategy tests.
- **Assumptions first.** State all assumptions before deriving results — referees will scrutinize them.
- **Notation consistency.** Use the same symbols in the theory as in the empirical sections.
- **No floating propositions.** Every proposition must connect back to a testable implication.
- **Proofs in appendix.** Main text has propositions and intuition; full proofs go to appendix.
