"""
Fast estimation: fixed hyperparameters, no CV, every-5-year rebalancing.
Produces preliminary results for paper drafting.
"""
import numpy as np
import pandas as pd
import time
import json
from pathlib import Path

from code.utils.data_loader import (
    load_panel, get_characteristic_cols, get_macro_cols,
    expanding_window_splits, build_managed_portfolios,
)
from code.utils.evaluation import r2_oos, sharpe_ratio, certainty_equivalent, diebold_mariano
from code.utils.portfolio import decile_sort, long_short, portfolio_metrics
from code.estimation.krr import StandardKRR
from code.estimation.theory_krr import TheoryKRR
from code.restrictions import build_all_restrictions
from code.baselines.linear import HistoricalMean, OLSModel, RidgeModel, LassoModel, ElasticNetModel
from code.baselines.ensemble import RandomForestModel


def run_fast():
    np.random.seed(42)
    out_path = Path('output')
    out_path.mkdir(parents=True, exist_ok=True)

    print("Loading panel...")
    panel = load_panel()
    chars = get_characteristic_cols(panel)
    macro = get_macro_cols(panel)
    selected_chars = chars[:7]  # top 7 by coverage for managed portfolios

    # Fixed hyperparameters (reasonable defaults, no CV)
    RIDGE_ALPHA = 1.0
    LASSO_ALPHA = 0.001
    EN_ALPHA, EN_L1 = 0.001, 0.5
    KRR_LAMBDA = 0.01
    TIKRR_LAMBDA = 0.01
    TIKRR_MU = {i: 0.01 for i in range(8)}

    registry = build_all_restrictions()

    # Model constructors
    def make_models():
        return {
            'hist_mean': HistoricalMean(),
            'ols': OLSModel(),
            'ridge': RidgeModel(alpha=RIDGE_ALPHA),
            'lasso': LassoModel(alpha=LASSO_ALPHA),
            'elastic_net': ElasticNetModel(alpha=EN_ALPHA, l1_ratio=EN_L1),
            'random_forest': RandomForestModel(),
            'krr': StandardKRR(lambda_stat=KRR_LAMBDA),
            'theory_krr': TheoryKRR(restrictions=registry.all()),
        }

    model_names = list(make_models().keys())
    all_predictions = {m: [] for m in model_names}
    all_realized = []
    all_train_means = []
    all_yyyymm = []
    window_log = []

    # Use every-3-year rebalancing to reduce windows from 41 to ~14
    for window_idx, (train_df, test_df) in enumerate(
        expanding_window_splits(panel, min_train=240, retrain_freq=36,
                                start_oos=198301)
    ):
        train_months = train_df['yyyymm'].unique()
        test_months = test_df['yyyymm'].unique()
        print(f"\n=== Window {window_idx}: train {train_months.min()}-{train_months.max()} "
              f"({len(train_months)}mo), test {test_months.min()}-{test_months.max()} "
              f"({len(test_months)}mo) ===")

        t0 = time.time()
        port_train = build_managed_portfolios(train_df, n_ports=37, chars=selected_chars)
        port_test = build_managed_portfolios(test_df, n_ports=37, chars=selected_chars)

        feat_cols = [c for c in selected_chars if c in port_train.columns]
        X_train = port_train[feat_cols].fillna(0).values
        y_train = port_train['port_ret'].fillna(0).values
        X_test = port_test[feat_cols].fillna(0).values
        y_test = port_test['port_ret'].fillna(0).values
        train_mean = float(np.mean(y_train))

        # Data context for restrictions
        dc = {}
        for c in macro:
            if c in port_train.columns:
                dc[c] = port_train[c].values
        for c in ['ik', 'roe', 'leverage', 'bm', 'roa', 'gp', 'ag', 'rd_intensity',
                   'Mom12m', 'streversal', 'LRreversal', 'me', 'grcapx',
                   'ForecastDispersion', 'IdioVol3F']:
            if c in port_train.columns:
                dc[c] = port_train[c].values

        print(f"  Portfolios: train={X_train.shape}, test={X_test.shape} ({time.time()-t0:.1f}s)")

        models = make_models()
        for name, model in models.items():
            t1 = time.time()
            try:
                if name == 'theory_krr':
                    model.fit(X_train, y_train, TIKRR_LAMBDA, TIKRR_MU, dc)
                elif name == 'krr':
                    model.fit(X_train, y_train)
                else:
                    model.fit(X_train, y_train)
                pred = model.predict(X_test)
                print(f"  {name}: {time.time()-t1:.1f}s, pred_mean={np.mean(pred):.6f}")
            except Exception as e:
                print(f"  {name}: FAILED ({e})")
                pred = np.full(len(y_test), train_mean)

            all_predictions[name].append(pred)

        all_realized.append(y_test)
        all_train_means.append(train_mean)
        all_yyyymm.append(port_test['yyyymm'].values)
        window_log.append({
            'window': window_idx,
            'train_end': int(train_months.max()),
            'test_start': int(test_months.min()),
            'test_end': int(test_months.max()),
            'n_train': len(X_train),
            'n_test': len(X_test),
            'elapsed': round(time.time() - t0, 1),
        })

    # Aggregate
    print("\n\n=== AGGREGATING ===")
    y_all = np.concatenate(all_realized)
    overall_mean = np.mean(all_train_means)

    results = {}
    for name in model_names:
        pred_all = np.concatenate(all_predictions[name])
        r2 = r2_oos(y_all, pred_all, overall_mean)
        results[name] = {'r2_oos_pct': round(r2 * 100, 2)}

    # DM tests vs hist_mean
    pred_hm = np.concatenate(all_predictions['hist_mean'])
    e_hm = y_all - pred_hm
    for name in model_names:
        if name == 'hist_mean':
            continue
        pred_m = np.concatenate(all_predictions[name])
        e_m = y_all - pred_m
        dm_stat, dm_pval = diebold_mariano(e_hm, e_m)
        results[name]['dm_stat'] = round(dm_stat, 2)
        results[name]['dm_pval'] = round(dm_pval, 4)

    # DM test: theory_krr vs krr
    e_krr = y_all - np.concatenate(all_predictions['krr'])
    e_tkrr = y_all - np.concatenate(all_predictions['theory_krr'])
    dm_tk, pv_tk = diebold_mariano(e_krr, e_tkrr)
    results['theory_krr']['dm_vs_krr'] = round(dm_tk, 2)
    results['theory_krr']['dm_vs_krr_pval'] = round(pv_tk, 4)

    results_df = pd.DataFrame(results).T
    results_df.to_csv(out_path / 'fast_results.csv')

    # Save predictions for portfolio analysis
    np.savez(
        out_path / 'fast_predictions.npz',
        y_realized=y_all,
        yyyymm=np.concatenate(all_yyyymm),
        **{f'pred_{m}': np.concatenate(all_predictions[m]) for m in model_names},
    )

    with open(out_path / 'fast_window_log.json', 'w') as f:
        json.dump(window_log, f, indent=2)

    print("\n=== RESULTS ===")
    print(results_df.to_string())

    # Theory-KRR multipliers from last window
    last_tkrr = models.get('theory_krr')
    if last_tkrr and hasattr(last_tkrr, 'adaptive_weights_') and last_tkrr.adaptive_weights_:
        print("\nMultiplier values (last window):")
        mvals = last_tkrr.get_multiplier_values()
        top10 = sorted(mvals.items(), key=lambda x: -x[1])[:10]
        for k, v in top10:
            print(f"  {k}: {v:.6f}")

    return results_df


if __name__ == '__main__':
    run_fast()
