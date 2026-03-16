"""
Type A: Information and learning restrictions (#32-37).

Based on information frictions, learning models,
forecast dispersion, and macro uncertainty.
All restrictions are Type A (Euler equation penalties).
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class ForecastDispersionEffect(Restriction):
    """#32: Higher analyst forecast dispersion → higher expected returns.
    Information uncertainty premium (Diether et al. 2002).
    """
    def __init__(self):
        super().__init__('forecast_dispersion', 'information', 'A',
                         'Forecast dispersion uncertainty premium')

    def penalty(self, f_hat, X, data_context):
        fd = data_context.get('ForecastDispersion', None)
        if fd is None:
            return 0.0
        mask = np.isfinite(fd) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], fd[mask])[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        fd = data_context.get('ForecastDispersion', None)
        n = len(f_hat)
        if fd is None:
            return np.zeros(n)
        mask = np.isfinite(fd) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], fd[mask])[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sfd = np.std(fd[mask])
        if sf == 0 or sfd == 0:
            return grad
        nm = mask.sum()
        grad[mask] = -2.0 * corr * (fd[mask] - np.mean(fd[mask])) / (nm * sf * sfd)
        return grad


class MacroUncertaintyPricing(Restriction):
    """#33: Macro uncertainty commands a risk premium.
    Higher VIX → higher expected returns.
    """
    def __init__(self):
        super().__init__('macro_uncertainty', 'information', 'A',
                         'Macro uncertainty risk premium (VIX)')

    def penalty(self, f_hat, X, data_context):
        vix = data_context.get('vix', None)
        if vix is None:
            return 0.0
        mask = np.isfinite(vix) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        corr = np.corrcoef(f_hat[mask], vix[mask])[0, 1]
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


class InformationLearningEuler(Restriction):
    """#34: Bayesian learning Euler equation.
    When investors learn about persistent parameters, risk premia
    depend on posterior uncertainty.
    """
    def __init__(self, gamma: float = 5.0):
        super().__init__('learning_euler', 'information', 'A',
                         'Bayesian learning Euler equation')
        self.gamma = gamma

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        vix = data_context.get('vix', None)
        if vix is None:
            return 0.0
        mask = np.isfinite(vix) & np.isfinite(cg) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        # Under learning: risk premium has additional term from parameter uncertainty
        # Simplified: E[R] ≈ γ·Var(Δc) + γ²·σ²_μ where σ²_μ ∝ VIX²
        uncertainty_premium = self.gamma ** 2 * np.var(vix[mask]) / 10000
        mean_pred = np.mean(f_hat[mask])
        base_premium = self.gamma * np.var(cg[mask])
        target = base_premium + uncertainty_premium
        return (mean_pred - target) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        vix = data_context.get('vix', None)
        n = len(f_hat)
        if vix is None:
            return np.zeros(n)
        mask = np.isfinite(vix) & np.isfinite(cg) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        uncertainty_premium = self.gamma ** 2 * np.var(vix[mask]) / 10000
        base_premium = self.gamma * np.var(cg[mask])
        target = base_premium + uncertainty_premium
        mean_pred = np.mean(f_hat[mask])
        grad = np.zeros(n)
        nm = mask.sum()
        grad[mask] = 2.0 * (mean_pred - target) / nm
        return grad


class AmbiguityAversion(Restriction):
    """#35: Ambiguity aversion pricing (Epstein-Schneider 2008).
    Ambiguity-averse investors overweight worst-case scenarios.
    """
    def __init__(self):
        super().__init__('ambiguity_aversion', 'information', 'A',
                         'Ambiguity aversion pricing restriction')

    def penalty(self, f_hat, X, data_context):
        vix = data_context.get('vix', None)
        if vix is None:
            return 0.0
        mask = np.isfinite(vix) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        high_vix = vix[mask] > np.median(vix[mask])
        if high_vix.sum() < 5 or (~high_vix).sum() < 5:
            return 0.0
        var_high = np.var(f_hat[mask][high_vix])
        var_low = np.var(f_hat[mask][~high_vix])
        return max(0, var_low - var_high) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        vix = data_context.get('vix', None)
        n = len(f_hat)
        if vix is None:
            return np.zeros(n)
        mask = np.isfinite(vix) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        high_vix = vix[mask] > np.median(vix[mask])
        if high_vix.sum() < 5 or (~high_vix).sum() < 5:
            return np.zeros(n)
        var_high = np.var(f_hat[mask][high_vix])
        var_low = np.var(f_hat[mask][~high_vix])
        diff = var_low - var_high
        if diff <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        idx = np.where(mask)[0]
        # d(var)/d(f_i) = 2(f_i - mean)/n for observations in that group
        f_h = f_hat[mask][high_vix]
        f_l = f_hat[mask][~high_vix]
        nh, nl = len(f_h), len(f_l)
        # Want var_high to increase and var_low to decrease
        grad[idx[high_vix]] = -2.0 * diff * 2.0 * (f_h - np.mean(f_h)) / nh
        grad[idx[~high_vix]] = 2.0 * diff * 2.0 * (f_l - np.mean(f_l)) / nl
        return grad


class RationalInattention(Restriction):
    """#36: Rational inattention (Sims 2003, Mackowiak-Wiederholt 2009).
    Limited attention → prices respond slowly to information.
    """
    def __init__(self):
        super().__init__('rational_inattention', 'information', 'A',
                         'Rational inattention slow price response')

    def penalty(self, f_hat, X, data_context):
        idio_vol = data_context.get('IdioVol3F', None)
        if idio_vol is None:
            return 0.0
        mask = np.isfinite(idio_vol) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        high_vol = idio_vol[mask] > np.median(idio_vol[mask])
        if high_vol.sum() < 5 or (~high_vol).sum() < 5:
            return 0.0
        var_high = np.var(f_hat[mask][high_vol])
        var_low = np.var(f_hat[mask][~high_vol])
        return max(0, var_low - var_high) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        idio_vol = data_context.get('IdioVol3F', None)
        n = len(f_hat)
        if idio_vol is None:
            return np.zeros(n)
        mask = np.isfinite(idio_vol) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        high_vol = idio_vol[mask] > np.median(idio_vol[mask])
        if high_vol.sum() < 5 or (~high_vol).sum() < 5:
            return np.zeros(n)
        var_high = np.var(f_hat[mask][high_vol])
        var_low = np.var(f_hat[mask][~high_vol])
        diff = var_low - var_high
        if diff <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        idx = np.where(mask)[0]
        f_h = f_hat[mask][high_vol]
        f_l = f_hat[mask][~high_vol]
        nh, nl = len(f_h), len(f_l)
        grad[idx[high_vol]] = -2.0 * diff * 2.0 * (f_h - np.mean(f_h)) / nh
        grad[idx[~high_vol]] = 2.0 * diff * 2.0 * (f_l - np.mean(f_l)) / nl
        return grad


class ConsumptionDisagreement(Restriction):
    """#37: Disagreement about consumption growth.
    Heterogeneous beliefs create risk premium from disagreement.
    """
    def __init__(self):
        super().__init__('cons_disagreement', 'information', 'A',
                         'Consumption disagreement risk premium')

    def penalty(self, f_hat, X, data_context):
        fd = data_context.get('ForecastDispersion', None)
        cg = data_context.get('cons_growth', None)
        if fd is None or cg is None:
            return 0.0
        mask = np.isfinite(fd) & np.isfinite(cg) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        interaction = fd[mask] * np.abs(cg[mask])
        corr = np.corrcoef(f_hat[mask], interaction)[0, 1]
        return max(0, -corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        fd = data_context.get('ForecastDispersion', None)
        cg = data_context.get('cons_growth', None)
        n = len(f_hat)
        if fd is None or cg is None:
            return np.zeros(n)
        mask = np.isfinite(fd) & np.isfinite(cg) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        interaction = fd[mask] * np.abs(cg[mask])
        corr = np.corrcoef(f_hat[mask], interaction)[0, 1]
        if corr >= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        si = np.std(interaction)
        if sf == 0 or si == 0:
            return grad
        nm = mask.sum()
        dcorr = (interaction - np.mean(interaction)) / (nm * sf * si)
        grad[mask] = -2.0 * corr * dcorr
        return grad


def register_information_restrictions(registry: RestrictionRegistry):
    """Register all 6 information restrictions."""
    restrictions = [
        ForecastDispersionEffect(),
        MacroUncertaintyPricing(),
        InformationLearningEuler(),
        AmbiguityAversion(),
        RationalInattention(),
        ConsumptionDisagreement(),
    ]
    for r in restrictions:
        registry.register(r)
