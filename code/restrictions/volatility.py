"""
Type B: Variance/volatility restrictions (#44-45).

Based on volatility risk pricing and variance risk premium.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class VIXRiskPremium(Restriction):
    """#44: VIX predicts returns: higher VIX → higher expected returns.
    Variance risk premium is priced in the cross-section.
    """
    def __init__(self):
        super().__init__('vix_premium', 'volatility', 'B',
                         'VIX variance risk premium')

    def penalty(self, f_hat, X, data_context):
        vix = data_context.get('vix', None)
        if vix is None:
            return 0.0
        mask = np.isfinite(vix) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], vix[mask])[0, 1]
        # Higher VIX → higher returns (risk compensation)
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        vix = data_context.get('vix', None)
        n = len(f_hat)
        if vix is None:
            return np.zeros(n)
        mask = np.isfinite(vix) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], vix[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sv = np.std(vix[mask])
        if sf == 0 or sv == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (vix[mask] - np.mean(vix[mask])) / (nm * sf * sv)
        return grad


class RealizedVolEffect(Restriction):
    """#45: Realized variance predicts returns.
    Higher realized volatility → higher expected returns.
    """
    def __init__(self):
        super().__init__('realized_vol', 'volatility', 'B',
                         'Realized volatility risk premium')

    def penalty(self, f_hat, X, data_context):
        rv = data_context.get('realized_var', None)
        if rv is None:
            return 0.0
        mask = np.isfinite(rv) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], rv[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        rv = data_context.get('realized_var', None)
        n = len(f_hat)
        if rv is None:
            return np.zeros(n)
        mask = np.isfinite(rv) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], rv[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sr = np.std(rv[mask])
        if sf == 0 or sr == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (rv[mask] - np.mean(rv[mask])) / (nm * sf * sr)
        return grad


def register_volatility_restrictions(registry: RestrictionRegistry):
    """Register all 2 volatility restrictions."""
    for r in [VIXRiskPremium(), RealizedVolEffect()]:
        registry.register(r)
