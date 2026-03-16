"""
Main runner: rolling-window estimation for all models.

Usage:
    python -m code.run_estimation --models all --start-oos 198301 --output-dir output/
    python -m code.run_estimation --models theory_krr,ridge --start-oos 198301
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from code.utils.data_loader import (
    load_panel, get_characteristic_cols, get_macro_cols,
    expanding_window_splits, build_managed_portfolios,
)
from code.utils.kernel import median_heuristic
from code.utils.evaluation import r2_oos, sharpe_ratio, certainty_equivalent, diebold_mariano
from code.utils.portfolio import decile_sort, long_short, portfolio_metrics
from code.estimation.cv import loyo_cv_splits
from code.estimation.krr import StandardKRR
from code.estimation.theory_krr import TheoryKRR
from code.restrictions import build_all_restrictions
from code.baselines.linear import HistoricalMean, OLSModel, RidgeModel, LassoModel, ElasticNetModel
from code.baselines.ensemble import RandomForestModel
from code.baselines.neural_net import NeuralNetModel
from code.config import TEST_MODE, TEST_MAX_ROLLING_WINDOWS


# --- Model registry ---
MODEL_REGISTRY = {
    'hist_mean': lambda: HistoricalMean(),
    'ols': lambda: OLSModel(),
    'ridge': lambda: RidgeModel(),
    'lasso': lambda: LassoModel(),
    'elastic_net': lambda: ElasticNetModel(),
    'random_forest': lambda: RandomForestModel(),
    'neural_net': lambda: NeuralNetModel(),
    'krr': lambda: StandardKRR(),
    'theory_krr': lambda: _build_theory_krr(),
}


def _build_theory_krr() -> TheoryKRR:
    registry = build_all_restrictions()
    return TheoryKRR(restrictions=registry.all())


def _build_data_context(df: pd.DataFrame, char_cols: list, macro_cols: list) -> dict:
    """Build data_context dict from a DataFrame slice."""
    context = {}
    # Add macro variables
    for c in macro_cols:
        if c in df.columns:
            context[c] = df[c].values
    # Add key characteristics used by restrictions
    restriction_chars = [
        'ik', 'roe', 'leverage', 'bm', 'roa', 'gp', 'ag', 'rd_intensity',
        'Mom12m', 'streversal', 'LRreversal', 'me', 'grcapx',
        'ForecastDispersion', 'IdioVol3F',
    ]
    for c in restriction_chars:
        if c in df.columns:
            context[c] = df[c].values
    return context


def run_estimation(
    models: list[str],
    start_oos: int = 198301,
    end_oos: int | None = None,
    min_train: int = 240,
    retrain_freq: int = 12,
    output_dir: str = 'output',
    use_portfolios: bool = True,
    n_cv_draws: int = 200,
):
    """
    Run rolling-window estimation for specified models.

    Parameters
    ----------
    models : list of model names from MODEL_REGISTRY
    start_oos : first OOS month (yyyymm)
    end_oos : last OOS month
    min_train : minimum training window
    retrain_freq : retrain frequency (months)
    output_dir : where to save results
    use_portfolios : use managed portfolios (True) or stock-level (False)
    n_cv_draws : number of random search draws for Theory-KRR
    """
    np.random.seed(42)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("Loading panel data...")
    panel = load_panel()
    char_cols = get_characteristic_cols(panel)
    macro_cols = get_macro_cols(panel)
    print(f"Panel: {panel.shape[0]:,} rows, {len(char_cols)} chars, {len(macro_cols)} macro vars")

    # --- Storage for OOS predictions ---
    all_predictions = {m: [] for m in models}
    all_realized = []
    all_train_means = []
    all_yyyymm = []
    window_log = []

    # --- Rolling window loop ---
    max_windows = TEST_MAX_ROLLING_WINDOWS if TEST_MODE else None
    if TEST_MODE:
        print(f"[TEST_MODE] Limiting to {max_windows} rolling windows")
    for window_idx, (train_df, test_df) in enumerate(
        expanding_window_splits(panel, min_train, retrain_freq, start_oos, end_oos)
    ):
        if max_windows is not None and window_idx >= max_windows:
            break
        train_months = train_df['yyyymm'].unique()
        test_months = test_df['yyyymm'].unique()
        print(f"\n=== Window {window_idx}: train {train_months.min()}-{train_months.max()} "
              f"({len(train_months)} months), test {test_months.min()}-{test_months.max()} "
              f"({len(test_months)} months) ===")

        t0 = time.time()

        if use_portfolios:
            # Build managed portfolios
            port_train = build_managed_portfolios(train_df, n_ports=37, chars=char_cols[:7])
            port_test = build_managed_portfolios(test_df, n_ports=37, chars=char_cols[:7])

            # Feature columns = characteristics in portfolio panel
            feat_cols = [c for c in char_cols[:7] if c in port_train.columns]
            if not feat_cols:
                feat_cols = [c for c in port_train.columns
                             if c not in ['yyyymm', 'port_id', 'port_ret'] + macro_cols]

            X_train = port_train[feat_cols].fillna(0).values
            y_train = port_train['port_ret'].fillna(0).values
            X_test = port_test[feat_cols].fillna(0).values
            y_test = port_test['port_ret'].fillna(0).values
            dc_train = _build_data_context(port_train, feat_cols, macro_cols)
        else:
            # Stock-level estimation
            feat_cols = char_cols
            valid_train = train_df[feat_cols + ['RET']].dropna()
            valid_test = test_df[feat_cols + ['RET']].dropna()
            X_train = valid_train[feat_cols].values
            y_train = valid_train['RET'].values
            X_test = valid_test[feat_cols].values
            y_test = valid_test['RET'].values
            dc_train = _build_data_context(valid_train, feat_cols, macro_cols)

        train_mean = float(np.mean(y_train))

        # Build CV splits on training data
        if use_portfolios:
            yyyymm_train = port_train['yyyymm'].values
        else:
            yyyymm_train = valid_train['yyyymm'].values
        cv_splits = loyo_cv_splits(yyyymm_train, min_train=max(60, len(train_months) // 2))

        # --- Fit and predict each model ---
        for model_name in models:
            print(f"  Fitting {model_name}...", end=' ', flush=True)
            model = MODEL_REGISTRY[model_name]()

            try:
                if model_name == 'theory_krr':
                    if cv_splits:
                        model.tune(X_train, y_train, cv_splits, dc_train, n_draws=n_cv_draws)
                    else:
                        mu_default = {i: 0.01 for i in range(8)}
                        model.fit(X_train, y_train, 1e-3, mu_default, dc_train)
                elif model_name == 'krr':
                    if cv_splits:
                        model.tune(X_train, y_train, cv_splits)
                    else:
                        model.fit(X_train, y_train)
                else:
                    if cv_splits:
                        model.tune(X_train, y_train, cv_splits)
                    else:
                        model.fit(X_train, y_train)

                pred = model.predict(X_test)
                print(f"done (pred mean={np.mean(pred):.6f})")
            except Exception as e:
                print(f"FAILED: {e}")
                pred = np.full(len(y_test), train_mean)

            all_predictions[model_name].append(pred)

        all_realized.append(y_test)
        all_train_means.append(train_mean)
        if use_portfolios:
            all_yyyymm.append(port_test['yyyymm'].values)
        else:
            all_yyyymm.append(valid_test['yyyymm'].values)

        elapsed = time.time() - t0
        window_log.append({
            'window': window_idx,
            'train_start': int(train_months.min()),
            'train_end': int(train_months.max()),
            'test_start': int(test_months.min()),
            'test_end': int(test_months.max()),
            'n_train': len(X_train),
            'n_test': len(X_test),
            'elapsed_sec': round(elapsed, 1),
        })

    # --- Aggregate results ---
    print("\n=== Aggregating OOS results ===")
    results = {}
    y_all = np.concatenate(all_realized)
    # Overall training mean (expanding)
    overall_train_mean = np.mean(all_train_means)

    for model_name in models:
        pred_all = np.concatenate(all_predictions[model_name])
        r2 = r2_oos(y_all, pred_all, overall_train_mean)
        results[model_name] = {'r2_oos': round(r2 * 100, 2)}
        print(f"  {model_name}: R²_OOS = {r2*100:.2f}%")

    # --- Portfolio-based metrics (stock-level only) ---
    if not use_portfolios:
        yyyymm_all = np.concatenate(all_yyyymm)
        for model_name in models:
            pred_all = np.concatenate(all_predictions[model_name])
            port_df = pd.DataFrame({
                'yyyymm': yyyymm_all,
                'pred': pred_all,
                'RET': y_all,
                'me': 1.0,  # equal weight fallback
            })
            dec_ret = decile_sort(port_df, 'pred', 'RET', 'me')
            ls_ret = long_short(dec_ret)
            if len(ls_ret) > 0:
                metrics = portfolio_metrics(ls_ret)
                results[model_name].update({
                    'sharpe': round(metrics['sharpe'], 2),
                    'cer_annual': round(metrics['cer'], 4),
                    'mean_annual': round(metrics['mean_annual'], 4),
                    't_stat': round(metrics['t_stat'], 2),
                })

    # --- Diebold-Mariano tests vs historical mean ---
    if 'hist_mean' in models:
        pred_hm = np.concatenate(all_predictions['hist_mean'])
        e_hm = y_all - pred_hm
        for model_name in models:
            if model_name == 'hist_mean':
                continue
            pred_m = np.concatenate(all_predictions[model_name])
            e_m = y_all - pred_m
            dm_stat, dm_pval = diebold_mariano(e_hm, e_m)
            results[model_name]['dm_vs_hm'] = round(dm_stat, 2)
            results[model_name]['dm_pval'] = round(dm_pval, 4)

    # --- Save results ---
    results_df = pd.DataFrame(results).T
    results_df.to_csv(out_path / 'model_comparison.csv')
    print(f"\nResults saved to {out_path / 'model_comparison.csv'}")

    with open(out_path / 'window_log.json', 'w') as f:
        json.dump(window_log, f, indent=2)

    # Save raw predictions
    np.savez(
        out_path / 'predictions.npz',
        y_realized=y_all,
        **{f'pred_{m}': np.concatenate(all_predictions[m]) for m in models},
    )

    print("\n=== Results Summary ===")
    print(results_df.to_string())
    return results_df


def main():
    parser = argparse.ArgumentParser(description='Theory-Informed KRR Estimation')
    parser.add_argument('--models', default='all',
                        help='Comma-separated model names or "all"')
    parser.add_argument('--start-oos', type=int, default=198301,
                        help='First OOS month (yyyymm)')
    parser.add_argument('--end-oos', type=int, default=None,
                        help='Last OOS month (yyyymm)')
    parser.add_argument('--output-dir', default='output',
                        help='Output directory')
    parser.add_argument('--stock-level', action='store_true',
                        help='Use stock-level estimation (default: managed portfolios)')
    parser.add_argument('--n-cv-draws', type=int, default=200,
                        help='Number of random search CV draws')
    args = parser.parse_args()

    if args.models == 'all':
        models = list(MODEL_REGISTRY.keys())
    else:
        models = [m.strip() for m in args.models.split(',')]

    run_estimation(
        models=models,
        start_oos=args.start_oos,
        end_oos=args.end_oos,
        output_dir=args.output_dir,
        use_portfolios=not args.stock_level,
        n_cv_draws=args.n_cv_draws,
    )


if __name__ == '__main__':
    main()
