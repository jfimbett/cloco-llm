"""
Type C: Intermediary/institutional restrictions (#24-31).

Based on intermediary asset pricing models:
He-Krishnamurthy (2013), Adrian-Etula-Muir (2014),
and sentiment-based restrictions.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class HKMCapitalRatio(Restriction):
    """#24: He-Krishnamurthy-Manela intermediary capital ratio.
    Higher capital ratio → lower risk premium → lower expected returns.
    """
    def __init__(self):
        super().__init__('hkm_capital', 'intermediary', 'C',
                         'HKM capital ratio predicts returns negatively')

    def penalty(self, f_hat, X, data_context):
        hkm = data_context.get('hkm_capital_ratio', None)
        if hkm is None:
            return 0.0
        mask = np.isfinite(hkm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], hkm[mask])[0, 1]
        return max(0, corr) ** 2  # penalize positive correlation

    def penalty_gradient(self, f_hat, X, data_context):
        hkm = data_context.get('hkm_capital_ratio', None)
        n = len(f_hat)
        if hkm is None:
            return np.zeros(n)
        mask = np.isfinite(hkm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], hkm[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sh = np.std(hkm[mask])
        if sf == 0 or sh == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (hkm[mask] - np.mean(hkm[mask])) / (nm * sf * sh)
        return grad


class HKMFactorPricing(Restriction):
    """#25: HKM intermediary risk factor prices the cross-section.
    Assets with higher beta to HKM factor earn higher returns.
    """
    def __init__(self):
        super().__init__('hkm_factor', 'intermediary', 'C',
                         'HKM factor beta prices cross-section')

    def penalty(self, f_hat, X, data_context):
        hkm_f = data_context.get('hkm_risk_factor', None)
        if hkm_f is None:
            return 0.0
        mask = np.isfinite(hkm_f) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        # Beta to HKM factor
        var_f = np.var(hkm_f[mask])
        if var_f == 0:
            return 0.0
        beta = np.cov(f_hat[mask], hkm_f[mask])[0, 1] / var_f
        # Risk premium: higher beta → higher expected return
        # Penalize if relationship is wrong sign
        return max(0, -beta) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        hkm_f = data_context.get('hkm_risk_factor', None)
        n = len(f_hat)
        if hkm_f is None:
            return np.zeros(n)
        mask = np.isfinite(hkm_f) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        var_f = np.var(hkm_f[mask])
        if var_f == 0:
            return np.zeros(n)
        beta = np.cov(f_hat[mask], hkm_f[mask])[0, 1] / var_f
        if beta >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        nm = mask.sum()
        grad[mask] = -2.0 * beta * (hkm_f[mask] - np.mean(hkm_f[mask])) / (nm * var_f)
        return grad


class IntermediaryEuler(Restriction):
    """#26: Intermediary SDF Euler equation.
    E[M_I * R] = 1 where M_I depends on intermediary capital ratio.
    """
    def __init__(self, gamma: float = 5.0):
        super().__init__('intermediary_euler', 'intermediary', 'C',
                         'Intermediary SDF Euler equation')
        self.gamma = gamma

    def penalty(self, f_hat, X, data_context):
        hkm = data_context.get('hkm_capital_ratio', None)
        if hkm is None:
            return 0.0
        mask = np.isfinite(hkm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        # Intermediary SDF: M_I ∝ (η_t)^{-γ} where η is capital ratio
        log_m = -self.gamma * np.log(np.maximum(hkm[mask], 0.01))
        m = np.exp(log_m - np.max(log_m))  # normalize for numerical stability
        euler_err = np.mean(m * (1.0 + f_hat[mask])) - np.mean(m)
        return euler_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        hkm = data_context.get('hkm_capital_ratio', None)
        n = len(f_hat)
        if hkm is None:
            return np.zeros(n)
        mask = np.isfinite(hkm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        log_m = -self.gamma * np.log(np.maximum(hkm[mask], 0.01))
        m = np.exp(log_m - np.max(log_m))
        euler_err = np.mean(m * (1.0 + f_hat[mask])) - np.mean(m)
        grad = np.zeros(n)
        nm = mask.sum()
        grad[mask] = 2.0 * euler_err * m / nm
        return grad


class SentimentEffect(Restriction):
    """#27: Baker-Wurgler sentiment predicts returns.
    High sentiment → low subsequent returns (overpricing correction).
    """
    def __init__(self):
        super().__init__('sentiment_effect', 'intermediary', 'C',
                         'Sentiment negatively predicts returns')

    def penalty(self, f_hat, X, data_context):
        sent = data_context.get('sentiment', None)
        if sent is None:
            return 0.0
        mask = np.isfinite(sent) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], sent[mask])[0, 1]
        return max(0, corr) ** 2  # penalize positive correlation

    def penalty_gradient(self, f_hat, X, data_context):
        sent = data_context.get('sentiment', None)
        n = len(f_hat)
        if sent is None:
            return np.zeros(n)
        mask = np.isfinite(sent) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], sent[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        ss = np.std(sent[mask])
        if sf == 0 or ss == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (sent[mask] - np.mean(sent[mask])) / (nm * sf * ss)
        return grad


class SentimentCrossSection(Restriction):
    """#28: Sentiment differentially affects hard-to-value stocks.
    Small, young, volatile stocks more affected by sentiment.
    """
    def __init__(self):
        super().__init__('sentiment_xs', 'intermediary', 'C',
                         'Sentiment cross-sectional effect (size interaction)')

    def penalty(self, f_hat, X, data_context):
        sent = data_context.get('sentiment', None)
        me = data_context.get('me', None)
        if sent is None or me is None:
            return 0.0
        mask = np.isfinite(sent) & np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        interaction = sent[mask] / np.maximum(me[mask], 1e-6)
        corr = np.corrcoef(f_hat[mask], interaction)[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        sent = data_context.get('sentiment', None)
        me = data_context.get('me', None)
        n = len(f_hat)
        if sent is None or me is None:
            return np.zeros(n)
        mask = np.isfinite(sent) & np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return np.zeros(n)
        interaction = sent[mask] / np.maximum(me[mask], 1e-6)
        corr = np.corrcoef(f_hat[mask], interaction)[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        si = np.std(interaction)
        if sf == 0 or si == 0:
            return grad
        nm = mask.sum()
        dcorr = (interaction - np.mean(interaction)) / (nm * sf * si)
        grad[mask] = 2.0 * corr * dcorr
        return grad


class LeverageCycle(Restriction):
    """#29: Adrian-Etula-Muir leverage cycle.
    Broker-dealer leverage predicts returns.
    """
    def __init__(self):
        super().__init__('leverage_cycle', 'intermediary', 'C',
                         'Leverage cycle return predictability')

    def penalty(self, f_hat, X, data_context):
        hkm = data_context.get('hkm_capital_ratio', None)
        if hkm is None:
            return 0.0
        mask = np.isfinite(hkm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        leverage_proxy = 1.0 / np.maximum(hkm[mask], 0.01)
        corr = np.corrcoef(f_hat[mask], leverage_proxy)[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        hkm = data_context.get('hkm_capital_ratio', None)
        n = len(f_hat)
        if hkm is None:
            return np.zeros(n)
        mask = np.isfinite(hkm) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        leverage_proxy = 1.0 / np.maximum(hkm[mask], 0.01)
        corr = np.corrcoef(f_hat[mask], leverage_proxy)[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sl = np.std(leverage_proxy)
        if sf == 0 or sl == 0:
            return grad
        nm = mask.sum()
        dcorr = (leverage_proxy - np.mean(leverage_proxy)) / (nm * sf * sl)
        grad[mask] = -2.0 * corr * dcorr
        return grad


class FundingLiquidity(Restriction):
    """#30: Funding liquidity constraint.
    Tighter funding conditions → higher required returns.
    """
    def __init__(self):
        super().__init__('funding_liquidity', 'intermediary', 'C',
                         'Funding liquidity constraint')

    def penalty(self, f_hat, X, data_context):
        ebp = data_context.get('ebp', None)
        if ebp is None:
            return 0.0
        mask = np.isfinite(ebp) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        # EBP (excess bond premium) proxies funding stress
        # Higher EBP → higher required returns
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


class InstitutionalOwnershipEffect(Restriction):
    """#31: Institutional constraints affect pricing.
    Stocks with limited institutional participation are mispriced.
    """
    def __init__(self):
        super().__init__('institutional_ownership', 'intermediary', 'C',
                         'Institutional ownership pricing effect')

    def penalty(self, f_hat, X, data_context):
        # Use size as proxy for institutional participation
        me = data_context.get('me', None)
        if me is None:
            return 0.0
        mask = np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        # Small stocks (less institutional) should have higher expected returns
        corr = np.corrcoef(f_hat[mask], me[mask])[0, 1]
        return max(0, corr) ** 2  # penalize if large stocks have higher predicted returns

    def penalty_gradient(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        n = len(f_hat)
        if me is None:
            return np.zeros(n)
        mask = np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], me[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sm = np.std(me[mask])
        if sf == 0 or sm == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (me[mask] - np.mean(me[mask])) / (nm * sf * sm)
        return grad


def register_intermediary_restrictions(registry: RestrictionRegistry):
    """Register all 8 intermediary restrictions."""
    restrictions = [
        HKMCapitalRatio(),
        HKMFactorPricing(),
        IntermediaryEuler(),
        SentimentEffect(),
        SentimentCrossSection(),
        LeverageCycle(),
        FundingLiquidity(),
        InstitutionalOwnershipEffect(),
    ]
    for r in restrictions:
        registry.register(r)
