---
name: structural-estimation
description: Design and implement structural estimation strategies by dispatching the structural-estimation-expert agent. Covers model solution methods, estimation (MLE, GMM, SMM, indirect inference, Bayesian), calibration, and model fit evaluation. Use when asked to "estimate the structural model", "solve the model", "design the GMM moments", or "implement BLP".
disable-model-invocation: true
argument-hint: "[model description or specification file]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Edit", "Task", "WebSearch"]
---

# Structural Estimation

Design and implement a structural estimation strategy by dispatching the **structural-estimation-expert** agent.

**Input:** `$ARGUMENTS` — model description, specification file, or research question requiring structural estimation.

---

## Workflow

### Step 1: Gather Context

Before launching the agent:
1. Read `paper/main.tex` — understand the model being estimated
2. Read `quality_reports/theory_model_*.md` if it exists — the theory feeds the structural model
3. Read `.claude/rules/domain-profile.md` — field conventions for structural work
4. Check `code/` for any existing model solution code
5. Read any existing strategy memos in `quality_reports/`

### Step 2: Determine Scope

From the input and context, determine:
- **Model type:** Dynamic discrete choice / IO demand / Asset pricing / Heterogeneous agents / Other
- **Solution method needed:** VFI, EGM, PFI, contraction mapping, particle filter, etc.
- **Estimation method:** MLE, GMM, SMM, Indirect Inference, Bayesian MCMC, etc.
- **Software:** R, Python, Julia, Matlab — use whatever is already in `code/`

### Step 3: Launch structural-estimation-expert Agent

Delegate to the `structural-estimation-expert` agent via Task tool:

```
Prompt: Design and implement a structural estimation strategy for [model/research question].

Context:
- Model: [from theory_model or paper]
- Field conventions: [from domain-profile.md]
- Existing code: [from code/ directory if any]
- Data available: [from data assessment if any]

Deliverables:
1. Estimation strategy memo — method choice with justification
2. Identification argument — what identifies the structural parameters
3. Model solution code — efficient solver
4. Estimation code — objective function, optimization, standard errors
5. Model fit assessment — moments matched, goodness of fit
6. Robustness — sensitivity to starting values, alternative estimation windows

Save strategy memo to: quality_reports/structural_strategy_[date].md
Save code to: code/structural/
```

### Step 4: econometrics-critic Review

After the structural-estimation-expert returns, dispatch the `econometrics-critic` to verify:

```
Prompt: Review the structural estimation strategy at quality_reports/structural_strategy_[date].md.
Focus on:
  - Identification: are the structural parameters identified? What's the exclusion restriction?
  - Estimation validity: is the chosen method appropriate for this model class?
  - Inference: are standard errors computed correctly (delta method, bootstrap, analytical)?
  - Code-model alignment: does the code implement what the memo specifies?
Save review to: quality_reports/structural_econometrics_review_[date].md
```

### Step 5: Code Review

Dispatch the `debugger` agent on the structural code:

```
Prompt: Review code in code/structural/ in full mode.
Compare against quality_reports/structural_strategy_[date].md.
Focus on: numerical precision, convergence criteria, seed for stochastic solvers,
path handling, output saving (RDS/pkl for all computed objects).
```

### Step 6: Fix and Iterate

If either review finds Critical issues:
1. Re-dispatch structural-estimation-expert with specific fixes (max 3 rounds per three-strikes.md)
2. Re-run reviews to verify

### Step 7: Present Results

```markdown
## Structural Estimation: [Model Name]
**Date:** YYYY-MM-DD

### Estimation Strategy
- Method: [MLE / GMM / SMM / Indirect Inference / Bayesian]
- Identification: [what identifies key parameters]
- Software: [R / Python / Julia]

### econometrics-critic Assessment: [SOUND / CONCERNS / CRITICAL]
### debugger Score: XX/100

### Key Parameter Estimates
| Parameter | Estimate | SE | Interpretation |
|-----------|----------|-----|----------------|

### Model Fit
[Moments matched, goodness of fit statistics]

### Output Files
- Strategy memo: quality_reports/structural_strategy_[date].md
- Code: code/structural/
```

---

## Output Location

- Strategy memo: `quality_reports/structural_strategy_[date].md`
- Code: `code/structural/`
- Append entry to `quality_reports/research_journal.md`

---

## Principles

- **Identification first.** Before any code, confirm the structural parameters are identified.
- **Efficient solver.** For dynamic models, solution speed dominates — use EGM over VFI where possible.
- **Separate solution from estimation.** Solver code and estimation wrapper are different files.
- **Seeds everywhere.** Any stochastic simulation or MCMC must have a fixed seed.
- **econometrics-critic is mandatory.** Structural models have many ways to go wrong quietly — always review.
