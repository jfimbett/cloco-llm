"""
Type A/B: Macro-finance restrictions (#52-56).

Based on macro predictors: term spread, default spread, cay,
excess bond premium, and risk-free rate effects.
Factor-based restrictions use Type A (linear SDF); direct
predictability restrictions use Type B.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class TermSpreadPredictability(Restriction):
    """#52: Term spread predicts equity returns.
    Higher term spread → higher expected returns (business cycle risk).
    """
    def __init__(self):
        super().__init__('term_spread_pred', 'macro', 'B',
                         'Term spread positive return predictability')

    def penalty(self, f_hat, X, data_context):
        ts = data_context.get('term_spread', None)
        if ts is None:
            return 0.0
        mask = np.isfinite(ts) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], ts[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        ts = data_context.get('term_spread', None)
        n = len(f_hat)
        if ts is None:
            return np.zeros(n)
        mask = np.isfinite(ts) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], ts[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        st = np.std(ts[mask])
        if sf == 0 or st == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (ts[mask] - np.mean(ts[mask])) / (nm * sf * st)
        return grad


class DefaultSpreadPredictability(Restriction):
    """#53: Default spread predicts equity returns.
    Higher default spread → higher expected returns (credit risk premium).
    """
    def __init__(self):
        super().__init__('default_spread_pred', 'macro', 'B',
                         'Default spread positive return predictability')

    def penalty(self, f_hat, X, data_context):
        ds = data_context.get('default_spread', None)
        if ds is None:
            return 0.0
        mask = np.isfinite(ds) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], ds[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        ds = data_context.get('default_spread', None)
        n = len(f_hat)
        if ds is None:
            return np.zeros(n)
        mask = np.isfinite(ds) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], ds[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sd = np.std(ds[mask])
        if sf == 0 or sd == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (ds[mask] - np.mean(ds[mask])) / (nm * sf * sd)
        return grad


class EBPPredictability(Restriction):
    """#54: Excess bond premium predicts equity returns.
    Gilchrist-Zakrajsek EBP captures credit market distress.
    """
    def __init__(self):
        super().__init__('ebp_pred', 'macro', 'A',
                         'Excess bond premium return predictability')

    def penalty(self, f_hat, X, data_context):
        ebp = data_context.get('ebp', None)
        if ebp is None:
            return 0.0
        mask = np.isfinite(ebp) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], ebp[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        ebp = data_context.get('ebp', None)
        n = len(f_hat)
        if ebp is None:
            return np.zeros(n)
        mask = np.isfinite(ebp) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], ebp[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        se = np.std(ebp[mask])
        if sf == 0 or se == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (ebp[mask] - np.mean(ebp[mask])) / (nm * sf * se)
        return grad


class RiskFreeRateEffect(Restriction):
    """#55: Risk-free rate negatively predicts excess returns.
    Higher rf → lower equity premium (Fed model intuition).
    """
    def __init__(self):
        super().__init__('rf_effect', 'macro', 'A',
                         'Risk-free rate negative return effect')

    def penalty(self, f_hat, X, data_context):
        rf = data_context.get('rf', None)
        if rf is None:
            return 0.0
        mask = np.isfinite(rf) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], rf[mask])[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        rf = data_context.get('rf', None)
        n = len(f_hat)
        if rf is None:
            return np.zeros(n)
        mask = np.isfinite(rf) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], rf[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sr = np.std(rf[mask])
        if sf == 0 or sr == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (rf[mask] - np.mean(rf[mask])) / (nm * sf * sr)
        return grad


class MacroFactorStructure(Restriction):
    """#56: Macro factor structure.
    Expected returns load on a small number of macro factors
    (term spread, default spread, cay, ebp).
    """
    def __init__(self):
        super().__init__('macro_factor_structure', 'macro', 'A',
                         'Macro factor structure in expected returns')

    def penalty(self, f_hat, X, data_context):
        # Collect macro variables
        macro_vars = []
        for key in ['term_spread', 'default_spread', 'cay', 'ebp', 'rf']:
            v = data_context.get(key, None)
            if v is not None:
                macro_vars.append(v)
        if len(macro_vars) < 2:
            return 0.0

        macro_mat = np.column_stack(macro_vars)
        mask = np.all(np.isfinite(macro_mat), axis=1) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0

        # OLS regression of f_hat on macro variables
        X_macro = np.column_stack([macro_mat[mask], np.ones(mask.sum())])
        try:
            beta, residuals, _, _ = np.linalg.lstsq(X_macro, f_hat[mask], rcond=None)
        except np.linalg.LinAlgError:
            return 0.0

        # R² of macro regression
        ss_res = np.sum((f_hat[mask] - X_macro @ beta) ** 2)
        ss_tot = np.sum((f_hat[mask] - np.mean(f_hat[mask])) ** 2)
        if ss_tot == 0:
            return 0.0
        r2 = 1 - ss_res / ss_tot

        # Penalize if macro factors explain too little
        # Expected returns should have substantial macro component
        return max(0, 0.1 - r2) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        macro_vars = []
        for key in ['term_spread', 'default_spread', 'cay', 'ebp', 'rf']:
            v = data_context.get(key, None)
            if v is not None:
                macro_vars.append(v)
        n = len(f_hat)
        if len(macro_vars) < 2:
            return np.zeros(n)

        macro_mat = np.column_stack(macro_vars)
        mask = np.all(np.isfinite(macro_mat), axis=1) & np.isfinite(f_hat)
        nm = mask.sum()
        if nm < 20:
            return np.zeros(n)

        X_m = np.column_stack([macro_mat[mask], np.ones(nm)])
        try:
            XtX_inv = np.linalg.inv(X_m.T @ X_m)
        except np.linalg.LinAlgError:
            return np.zeros(n)

        # Projection and residual maker
        P = X_m @ XtX_inv @ X_m.T  # (nm, nm) — but for n=5K this is 200MB, too large
        # Instead compute fitted values directly
        beta = XtX_inv @ (X_m.T @ f_hat[mask])
        fitted = X_m @ beta
        resid = f_hat[mask] - fitted

        ss_res = np.dot(resid, resid)
        f_bar = np.mean(f_hat[mask])
        ss_tot = np.sum((f_hat[mask] - f_bar) ** 2)
        if ss_tot == 0:
            return np.zeros(n)
        r2 = 1.0 - ss_res / ss_tot
        if r2 >= 0.1:
            return np.zeros(n)

        # d(ss_res)/d(f_i) = 2 * resid_i * (1 - P_ii) ≈ 2 * resid_i * (1 - p/nm)
        # For efficiency, use M = I - P, M@resid = resid (since resid ⊥ X)
        # So d(ss_res)/d(f) = 2 * M^T @ resid. But M resid = resid and M is symmetric.
        # The proper derivative: d(ss_res)/d(f_i) = 2 * (M @ e_i)^T @ resid
        #   = 2 * resid_i - 2 * (P @ e_i)^T @ resid
        # For speed: d(ss_res)/d(f) = 2*(resid - P @ resid) = 2*resid (since P@resid=0)
        d_ss_res = 2.0 * resid

        d_ss_tot = 2.0 * (f_hat[mask] - f_bar) * (1.0 - 1.0 / nm)

        # d(r2)/d(f) = -(d_ss_res * ss_tot - ss_res * d_ss_tot) / ss_tot²
        dr2 = -(d_ss_res * ss_tot - ss_res * d_ss_tot) / (ss_tot ** 2)

        grad = np.zeros(n)
        grad[mask] = -2.0 * (0.1 - r2) * dr2
        return grad


def register_macro_restrictions(registry: RestrictionRegistry):
    """Register all 5 macro restrictions."""
    restrictions = [
        TermSpreadPredictability(),
        DefaultSpreadPredictability(),
        EBPPredictability(),
        RiskFreeRateEffect(),
        MacroFactorStructure(),
    ]
    for r in restrictions:
        registry.register(r)
