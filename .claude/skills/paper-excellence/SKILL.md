---
name: paper-excellence
description: Multi-agent paper review dispatching econometrics-critic, debugger, academic-proofreader, and replication-verifier in parallel. Computes weighted aggregate score per scoring-protocol.md. Use for comprehensive quality check before submission or major milestones.
disable-model-invocation: true
argument-hint: "[paper .tex path OR 'all' for full project review]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Task", "Bash"]
---

# Paper Excellence Review

Run all review agents in parallel for a comprehensive paper quality assessment. Computes the weighted aggregate score from `scoring-protocol.md`.

**Input:** `$ARGUMENTS` — path to paper `.tex` file, or `all` for full project review.

---

## Workflow

### Step 1: Identify Targets

- If `$ARGUMENTS` is a `.tex` file: review that file
- If `$ARGUMENTS` is `all`: review `paper/main.tex` + all scripts in `scripts/R/`
- Also scan for `Talks/*.tex` for auxiliary scoring

### Step 2: Gather Context

Before launching agents:
1. Read `.claude/rules/domain-profile.md` for field-specific calibration
2. Read `.claude/rules/scoring-protocol.md` for weight formula
3. Read any existing strategy memos in `quality_reports/`

### Step 3: Launch Review Agents (Parallel)

Launch up to 4 agents simultaneously via Task tool:

**Agent 1: econometrics-critic** (subagent_type: econometrics-critic)
```
Review [paper.tex] through all 4 phases: claim, design validity, inference, polish.
Also check scripts in scripts/R/ for code-theory alignment.
Save report to quality_reports/[file]_econometrics_review.md
```
**Weight:** Identification 25% of aggregate score.

**Agent 2: Debugger** (subagent_type: general-purpose, with debugger agent instructions)
```
Review all scripts in scripts/R/ for code quality and correctness.
Run categories 4-12 (code quality) plus categories 1-3 (strategic) if strategy memo exists.
Save report to quality_reports/[script]_code_review.md
```
**Weight:** Code 15% of aggregate score.

**Agent 3: academic-proofreader** (subagent_type: academic-proofreader)
```
Review [paper.tex] for grammar, writing quality, claims-evidence alignment,
notation consistency, and compilation. 6 check categories.
Save report to quality_reports/[file]_proofread_report.md
```
**Weight:** Paper 25% of aggregate score.

**Agent 4: replication-verifier** (subagent_type: replication-verifier)
```
Run standard verification (checks 1-4): LaTeX compilation, script execution,
file integrity, output freshness.
Save report to quality_reports/[file]_verification.md
```
**Weight:** Replication 5% of aggregate score.

### Step 4: Launch Talk Review (Advisory, if talks exist)

If `Talks/*.tex` files exist, launch:

**storyteller** — check notation matches paper, slide count within format range.
**discussant** — narrative flow, visual quality, content fidelity.

Talk scores are **advisory, non-blocking**.

### Step 5: Compute Weighted Aggregate Score

Per `scoring-protocol.md`, compute:

```
Overall = Σ (weight_k × score_k) for available components
```

| Component | Weight | Agent |
|-----------|--------|-------|
| Literature | 10% | (skip if no lit review exists) |
| Data | 10% | (skip if no data review exists) |
| Identification | 25% | econometrics-critic |
| Code | 15% | debugger |
| Paper | 25% | academic-proofreader |
| Polish | 10% | (from academic-proofreader writing quality subscore) |
| Replication | 5% | replication-verifier |

If components are missing, renormalize weights over available components.

### Step 6: Present Results

```markdown
# Paper Excellence Report: [Title]
**Date:** [YYYY-MM-DD]
**Aggregate Score:** [XX/100] — [gate status]

## Score Breakdown
| Component | Weight | Score | Issues | Agent |
|-----------|--------|-------|--------|-------|
| Identification | 25% | XX | N | econometrics-critic |
| Code | 15% | XX | N | Debugger |
| Paper | 25% | XX | N | academic-proofreader |
| Polish | 10% | XX | N | academic-proofreader |
| Replication | 5% | XX | PASS/FAIL | replication-verifier |

## Auxiliary: Talk Scores (non-blocking)
| Talk | Score | Issues |
|------|-------|--------|

## Priority Fixes (Top 5)
1. **[CRITICAL]** [Most important — from which agent]
2. **[MAJOR]** [Second priority]
...

## Full Reports
[Links to individual report files]
```

### Step 7: Gate Enforcement

Per `quality-gates.md`:
- **Score >= 95 + all components >= 80:** "Ready for top-5 submission."
- **Score >= 90:** "Ready for submission. Minor polish recommended."
- **Score >= 80:** "Commit-ready. Address major issues before submission."
- **Score < 80:** "Blocked. Must fix critical/major issues."

---

## Principles

- **Paper score is blocking.** Must pass quality gates.
- **Talk scores are advisory.** Reported but non-blocking.
- **Parallel execution.** All agents run simultaneously.
- **Weighted aggregation.** Uses scoring-protocol.md formula, not simple average.
- **Don't double-count.** Same issue in multiple reports counts once.
- **One unified report.** User sees one priority list, not separate reports.
