# Utils package for Theory-Informed KRR
from .data_loader import load_panel, get_characteristic_cols, get_macro_cols
from .data_loader import expanding_window_splits, build_managed_portfolios
from .kernel import gaussian_rbf, median_heuristic, nystrom_approx
from .evaluation import r2_oos, sharpe_ratio, certainty_equivalent, diebold_mariano, block_bootstrap_sr
from .portfolio import decile_sort, long_short, portfolio_metrics
