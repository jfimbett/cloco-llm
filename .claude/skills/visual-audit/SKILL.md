---
name: visual-audit
description: Visual layout audit of Beamer (.tex) or Quarto (.qmd) slide decks. Dispatches the discussant agent for scored review covering overflow, font consistency, paper fidelity, narrative arc, and compilation. Advisory score — non-blocking.
argument-hint: "[path to .tex or .qmd file]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Task", "Bash"]
---

# Visual Audit of Slide Deck

Dispatch the **discussant** agent to perform a scored visual and content audit of a presentation.

**Input:** `$ARGUMENTS` — path to `.tex` (Beamer) or `.qmd` (Quarto) file.

---

## Workflow

### Step 1: Identify File and Format

- Determine format from file extension: `.tex` → Beamer, `.qmd` → Quarto
- If `$ARGUMENTS` is empty, look for files in `talks/beamer/` and `talks/quarto/` and ask the user to choose

### Step 2: Verify Compilation

**Beamer (.tex):**
```bash
latexmk -pdf -cd [file] 2>&1 | grep -E "Error|Warning|Overfull"
```

**Quarto (.qmd):**
```bash
quarto render [file] 2>&1 | grep -E "ERROR|WARNING"
```

Report any compilation errors before proceeding.

### Step 3: Launch discussant Agent

Delegate to the `discussant` agent via Task tool:

```
Prompt: Audit the presentation at [file].
Also read paper/main.tex to check content fidelity.
Format: [Beamer | Quarto]
Type: [infer from filename or slide count]
Run all 8 audit categories:
  1. Compilation readiness
  2. Format compliance (slide count)
  3. Paper consistency (numbers, figures, notation)
  4. Narrative arc
  5. Slide density
  6. Visual quality
  7. Figure and table quality
  8. Professional polish
Score as advisory (non-blocking).
Save report to quality_reports/visual_audit_[date].md
```

### Step 4: Spacing-First Remediation Suggestions

The discussant will flag issues. For layout/density issues, suggest in this priority order:
1. Reduce vertical spacing (negative margins in Beamer, `margin` in Quarto CSS)
2. Consolidate bullet lists
3. Move displayed equations inline
4. Reduce figure size
5. Last resort: font size reduction (never below 0.85em / `\footnotesize`)

### Step 5: Present Results

```markdown
## Visual Audit: [filename]
**Format:** [Beamer / Quarto]
**Talk Score:** XX/100 (Advisory — non-blocking)

### Critical Issues (fix before presenting)
### Warnings (should fix)
### Minor (nice to fix)
```

---

## Principles

- **discussant is a critic, not a creator.** It identifies issues; fixes are applied by the storyteller.
- **Advisory only.** Talk scores never block commits or PRs.
- **Paper consistency is non-negotiable.** Any number or figure mismatch with the paper is Critical.
- **Spacing-first.** Never reach for smaller fonts before trying layout fixes.
