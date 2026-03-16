"""
Type B: Production/investment restrictions (#14-23).

Based on production-based asset pricing: investment-capital ratio,
profitability, q-theory, and related cross-sectional patterns.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class InvestmentMonotonicity(Restriction):
    """#14: Higher investment/capital → lower expected returns (q-theory)."""
    def __init__(self):
        super().__init__('invest_mono', 'production', 'B',
                         'Investment-capital ratio monotonicity (q-theory)')

    def penalty(self, f_hat, X, data_context):
        ik = data_context.get('ik', None)
        if ik is None:
            return 0.0
        mask = np.isfinite(ik) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], ik[mask])[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        ik = data_context.get('ik', None)
        n = len(f_hat)
        if ik is None:
            return np.zeros(n)
        mask = np.isfinite(ik) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], ik[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        si = np.std(ik[mask])
        if sf == 0 or si == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (ik[mask] - np.mean(ik[mask])) / (nm * sf * si)
        return grad


class ProfitabilityMonotonicity(Restriction):
    """#15: Higher profitability → higher expected returns."""
    def __init__(self):
        super().__init__('profit_mono', 'production', 'B',
                         'Profitability monotonicity')

    def penalty(self, f_hat, X, data_context):
        roe = data_context.get('roe', None)
        if roe is None:
            return 0.0
        mask = np.isfinite(roe) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], roe[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        roe = data_context.get('roe', None)
        n = len(f_hat)
        if roe is None:
            return np.zeros(n)
        mask = np.isfinite(roe) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], roe[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sr = np.std(roe[mask])
        if sf == 0 or sr == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (roe[mask] - np.mean(roe[mask])) / (nm * sf * sr)
        return grad


class LeverageEffect(Restriction):
    """#16: Higher leverage → higher expected returns (financial distress risk)."""
    def __init__(self):
        super().__init__('leverage_effect', 'production', 'B',
                         'Leverage-return positive relationship')

    def penalty(self, f_hat, X, data_context):
        lev = data_context.get('leverage', None)
        if lev is None:
            return 0.0
        mask = np.isfinite(lev) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], lev[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        lev = data_context.get('leverage', None)
        n = len(f_hat)
        if lev is None:
            return np.zeros(n)
        mask = np.isfinite(lev) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], lev[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sl = np.std(lev[mask])
        if sf == 0 or sl == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (lev[mask] - np.mean(lev[mask])) / (nm * sf * sl)
        return grad


class ROAMonotonicity(Restriction):
    """#17: Higher ROA → higher expected returns."""
    def __init__(self):
        super().__init__('roa_mono', 'production', 'B',
                         'ROA monotonicity')

    def penalty(self, f_hat, X, data_context):
        roa = data_context.get('roa', None)
        if roa is None:
            return 0.0
        mask = np.isfinite(roa) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], roa[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        roa = data_context.get('roa', None)
        n = len(f_hat)
        if roa is None:
            return np.zeros(n)
        mask = np.isfinite(roa) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], roa[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sr = np.std(roa[mask])
        if sf == 0 or sr == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (roa[mask] - np.mean(roa[mask])) / (nm * sf * sr)
        return grad


class GrossProfitMonotonicity(Restriction):
    """#18: Higher gross profitability → higher expected returns (Novy-Marx 2013)."""
    def __init__(self):
        super().__init__('gp_mono', 'production', 'B',
                         'Gross profitability monotonicity')

    def penalty(self, f_hat, X, data_context):
        gp = data_context.get('gp', None)
        if gp is None:
            return 0.0
        mask = np.isfinite(gp) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], gp[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        gp = data_context.get('gp', None)
        n = len(f_hat)
        if gp is None:
            return np.zeros(n)
        mask = np.isfinite(gp) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], gp[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sg = np.std(gp[mask])
        if sf == 0 or sg == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (gp[mask] - np.mean(gp[mask])) / (nm * sf * sg)
        return grad


class AssetGrowthEffect(Restriction):
    """#19: Higher asset growth → lower expected returns (Cooper et al. 2008)."""
    def __init__(self):
        super().__init__('ag_effect', 'production', 'B',
                         'Asset growth negative return effect')

    def penalty(self, f_hat, X, data_context):
        ag = data_context.get('ag', None)
        if ag is None:
            return 0.0
        mask = np.isfinite(ag) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], ag[mask])[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        ag = data_context.get('ag', None)
        n = len(f_hat)
        if ag is None:
            return np.zeros(n)
        mask = np.isfinite(ag) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], ag[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sa = np.std(ag[mask])
        if sf == 0 or sa == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (ag[mask] - np.mean(ag[mask])) / (nm * sf * sa)
        return grad


class RDIntensityEffect(Restriction):
    """#20: Higher R&D intensity → higher expected returns (Chan et al. 2001)."""
    def __init__(self):
        super().__init__('rd_effect', 'production', 'B',
                         'R&D intensity positive return effect')

    def penalty(self, f_hat, X, data_context):
        rd = data_context.get('rd_intensity', None)
        if rd is None:
            return 0.0
        mask = np.isfinite(rd) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], rd[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        rd = data_context.get('rd_intensity', None)
        n = len(f_hat)
        if rd is None:
            return np.zeros(n)
        mask = np.isfinite(rd) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], rd[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sr = np.std(rd[mask])
        if sf == 0 or sr == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (rd[mask] - np.mean(rd[mask])) / (nm * sf * sr)
        return grad


class QTheoryPricing(Restriction):
    """#21: Q-theory cross-sectional pricing.
    Expected return = f(I/K, ROE) with specific signs.
    """
    def __init__(self):
        super().__init__('q_theory_pricing', 'production', 'B',
                         'Q-theory cross-sectional pricing')

    def penalty(self, f_hat, X, data_context):
        ik = data_context.get('ik', None)
        roe = data_context.get('roe', None)
        if ik is None or roe is None:
            return 0.0
        mask = np.isfinite(ik) & np.isfinite(roe) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        # Q-theory: E[R] = f(I/K(-), ROE(+))
        # Regress f_hat on ik and roe, check signs
        X_q = np.column_stack([ik[mask], roe[mask], np.ones(mask.sum())])
        try:
            beta = np.linalg.lstsq(X_q, f_hat[mask], rcond=None)[0]
        except np.linalg.LinAlgError:
            return 0.0
        # Penalize wrong signs: beta_ik should be negative, beta_roe positive
        pen = max(0, beta[0]) ** 2 + max(0, -beta[1]) ** 2
        return pen

    def penalty_gradient(self, f_hat, X, data_context):
        ik = data_context.get('ik', None)
        roe = data_context.get('roe', None)
        n = len(f_hat)
        if ik is None or roe is None:
            return np.zeros(n)
        mask = np.isfinite(ik) & np.isfinite(roe) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return np.zeros(n)
        X_q = np.column_stack([ik[mask], roe[mask], np.ones(mask.sum())])
        try:
            beta = np.linalg.lstsq(X_q, f_hat[mask], rcond=None)[0]
        except np.linalg.LinAlgError:
            return np.zeros(n)
        # d(beta)/d(f) = (X'X)^{-1} X' (per-element)
        # d(penalty)/d(f) = d/d(beta) * d(beta)/d(f)
        try:
            XtX_inv = np.linalg.inv(X_q.T @ X_q)
        except np.linalg.LinAlgError:
            return np.zeros(n)
        dbeta_df = XtX_inv @ X_q.T  # (3, nm)
        # penalty = max(0,beta[0])^2 + max(0,-beta[1])^2
        grad = np.zeros(n)
        nm = mask.sum()
        if beta[0] > 0:
            grad[mask] += 2.0 * beta[0] * dbeta_df[0]
        if beta[1] < 0:
            grad[mask] += 2.0 * beta[1] * dbeta_df[1]  # d/d(beta1) of (-beta1)^2 = -2*(-beta1) but sign works out
        return grad


class CapexGrowthEffect(Restriction):
    """#22: Higher capex growth → lower expected returns."""
    def __init__(self):
        super().__init__('capex_growth', 'production', 'B',
                         'Capex growth negative return effect')

    def penalty(self, f_hat, X, data_context):
        grcapx = data_context.get('grcapx', None)
        if grcapx is None:
            return 0.0
        mask = np.isfinite(grcapx) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], grcapx[mask])[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        grcapx = data_context.get('grcapx', None)
        n = len(f_hat)
        if grcapx is None:
            return np.zeros(n)
        mask = np.isfinite(grcapx) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], grcapx[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sg = np.std(grcapx[mask])
        if sf == 0 or sg == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (grcapx[mask] - np.mean(grcapx[mask])) / (nm * sf * sg)
        return grad


class BookToMarketValue(Restriction):
    """#23: Higher book-to-market → higher expected returns (value effect)."""
    def __init__(self):
        super().__init__('bm_value', 'production', 'B',
                         'Book-to-market value effect')

    def penalty(self, f_hat, X, data_context):
        bm = data_context.get('bm', None)
        if bm is None:
            return 0.0
        mask = np.isfinite(bm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], bm[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        bm = data_context.get('bm', None)
        n = len(f_hat)
        if bm is None:
            return np.zeros(n)
        mask = np.isfinite(bm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], bm[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sb = np.std(bm[mask])
        if sf == 0 or sb == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (bm[mask] - np.mean(bm[mask])) / (nm * sf * sb)
        return grad


def register_production_restrictions(registry: RestrictionRegistry):
    """Register all 10 production restrictions."""
    restrictions = [
        InvestmentMonotonicity(),
        ProfitabilityMonotonicity(),
        LeverageEffect(),
        ROAMonotonicity(),
        GrossProfitMonotonicity(),
        AssetGrowthEffect(),
        RDIntensityEffect(),
        QTheoryPricing(),
        CapexGrowthEffect(),
        BookToMarketValue(),
    ]
    for r in restrictions:
        registry.register(r)
