"""
Type B/A: Behavioral restrictions (#46-51).

Based on momentum, reversals, and behavioral finance patterns
with theoretical grounding in underreaction/overreaction models.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class MomentumEffect(Restriction):
    """#46: Momentum: past winners continue to win (Jegadeesh-Titman 1993).
    Positive relationship between past 12-month return and expected return.
    """
    def __init__(self):
        super().__init__('momentum', 'behavioral', 'B',
                         'Momentum: past winners earn higher returns')

    def penalty(self, f_hat, X, data_context):
        mom = data_context.get('Mom12m', None)
        if mom is None:
            return 0.0
        mask = np.isfinite(mom) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], mom[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        mom = data_context.get('Mom12m', None)
        n = len(f_hat)
        if mom is None:
            return np.zeros(n)
        mask = np.isfinite(mom) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], mom[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sm = np.std(mom[mask])
        if sf == 0 or sm == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (mom[mask] - np.mean(mom[mask])) / (nm * sf * sm)
        return grad


class ShortTermReversal(Restriction):
    """#47: Short-term reversal: past month losers bounce back (Jegadeesh 1990).
    Negative relationship between past 1-month return and expected return.
    """
    def __init__(self):
        super().__init__('st_reversal', 'behavioral', 'B',
                         'Short-term reversal')

    def penalty(self, f_hat, X, data_context):
        strev = data_context.get('streversal', None)
        if strev is None:
            return 0.0
        mask = np.isfinite(strev) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], strev[mask])[0, 1]
        return max(0, corr) ** 2  # penalize positive correlation

    def penalty_gradient(self, f_hat, X, data_context):
        strev = data_context.get('streversal', None)
        n = len(f_hat)
        if strev is None:
            return np.zeros(n)
        mask = np.isfinite(strev) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], strev[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        ss = np.std(strev[mask])
        if sf == 0 or ss == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (strev[mask] - np.mean(strev[mask])) / (nm * sf * ss)
        return grad


class LongTermReversal(Restriction):
    """#48: Long-term reversal: 3-5 year losers rebound (DeBondt-Thaler 1985).
    Negative relationship between past 3-5 year return and expected return.
    """
    def __init__(self):
        super().__init__('lt_reversal', 'behavioral', 'B',
                         'Long-term reversal')

    def penalty(self, f_hat, X, data_context):
        lrrev = data_context.get('LRreversal', None)
        if lrrev is None:
            return 0.0
        mask = np.isfinite(lrrev) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], lrrev[mask])[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        lrrev = data_context.get('LRreversal', None)
        n = len(f_hat)
        if lrrev is None:
            return np.zeros(n)
        mask = np.isfinite(lrrev) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], lrrev[mask])[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sl = np.std(lrrev[mask])
        if sf == 0 or sl == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (lrrev[mask] - np.mean(lrrev[mask])) / (nm * sf * sl)
        return grad


class SentimentInteraction(Restriction):
    """#49: Behavioral patterns are stronger when sentiment is high.
    Momentum and value effects interact with sentiment (Stambaugh et al. 2012).
    """
    def __init__(self):
        super().__init__('sentiment_interaction', 'behavioral', 'A',
                         'Anomalies stronger in high-sentiment periods')

    def penalty(self, f_hat, X, data_context):
        sent = data_context.get('sentiment', None)
        mom = data_context.get('Mom12m', None)
        if sent is None or mom is None:
            return 0.0
        mask = np.isfinite(sent) & np.isfinite(mom) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        high_sent = sent[mask] > np.median(sent[mask])
        if high_sent.sum() < 5 or (~high_sent).sum() < 5:
            return 0.0
        corr_high = np.corrcoef(f_hat[mask][high_sent], mom[mask][high_sent])[0, 1]
        corr_low = np.corrcoef(f_hat[mask][~high_sent], mom[mask][~high_sent])[0, 1]
        return max(0, corr_low - corr_high) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        sent = data_context.get('sentiment', None)
        mom = data_context.get('Mom12m', None)
        n = len(f_hat)
        if sent is None or mom is None:
            return np.zeros(n)
        mask = np.isfinite(sent) & np.isfinite(mom) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return np.zeros(n)
        high_sent = sent[mask] > np.median(sent[mask])
        if high_sent.sum() < 5 or (~high_sent).sum() < 5:
            return np.zeros(n)
        corr_high = np.corrcoef(f_hat[mask][high_sent], mom[mask][high_sent])[0, 1]
        corr_low = np.corrcoef(f_hat[mask][~high_sent], mom[mask][~high_sent])[0, 1]
        diff = corr_low - corr_high
        if diff <= 0:
            return np.zeros(n)
        # d(corr)/d(f) within each group
        grad = np.zeros(n)
        idx = np.where(mask)[0]
        # High sentiment group: want to increase corr_high → gradient via dcorr/df
        f_h = f_hat[mask][high_sent]
        m_h = mom[mask][high_sent]
        sf_h, sm_h = np.std(f_h), np.std(m_h)
        nh = high_sent.sum()
        if sf_h > 0 and sm_h > 0:
            dcorr_h = (m_h - np.mean(m_h)) / (nh * sf_h * sm_h)
            grad[idx[high_sent]] += 2.0 * diff * dcorr_h  # +dcorr_high reduces penalty

        # Low sentiment group: want to decrease corr_low
        f_l = f_hat[mask][~high_sent]
        m_l = mom[mask][~high_sent]
        sf_l, sm_l = np.std(f_l), np.std(m_l)
        nl = (~high_sent).sum()
        if sf_l > 0 and sm_l > 0:
            dcorr_l = (m_l - np.mean(m_l)) / (nl * sf_l * sm_l)
            grad[idx[~high_sent]] += -2.0 * diff * dcorr_l  # -dcorr_low reduces penalty
        return grad


class OverreactionCorrection(Restriction):
    """#50: Overreaction-correction model.
    Extreme past returns (either direction) → mean reversion.
    """
    def __init__(self):
        super().__init__('overreaction', 'behavioral', 'A',
                         'Overreaction correction for extreme returns')

    def penalty(self, f_hat, X, data_context):
        mom = data_context.get('Mom12m', None)
        if mom is None:
            return 0.0
        mask = np.isfinite(mom) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        extreme = np.abs(mom[mask]) > np.percentile(np.abs(mom[mask]), 90)
        if extreme.sum() < 5:
            return 0.0
        mean_extreme_pred = np.mean(np.abs(f_hat[mask][extreme]))
        mean_normal_pred = np.mean(np.abs(f_hat[mask][~extreme]))
        return max(0, mean_extreme_pred - 2 * mean_normal_pred) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        mom = data_context.get('Mom12m', None)
        n = len(f_hat)
        if mom is None:
            return np.zeros(n)
        mask = np.isfinite(mom) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return np.zeros(n)
        extreme = np.abs(mom[mask]) > np.percentile(np.abs(mom[mask]), 90)
        if extreme.sum() < 5:
            return np.zeros(n)
        mean_extreme = np.mean(np.abs(f_hat[mask][extreme]))
        mean_normal = np.mean(np.abs(f_hat[mask][~extreme]))
        diff = mean_extreme - 2 * mean_normal
        if diff <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        idx = np.where(mask)[0]
        n_ext = extreme.sum()
        n_norm = (~extreme).sum()
        # d|f|/df = sign(f)
        grad[idx[extreme]] = 2.0 * diff * np.sign(f_hat[mask][extreme]) / n_ext
        grad[idx[~extreme]] = -2.0 * diff * 2.0 * np.sign(f_hat[mask][~extreme]) / n_norm
        return grad


class DispositionEffect(Restriction):
    """#51: Disposition effect creates predictable return patterns.
    Stocks with unrealized gains tend to have lower future returns
    (Frazzini 2006 capital gains overhang).
    """
    def __init__(self):
        super().__init__('disposition_effect', 'behavioral', 'B',
                         'Disposition effect return predictability')

    def penalty(self, f_hat, X, data_context):
        mom = data_context.get('Mom12m', None)
        strev = data_context.get('streversal', None)
        if mom is None or strev is None:
            return 0.0
        mask = np.isfinite(mom) & np.isfinite(strev) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        # Capital gains overhang proxy: mom - strev (long-term gain minus recent)
        cgo = mom[mask] - strev[mask]
        if np.std(cgo) == 0:
            return 0.0
        corr = np.corrcoef(f_hat[mask], cgo)[0, 1]
        # Higher unrealized gains → lower future returns (disposition → selling pressure)
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        mom = data_context.get('Mom12m', None)
        strev = data_context.get('streversal', None)
        n = len(f_hat)
        if mom is None or strev is None:
            return np.zeros(n)
        mask = np.isfinite(mom) & np.isfinite(strev) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return np.zeros(n)
        cgo = mom[mask] - strev[mask]
        if np.std(cgo) == 0:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], cgo)[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sc = np.std(cgo)
        if sf == 0 or sc == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (cgo - np.mean(cgo)) / (nm * sf * sc)
        return grad


def register_behavioral_restrictions(registry: RestrictionRegistry):
    """Register all 6 behavioral restrictions."""
    restrictions = [
        MomentumEffect(),
        ShortTermReversal(),
        LongTermReversal(),
        SentimentInteraction(),
        OverreactionCorrection(),
        DispositionEffect(),
    ]
    for r in restrictions:
        registry.register(r)
