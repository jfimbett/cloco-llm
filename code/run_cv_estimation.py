"""
CV-tuned estimation for Theory-KRR.

Strategy: For each rolling window, evaluate a coarse grid of mu configurations
on the LAST year of the training set (temporal validation), then use the best
configuration for OOS prediction. This avoids the expense of full LOYO CV
while still selecting meaningful mu values.

Also runs ablation: Theory-KRR with each group removed individually.
"""
import numpy as np
import pandas as pd
import time
import json
from pathlib import Path

from code.utils.data_loader import (
    load_panel, get_characteristic_cols, get_macro_cols,
    build_managed_portfolios,
)
from code.utils.evaluation import r2_oos, diebold_mariano
from code.estimation.krr import StandardKRR
from code.estimation.theory_krr import TheoryKRR, DEFAULT_GROUPS
from code.restrictions import build_all_restrictions
from code.baselines.linear import HistoricalMean, RidgeModel
from code.baselines.ensemble import RandomForestModel


# --- mu configurations to evaluate ---
MU_CONFIGS = {
    'krr_only':      {i: 0.0 for i in range(8)},
    'all_0.001':     {i: 0.001 for i in range(8)},
    'all_0.01':      {i: 0.01 for i in range(8)},
    'all_0.1':       {i: 0.1 for i in range(8)},
    'all_1.0':       {i: 1.0 for i in range(8)},
    'all_10.0':      {i: 10.0 for i in range(8)},
    'cons_only':     {0: 1.0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0},
    'prod_only':     {0: 0, 1: 1.0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0},
    'inter_only':    {0: 0, 1: 0, 2: 1.0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0},
    'info_only':     {0: 0, 1: 0, 2: 0, 3: 1.0, 4: 0, 5: 0, 6: 0, 7: 0},
    'demand_only':   {0: 0, 1: 0, 2: 0, 3: 0, 4: 1.0, 5: 0, 6: 0, 7: 0},
    'vol_only':      {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 1.0, 6: 0, 7: 0},
    'behav_only':    {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1.0, 7: 0},
    'macro_only':    {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 1.0},
    'cons_inter':    {0: 1.0, 1: 0, 2: 1.0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0},
    'top4':          {0: 0.1, 1: 0.1, 2: 0.1, 3: 0, 4: 0, 5: 0.1, 6: 0, 7: 0},
    # Ablation: all except one group
    'no_cons':       {0: 0, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0.1, 7: 0.1},
    'no_prod':       {0: 0.1, 1: 0, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0.1, 7: 0.1},
    'no_inter':      {0: 0.1, 1: 0.1, 2: 0, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0.1, 7: 0.1},
    'no_behav':      {0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0, 7: 0.1},
}

# Lambda grid for joint tuning
LAMBDA_GRID = [1e-4, 1e-3, 1e-2, 1e-1, 1.0]

GROUP_NAMES = {
    0: 'consumption', 1: 'production', 2: 'intermediary', 3: 'information',
    4: 'demand', 5: 'volatility', 6: 'behavioral', 7: 'macro',
}


def build_data_context(df, macro_cols):
    """Build data_context dict from portfolio DataFrame."""
    dc = {}
    for c in macro_cols:
        if c in df.columns:
            dc[c] = df[c].values
    for c in ['ik', 'roe', 'leverage', 'bm', 'roa', 'gp', 'ag', 'rd_intensity',
              'Mom12m', 'streversal', 'LRreversal', 'me', 'grcapx',
              'ForecastDispersion', 'IdioVol3F']:
        if c in df.columns:
            dc[c] = df[c].values
    return dc


def run_cv_estimation():
    np.random.seed(42)
    out_path = Path('output')
    out_path.mkdir(parents=True, exist_ok=True)

    print("Loading panel...")
    panel = load_panel()
    chars = get_characteristic_cols(panel)
    macro = get_macro_cols(panel)
    selected_chars = chars[:7]

    registry = build_all_restrictions()
    months = np.sort(panel['yyyymm'].unique())

    # Rolling windows: every 3 years, expanding, min 240 months training
    rebalance_months = []
    start_oos = 198301
    oos_months = months[(months >= start_oos)]
    for m in oos_months[::36]:
        rebalance_months.append(m)

    # Store results per window
    window_results = []
    all_preds = {k: [] for k in ['hist_mean', 'ridge', 'rf', 'krr', 'best_tikrr']}
    all_realized = []
    all_train_means = []

    for w_idx, rb_date in enumerate(rebalance_months):
        # Training: all before rb_date
        train_df = panel[panel['yyyymm'] < rb_date]
        # Test: rb_date to next rebalance (or end)
        if w_idx + 1 < len(rebalance_months):
            test_df = panel[(panel['yyyymm'] >= rb_date) &
                            (panel['yyyymm'] < rebalance_months[w_idx + 1])]
        else:
            test_df = panel[panel['yyyymm'] >= rb_date]

        if len(train_df) == 0 or len(test_df) == 0:
            continue

        train_months_arr = train_df['yyyymm'].unique()
        test_months_arr = test_df['yyyymm'].unique()
        print(f"\n{'='*70}")
        print(f"Window {w_idx}: train ...-{train_months_arr.max()} "
              f"({len(train_months_arr)}mo), test {test_months_arr.min()}-{test_months_arr.max()}")

        t0 = time.time()

        # Build managed portfolios
        port_train = build_managed_portfolios(train_df, n_ports=37, chars=selected_chars)
        port_test = build_managed_portfolios(test_df, n_ports=37, chars=selected_chars)

        feat_cols = [c for c in selected_chars if c in port_train.columns]
        X_train_full = port_train[feat_cols].fillna(0).values
        y_train_full = port_train['port_ret'].fillna(0).values
        X_test = port_test[feat_cols].fillna(0).values
        y_test = port_test['port_ret'].fillna(0).values
        dc_train_full = build_data_context(port_train, macro)

        train_mean = float(np.mean(y_train_full))
        print(f"  Portfolios built ({time.time()-t0:.1f}s): "
              f"train={X_train_full.shape}, test={X_test.shape}")

        # --- Split training into train/val for hyperparameter selection ---
        # Use last 24 months of training as validation
        val_cutoff = train_months_arr[-24] if len(train_months_arr) > 48 else train_months_arr[-12]
        val_mask = port_train['yyyymm'] >= val_cutoff
        X_tr = X_train_full[~val_mask.values]
        y_tr = y_train_full[~val_mask.values]
        X_val = X_train_full[val_mask.values]
        y_val = y_train_full[val_mask.values]
        dc_tr = {}
        for k, v in dc_train_full.items():
            dc_tr[k] = v[~val_mask.values]

        print(f"  Validation split: train={X_tr.shape[0]}, val={X_val.shape[0]}")

        # --- Baselines (fit on full training, predict test) ---
        # Historical mean
        hm = HistoricalMean()
        hm.fit(X_train_full, y_train_full)
        pred_hm = hm.predict(X_test)
        all_preds['hist_mean'].append(pred_hm)

        # Ridge
        ridge = RidgeModel(alpha=1.0)
        ridge.fit(X_train_full, y_train_full)
        pred_ridge = ridge.predict(X_test)
        all_preds['ridge'].append(pred_ridge)

        # Random Forest
        rf = RandomForestModel()
        rf.fit(X_train_full, y_train_full)
        pred_rf = rf.predict(X_test)
        all_preds['rf'].append(pred_rf)

        # Standard KRR (tune lambda on validation set)
        best_krr_lambda = 0.01
        best_krr_val_mse = np.inf
        for lam in LAMBDA_GRID:
            krr_tmp = StandardKRR(lambda_stat=lam)
            krr_tmp.fit(X_tr, y_tr)
            val_pred = krr_tmp.predict(X_val)
            val_mse = np.mean((y_val - val_pred) ** 2)
            if val_mse < best_krr_val_mse:
                best_krr_val_mse = val_mse
                best_krr_lambda = lam

        krr = StandardKRR(lambda_stat=best_krr_lambda)
        krr.fit(X_train_full, y_train_full)
        pred_krr = krr.predict(X_test)
        all_preds['krr'].append(pred_krr)
        print(f"  KRR: lambda={best_krr_lambda}, val_mse={best_krr_val_mse:.8f}")

        # --- Theory-KRR: evaluate mu configurations on validation set ---
        print(f"  Evaluating {len(MU_CONFIGS)} mu configurations...")
        config_results = {}
        best_config = 'krr_only'
        best_val_mse = np.inf

        for config_name, mu_config in MU_CONFIGS.items():
            t1 = time.time()
            try:
                tikrr = TheoryKRR(restrictions=registry.all())
                tikrr.fit(X_tr, y_tr, best_krr_lambda, mu_config, dc_tr)
                val_pred = tikrr.predict(X_val)
                val_mse = float(np.mean((y_val - val_pred) ** 2))
                config_results[config_name] = val_mse
                if val_mse < best_val_mse:
                    best_val_mse = val_mse
                    best_config = config_name
                dt = time.time() - t1
                if dt > 5:
                    print(f"    {config_name}: val_mse={val_mse:.8f} ({dt:.0f}s)")
            except Exception as e:
                config_results[config_name] = np.inf
                print(f"    {config_name}: FAILED ({e})")

        print(f"  Best config: {best_config} (val_mse={best_val_mse:.8f})")
        print(f"  KRR baseline val_mse: {config_results.get('krr_only', np.nan):.8f}")

        # --- Fit best Theory-KRR on full training, predict test ---
        best_mu = MU_CONFIGS[best_config]
        tikrr_final = TheoryKRR(restrictions=registry.all())
        tikrr_final.fit(X_train_full, y_train_full, best_krr_lambda,
                        best_mu, dc_train_full)
        pred_tikrr = tikrr_final.predict(X_test)
        all_preds['best_tikrr'].append(pred_tikrr)

        # Record multiplier values
        mvals = tikrr_final.get_multiplier_values()
        top5 = sorted(mvals.items(), key=lambda x: -x[1])[:5]
        print(f"  Top multipliers: {[(k, round(v, 4)) for k, v in top5]}")

        all_realized.append(y_test)
        all_train_means.append(train_mean)

        # Log per-config validation MSEs
        window_results.append({
            'window': w_idx,
            'test_start': int(test_months_arr.min()),
            'test_end': int(test_months_arr.max()),
            'best_config': best_config,
            'best_lambda': best_krr_lambda,
            'best_val_mse': best_val_mse,
            'krr_val_mse': config_results.get('krr_only', np.nan),
            'config_mses': {k: round(v, 10) for k, v in config_results.items()},
            'top_multipliers': {k: round(v, 6) for k, v in top5},
        })

        elapsed = time.time() - t0
        print(f"  Window total: {elapsed:.0f}s")

    # --- Aggregate OOS results ---
    print("\n\n" + "=" * 70)
    print("AGGREGATE OOS RESULTS")
    print("=" * 70)

    y_all = np.concatenate(all_realized)
    overall_mean = np.mean(all_train_means)

    results = {}
    for name in all_preds:
        pred_all = np.concatenate(all_preds[name])
        r2 = r2_oos(y_all, pred_all, overall_mean)
        results[name] = {'r2_oos_pct': round(r2 * 100, 2)}

    # DM tests
    e_hm = y_all - np.concatenate(all_preds['hist_mean'])
    e_krr = y_all - np.concatenate(all_preds['krr'])
    e_tikrr = y_all - np.concatenate(all_preds['best_tikrr'])

    for name in ['ridge', 'rf', 'krr', 'best_tikrr']:
        e_m = y_all - np.concatenate(all_preds[name])
        dm_stat, dm_pval = diebold_mariano(e_hm, e_m)
        results[name]['dm_vs_hm'] = round(dm_stat, 2)
        results[name]['dm_vs_hm_pval'] = round(dm_pval, 4)

    # Theory-KRR vs KRR
    dm_tk, pv_tk = diebold_mariano(e_krr, e_tikrr)
    results['best_tikrr']['dm_vs_krr'] = round(dm_tk, 2)
    results['best_tikrr']['dm_vs_krr_pval'] = round(pv_tk, 4)

    results_df = pd.DataFrame(results).T
    results_df.to_csv(out_path / 'cv_results.csv')

    print("\n" + results_df.to_string())

    # --- Config selection frequency ---
    print("\n\nConfig selection frequency across windows:")
    from collections import Counter
    config_counts = Counter(w['best_config'] for w in window_results)
    for config, count in config_counts.most_common():
        print(f"  {config}: {count} windows")

    # --- Per-group ablation summary ---
    print("\n\nGroup importance (avg validation MSE reduction vs krr_only):")
    group_only_configs = {
        'consumption': 'cons_only', 'production': 'prod_only',
        'intermediary': 'inter_only', 'information': 'info_only',
        'demand': 'demand_only', 'volatility': 'vol_only',
        'behavioral': 'behav_only', 'macro': 'macro_only',
    }
    for group_name, config_name in group_only_configs.items():
        improvements = []
        for w in window_results:
            krr_mse = w['config_mses'].get('krr_only', np.nan)
            group_mse = w['config_mses'].get(config_name, np.nan)
            if np.isfinite(krr_mse) and np.isfinite(group_mse):
                improvements.append((krr_mse - group_mse) / krr_mse * 100)
        if improvements:
            avg_imp = np.mean(improvements)
            print(f"  {group_name:15s}: {avg_imp:+.4f}% avg MSE reduction")

    # Save detailed results
    with open(out_path / 'cv_window_results.json', 'w') as f:
        json.dump(window_results, f, indent=2, default=str)

    np.savez(
        out_path / 'cv_predictions.npz',
        y_realized=y_all,
        **{f'pred_{m}': np.concatenate(all_preds[m]) for m in all_preds},
    )

    return results_df


if __name__ == '__main__':
    run_cv_estimation()
