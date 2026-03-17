---
name: audit-restrictions
description: Audit all theory restrictions in the paper for data coverage, variable documentation, and summary statistics inclusion. Produces a report with issues and fixes.
argument-hint: "[fix|report]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Edit", "Bash", "Agent"]
---

# Audit Theory Restrictions

Cross-reference every restriction in the paper against (1) data availability, (2) paper documentation, and (3) summary statistics coverage. Produces a structured report and optionally applies fixes.

## Mode

- `$ARGUMENTS` = `report` (default): produce the audit report only, do not edit files
- `$ARGUMENTS` = `fix`: produce the report AND apply corrections to paper files

## Workflow

### Phase 1: Extract Restrictions Inventory

Read all restriction tables from `paper/tables_and_figures.tex` (Tables 2–9). For each restriction, extract:

1. **Restriction number and name** (e.g., "14 — Investment CAPM")
2. **Variables referenced** in the penalty/SDF formula (e.g., $(I/K)$, $\mathrm{ROE}$, $\mathrm{Lev}$)
3. **Data type**: cross-sectional characteristic (firm-month) vs time-series macro (month)

Build a complete registry: `restriction_number | restriction_name | variables_needed | variable_type`

### Phase 2: Check Data Availability

For each variable identified in Phase 1:

1. **Check the panel**: Read `code/utils/data_loader.py` for `_MACRO_COLS` and load a sample of `data/processed/panel_monthly.parquet` column names to verify the variable exists
2. **Check raw sources**: If not in panel, check `data/raw/` for source files and `code/data_pipeline/build_panel.py` for construction logic
3. **Check proxies**: Some restrictions use proxies (e.g., `BidAskSpread` for search intensity). Flag these as "proxy" not "exact match"

Classify each variable as:
- **AVAILABLE**: exists in the panel (exact or close match)
- **PROXY**: available but using a proxy variable (note what the proxy is)
- **CONSTRUCTIBLE**: raw data exists, needs to be added to `build_panel.py`
- **MISSING**: no data source identified

### Phase 3: Check Paper Documentation

For each restriction, verify the paper explains how the data is obtained. Check these files:

- `paper/sections/estimation.tex` or `paper/sections/empirical.tex` — should have a "Data" subsection
- `paper/sections/framework.tex` — may document variable construction
- `paper/sections/introduction.tex` — may reference data sources

For each variable, check:
1. Is the **data source** mentioned? (e.g., "from CRSP", "from Compustat", "from FRED")
2. Is the **construction** explained if it's derived? (e.g., "I/K = capx / ppent")
3. Is the **availability period** noted if limited? (e.g., "VIX available from 1990")

Classify each as:
- **DOCUMENTED**: source and construction explained
- **PARTIAL**: mentioned but construction not explained
- **UNDOCUMENTED**: not mentioned in the paper

### Phase 4: Check Summary Statistics

Read the Table 1 generator (`code/tables/summary_stats.py`) and the generated `paper/tables/table_1.tex`. For each variable used in restrictions:

1. Does it appear in Panel A (firm characteristics) or Panel B (macro variables)?
2. If it's a key variable used in multiple restrictions, it SHOULD be in the summary stats
3. Flag variables used in 3+ restrictions that are missing from summary statistics

Classify as:
- **IN TABLE**: appears in summary statistics
- **SHOULD ADD**: used in 3+ restrictions, missing from table
- **OK TO OMIT**: used in 1-2 restrictions, omission is acceptable

### Phase 5: Generate Report

Write the audit report to `quality_reports/restriction_audit.md` with:

```markdown
# Restriction Data Audit — [date]

## Summary
- Total restrictions: X
- Variables covered: Y / Z
- Documentation gaps: N
- Summary stats gaps: M

## Restriction-by-Variable Matrix

| # | Restriction | Variable | Data Status | Paper Doc | Summary Stats |
|---|------------|----------|-------------|-----------|---------------|
| 1 | Power utility | cons_growth | AVAILABLE | DOCUMENTED | IN TABLE |
| ... | ... | ... | ... | ... | ... |

## Issues Found

### Data Gaps
[List variables with MISSING or CONSTRUCTIBLE status]

### Documentation Gaps
[List variables with UNDOCUMENTED or PARTIAL status]

### Summary Statistics Gaps
[List variables with SHOULD ADD status]

## Recommended Fixes
[Specific actions: add to summary stats, add documentation paragraph, etc.]
```

### Phase 6: Apply Fixes (if mode = `fix`)

Only if `$ARGUMENTS` = `fix`:

1. **Summary stats**: Update `code/tables/summary_stats.py` to add missing variables to Panel A or Panel B
2. **Paper documentation**: Add/update the data description paragraph in `paper/sections/estimation.tex` to cover undocumented variables
3. **Do NOT** modify restriction tables (Tables 2–9) — those are authoritative
4. After edits, regenerate Table 1: `python -m code.generate_tables --table 1`
5. Compile paper: `latexmk -pdf -cd paper/main.tex`

## Output

- Report always saved to `quality_reports/restriction_audit.md`
- If fix mode: edited files listed at end of report
- Return summary to user with issue counts and top-priority fixes
