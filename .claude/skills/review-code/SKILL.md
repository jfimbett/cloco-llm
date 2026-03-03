---
name: review-code
description: Code review dispatching the Debugger agent in standalone mode (categories 4-12 only). Checks code quality, reproducibility, output standards, and professional polish. Use for R, Stata, Python, Julia, or any analysis script.
argument-hint: "[filename or 'all']"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Task"]
---

# Review Code Scripts

Run the code review protocol by dispatching the **Debugger** agent in standalone mode.

In standalone mode, the Debugger runs **categories 4-12 only** (code quality). Categories 1-3 (strategic alignment) require a strategy memo and are only run within the pipeline or via `/econometrics-check`.

## Workflow

### Step 1: Identify Scripts

- If `$ARGUMENTS` is a specific file: review that file only
- If `$ARGUMENTS` is `all`: review all scripts in `code/`, `scripts/`, or subdirectories by language
- If `$ARGUMENTS` is a directory: review all scripts in that directory

### Step 2: Launch Debugger Agent

For each script (or batch), delegate to the `debugger` agent via Task tool:

```
Prompt: Review [file] in standalone mode (categories 4-12 only).
Adapt all checks to the language of the script (R, Python, Stata, Julia, etc.).
Categories:
  4. Script structure (header, sections, flow)
  5. Output hygiene (no debug print/log pollution, clean console output)
  6. Reproducibility (random seeds, relative paths, no hardcoded values)
  7. Function design (DRY, appropriate abstraction level, naming conventions)
  8. Figure/output quality (labels, dimensions, consistent style)
  9. Artifact saving pattern (all computed objects saved to appropriate output files)
  10. Comments (explain why, not what)
  11. Error handling (graceful failures, informative messages)
  12. Polish (consistent style, no dead code, clean namespace)
Save report to quality_reports/[script_name]_code_review.md
```

### Step 3: Present Summary

After all reviews complete:
- Total issues found per script
- Breakdown by severity (Critical / Major / Minor)
- Top 3 most critical issues across all scripts
- Code review score

### Step 4: IMPORTANT

**Do NOT edit any source files.** Only produce reports. Fixes are applied after user review, either manually or by re-dispatching Coder (main Claude).

---

## Principles

- **Standalone mode = code quality only.** Strategic alignment (does the code match the design?) requires a strategy memo.
- **Language-flexible.** Same categories apply to R, Stata, Python, Julia — adapt checks to language idioms.
- **Proportional severity.** Missing a random seed is Major. A missing comment is Minor.
- **Worker-critic separation.** The Debugger never fixes code — it only critiques.
