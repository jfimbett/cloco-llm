---
name: create-talk
description: Generate academic presentations (Beamer .tex or Quarto RevealJS .qmd) by dispatching the storyteller agent (creator) and discussant agent (critic). Supports 4 formats — job market, seminar, short, lightning. Derives all content from paper/main.tex.
disable-model-invocation: true
argument-hint: "[format: job-market | seminar | short | lightning] [output: beamer | quarto (default: beamer)] [paper path (optional)]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Edit", "Task", "Bash"]
---

# Create Talk

Generate an academic presentation by dispatching the **storyteller** (creator) and **discussant** (critic).

**Input:** `$ARGUMENTS` — format name, output type (beamer or quarto), optionally followed by paper path.

---

## Workflow

### Step 1: Parse Arguments

- **Format** (required): `job-market` | `seminar` | `short` | `lightning`
- **Output type** (optional): `beamer` (default) | `quarto`
- **Paper path** (optional): defaults to `paper/main.tex`
- If no format specified, ask the user before proceeding.

### Format Constraints

| Format | Slides | Duration | Content Scope |
|--------|--------|----------|---------------|
| Job market | 40-50 | 45-60 min | Full story, all results, mechanism, robustness |
| Seminar | 25-35 | 30-45 min | Motivation, main result, 2 robustness, conclusion |
| Short | 10-15 | 15 min | Question, method, key result, implication |
| Lightning | 3-5 | 5 min | Hook, one result, so-what |

### Output Format Details

**Beamer (.tex)**
- Output: `talks/beamer/[format]_talk.tex`
- Compile: `latexmk -pdf -cd talks/beamer/[format]_talk.tex`
- Figures: `\includegraphics[width=0.85\textwidth]{../../paper/figures/fig.pdf}`

**Quarto RevealJS (.qmd)**
- Output: `talks/quarto/[format]_talk.qmd`
- Compile: `quarto render talks/quarto/[format]_talk.qmd`
- Figures: `![](../../paper/figures/fig.pdf){width=85%}`
- YAML: `format: revealjs`, `theme: simple`, `embed-resources: true`, `slide-number: true`

### Step 2: Launch storyteller Agent

Delegate to the `storyteller` agent via Task tool:

```
Prompt: Create a [format] talk from [paper] in [beamer|quarto] format.
Read paper/main.tex fully. Extract: research question, identification strategy,
main result (with exact value and units), secondary results, robustness checks,
key figures/tables (with file paths), institutional background.
Design narrative arc for [format] format.
Build [Beamer .tex | Quarto .qmd] file. Use figures from paper/figures/ directly.
Compile to verify it runs cleanly.
Save to talks/[beamer|quarto]/[format]_talk.[tex|qmd]
```

The storyteller follows these principles:
- One idea per slide
- Figures > tables (move tables to backup slides)
- Build tension: motivation → question → method → findings → implications
- All claims must appear verbatim in paper/main.tex (single source of truth)
- Notation must match paper exactly (same subscripts, Greek letters, variable names)

### Step 3: Launch discussant Agent (Talk Critic)

After storyteller returns, delegate to the `discussant` agent:

```
Prompt: Review the talk at talks/[format]/[format]_talk.[tex|qmd].
Also read paper/main.tex to verify content fidelity.
Format: [Beamer | Quarto]
Type: [format]
Run all 8 audit categories. Score as advisory (non-blocking).
Save report to quality_reports/[format]_talk_review.md
```

### Step 4: Fix Critical Issues

If discussant finds Critical issues (compilation failure, content not in paper):
1. Re-dispatch storyteller with the specific issues listed (max 3 rounds per three-strikes.md)
2. Re-run discussant to verify

### Step 5: Present Results

1. Generated file path and format
2. Slide count and format compliance
3. discussant score (advisory, non-blocking)
4. Any TODO items (missing figures, unresolved references)

---

## Output

- Beamer: `talks/beamer/[format]_talk.tex`
- Quarto: `talks/quarto/[format]_talk.qmd`

---

## Principles

- **Paper is authoritative.** Every claim must appear in paper/main.tex.
- **Same figures.** Never redraw figures — use the exact same files from paper/figures/.
- **Less is more.** Especially for short and lightning — ruthlessly cut.
- **Audience calibration.** Job market = rigor. Seminar = interesting result. Lightning = sell the idea.
- **Advisory scoring.** Talk scores don't block commits.
- **Worker-critic pairing.** storyteller creates, discussant critiques. Never skip the review.
