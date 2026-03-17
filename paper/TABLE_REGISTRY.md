# Table Registry

Auto-generated numerical tables for the paper. Regenerate with:

```bash
python -m code.generate_tables           # all tables
python -m code.generate_tables --table N  # specific table (1, 10, 11, 12)
```

| Table | Output File | Generator Script | Data Source |
|-------|------------|------------------|-------------|
| 1  | `paper/tables/table_1.tex`  | `code/tables/summary_stats.py` | `data/processed/panel_monthly.parquet` |
| 10 | `paper/tables/table_10.tex` | `code/tables/oos_performance.py` | `output/cv_results.csv` |
| 11 | `paper/tables/table_11.tex` | `code/tables/theory_ranking.py` | `output/cv_window_results.json` |
| 12 | `paper/tables/table_12.tex` | `code/tables/subsample_analysis.py` | `output/cv_window_results.json` |

Tables 2--9 are hardcoded in `paper/tables_and_figures.tex` (theory restriction catalogs, not computed).
