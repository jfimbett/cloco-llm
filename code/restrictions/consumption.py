"""
Type A: Consumption Euler restrictions (#1-13).

Based on consumption-based asset pricing models:
Campbell-Cochrane (1999) external habit, Bansal-Yaron (2004) long-run risk,
Epstein-Zin preferences, and variants.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class EulerCAPM(Restriction):
    """#1: Basic consumption CAPM Euler equation.
    E[M_{t+1} R_{i,t+1}] = 1 where M = β(C_{t+1}/C_t)^{-γ}
    Penalty: (E[Δc · R] - target)² averaged over assets.
    """
    def __init__(self, gamma: float = 2.0, beta: float = 0.995):
        super().__init__('euler_capm', 'consumption', 'A',
                         'Basic C-CAPM Euler: E[M*R]=1')
        self.gamma = gamma
        self.beta = beta

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        # log SDF ≈ log(β) - γ·Δc
        log_m = np.log(self.beta) - self.gamma * cg
        # Euler: E[exp(log_m) * (1 + f_hat)] ≈ 1
        euler_err = np.mean(np.exp(log_m) * (1.0 + f_hat)) - 1.0
        return euler_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        log_m = np.log(self.beta) - self.gamma * cg
        m = np.exp(log_m)
        euler_err = np.mean(m * (1.0 + f_hat)) - 1.0
        n = len(f_hat)
        return 2.0 * euler_err * m / n


class EulerHabit(Restriction):
    """#2: Campbell-Cochrane (1999) external habit Euler.
    SDF depends on surplus consumption ratio S_t.
    Penalty: squared Euler error with habit-adjusted M.
    """
    def __init__(self, gamma: float = 2.0, phi: float = 0.87, s_bar: float = 0.057):
        super().__init__('euler_habit', 'consumption', 'A',
                         'Campbell-Cochrane habit Euler')
        self.gamma = gamma
        self.phi = phi
        self.s_bar = s_bar

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        # Approximate surplus ratio dynamics
        # M ≈ β exp(-γ(Δc + λ(s)·v)) — simplified to γ_eff · Δc
        gamma_eff = self.gamma * (1.0 + 1.0 / self.s_bar)
        euler_err = np.mean(-gamma_eff * cg * f_hat)
        return euler_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        gamma_eff = self.gamma * (1.0 + 1.0 / self.s_bar)
        euler_err = np.mean(-gamma_eff * cg * f_hat)
        n = len(f_hat)
        return 2.0 * euler_err * (-gamma_eff * cg) / n


class EulerLRR(Restriction):
    """#3: Bansal-Yaron (2004) long-run risk Euler.
    Expected return depends on exposure to long-run consumption risk.
    """
    def __init__(self, gamma: float = 10.0, psi: float = 1.5):
        super().__init__('euler_lrr', 'consumption', 'A',
                         'Bansal-Yaron long-run risk Euler')
        self.gamma = gamma
        self.psi = psi

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        mktrf = data_context.get('mktrf', np.zeros_like(f_hat))
        # LRR: expected return ∝ γ·Cov(R, Δc) + (γ-1/ψ)·Cov(R, x_t)
        # Simplified: penalize deviation from risk-return tradeoff
        cov_rc = np.mean(f_hat * cg) - np.mean(f_hat) * np.mean(cg)
        target = self.gamma * np.var(cg)
        return (np.mean(f_hat) - target) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        target = self.gamma * np.var(cg)
        n = len(f_hat)
        return 2.0 * (np.mean(f_hat) - target) * np.ones(n) / n


class EulerEZCAPM(Restriction):
    """#4: Epstein-Zin CAPM Euler.
    Two-factor: consumption growth and market return.
    """
    def __init__(self, gamma: float = 10.0, psi: float = 1.5, beta: float = 0.995):
        super().__init__('euler_ez_capm', 'consumption', 'A',
                         'Epstein-Zin two-factor Euler')
        self.gamma = gamma
        self.psi = psi
        self.beta = beta
        self.theta = (1 - gamma) / (1 - 1/psi)

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        mktrf = data_context.get('mktrf', np.zeros_like(f_hat))
        # EZ SDF: m = θ·log(β) - (θ/ψ)·Δc + (θ-1)·r_m
        log_m = (self.theta * np.log(self.beta)
                 - (self.theta / self.psi) * cg
                 + (self.theta - 1) * mktrf)
        euler_err = np.mean(np.exp(log_m) * (1.0 + f_hat)) - 1.0
        return euler_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        mktrf = data_context.get('mktrf', np.zeros_like(f_hat))
        log_m = (self.theta * np.log(self.beta)
                 - (self.theta / self.psi) * cg
                 + (self.theta - 1) * mktrf)
        m = np.exp(log_m)
        euler_err = np.mean(m * (1.0 + f_hat)) - 1.0
        n = len(f_hat)
        return 2.0 * euler_err * m / n


class ConsGrowthMonotonicity(Restriction):
    """#5: Higher consumption growth → lower expected excess returns.
    Monotonicity in consumption growth (negative relationship).
    """
    def __init__(self):
        super().__init__('cons_growth_mono', 'consumption', 'A',
                         'Consumption growth monotonicity')

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        # Penalize positive correlation between f_hat and cons_growth
        corr = np.corrcoef(f_hat, cg)[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        n = len(f_hat)
        corr = np.corrcoef(f_hat, cg)[0, 1]
        if corr <= 0:
            return np.zeros(n)
        # d(corr)/d(f_hat) ≈ (cg - mean(cg)) / (n * std(f) * std(cg))
        sf = np.std(f_hat, ddof=0)
        sc = np.std(cg, ddof=0)
        if sf == 0 or sc == 0:
            return np.zeros(n)
        dcorr = (cg - np.mean(cg)) / (n * sf * sc)
        return 2.0 * corr * dcorr


class EulerConditionalCAPM(Restriction):
    """#6: Conditional C-CAPM with time-varying γ.
    Risk aversion proxied by aggregate conditions.
    """
    def __init__(self, gamma_base: float = 2.0):
        super().__init__('euler_cond_capm', 'consumption', 'A',
                         'Conditional C-CAPM Euler')
        self.gamma_base = gamma_base

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        cay = data_context.get('cay', np.zeros_like(f_hat))
        # Time-varying γ = γ_base + δ·cay
        gamma_t = self.gamma_base + 5.0 * cay
        euler_err = np.mean(-gamma_t * cg * (1.0 + f_hat))
        return euler_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        cay = data_context.get('cay', np.zeros_like(f_hat))
        gamma_t = self.gamma_base + 5.0 * cay
        euler_err = np.mean(-gamma_t * cg * (1.0 + f_hat))
        n = len(f_hat)
        return 2.0 * euler_err * (-gamma_t * cg) / n


class EulerDurableNondurable(Restriction):
    """#7: Two-good Euler with durable and nondurable consumption."""
    def __init__(self, gamma: float = 2.0, alpha: float = 0.8):
        super().__init__('euler_durable', 'consumption', 'A',
                         'Durable-nondurable consumption Euler')
        self.gamma = gamma
        self.alpha = alpha

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        # Approximate: penalize similar to basic CAPM but with adjusted γ
        gamma_adj = self.gamma / self.alpha
        euler_err = np.mean(-gamma_adj * cg * f_hat)
        return euler_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        gamma_adj = self.gamma / self.alpha
        euler_err = np.mean(-gamma_adj * cg * f_hat)
        n = len(f_hat)
        return 2.0 * euler_err * (-gamma_adj * cg) / n


class ConsumptionBeta(Restriction):
    """#8: Cross-sectional consumption beta pricing.
    E[R_i] = λ · β_i^c where β_i^c = Cov(R_i, Δc)/Var(Δc).
    """
    def __init__(self):
        super().__init__('cons_beta_pricing', 'consumption', 'A',
                         'Consumption beta cross-sectional pricing')

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        var_cg = np.var(cg)
        if var_cg == 0:
            return 0.0
        beta_c = (f_hat * cg - np.mean(f_hat) * np.mean(cg)) / var_cg
        # lambda should be positive (risk premium for consumption risk)
        lam = np.mean(f_hat * beta_c) / (np.mean(beta_c ** 2) + 1e-10)
        resid = f_hat - lam * beta_c
        return np.mean(resid ** 2)

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        n = len(f_hat)
        var_cg = np.var(cg)
        if var_cg == 0:
            return np.zeros(n)
        beta_c = (f_hat * cg - np.mean(f_hat) * np.mean(cg)) / var_cg
        lam = np.mean(f_hat * beta_c) / (np.mean(beta_c ** 2) + 1e-10)
        resid = f_hat - lam * beta_c
        return 2.0 * resid / n


class RecursiveUtilityEuler(Restriction):
    """#9: Recursive utility Euler with wealth-consumption ratio."""
    def __init__(self, gamma: float = 10.0, psi: float = 1.5):
        super().__init__('recursive_utility', 'consumption', 'A',
                         'Recursive utility Euler')
        self.gamma = gamma
        self.psi = psi

    def penalty(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        mktrf = data_context.get('mktrf', np.zeros_like(f_hat))
        # θ = (1-γ)/(1-1/ψ)
        theta = (1 - self.gamma) / (1 - 1.0 / self.psi)
        pricing_err = np.mean(f_hat + (theta / self.psi) * cg - (theta - 1) * mktrf)
        return pricing_err ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        mktrf = data_context.get('mktrf', np.zeros_like(f_hat))
        theta = (1 - self.gamma) / (1 - 1.0 / self.psi)
        pricing_err = np.mean(f_hat + (theta / self.psi) * cg - (theta - 1) * mktrf)
        n = len(f_hat)
        return 2.0 * pricing_err * np.ones(n) / n


class DisasterRiskEuler(Restriction):
    """#10: Rare disaster risk Euler (Barro 2006, Gabaix 2012).
    Risk premium driven by disaster probability and size.
    """
    def __init__(self, gamma: float = 4.0, p_disaster: float = 0.017, b: float = 0.4):
        super().__init__('disaster_risk', 'consumption', 'A',
                         'Rare disaster risk Euler')
        self.gamma = gamma
        self.p_disaster = p_disaster
        self.b = b

    def penalty(self, f_hat, X, data_context):
        # Disaster risk premium ≈ p · E[b^γ - 1]
        disaster_premium = self.p_disaster * ((1 - self.b) ** (-self.gamma) - 1)
        # Expected return should be at least this large on average
        mean_pred = np.mean(f_hat)
        # Penalize if mean prediction is too far from disaster-implied level
        return (mean_pred - disaster_premium * 0.5) ** 2  # 0.5 = share of systematic risk

    def penalty_gradient(self, f_hat, X, data_context):
        disaster_premium = self.p_disaster * ((1 - self.b) ** (-self.gamma) - 1)
        mean_pred = np.mean(f_hat)
        n = len(f_hat)
        return 2.0 * (mean_pred - disaster_premium * 0.5) * np.ones(n) / n


class IntertemporalSubstitution(Restriction):
    """#11: Intertemporal substitution effect.
    High EIS → less negative response to interest rate changes.
    """
    def __init__(self, psi: float = 1.5):
        super().__init__('intertemporal_sub', 'consumption', 'A',
                         'Intertemporal substitution restriction')
        self.psi = psi

    def penalty(self, f_hat, X, data_context):
        rf = data_context.get('rf', np.zeros_like(f_hat))
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        # Δc ≈ ψ · r_f → penalize deviation from this relationship
        resid = cg - self.psi * rf
        # Penalty: predicted returns should be consistent with this
        corr = np.corrcoef(f_hat, resid)[0, 1] if np.std(f_hat) > 0 else 0
        return corr ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        rf = data_context.get('rf', np.zeros_like(f_hat))
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        resid = cg - self.psi * rf
        n = len(f_hat)
        sf = np.std(f_hat, ddof=0)
        sr = np.std(resid, ddof=0)
        if sf == 0 or sr == 0:
            return np.zeros(n)
        corr = np.corrcoef(f_hat, resid)[0, 1]
        dcorr = (resid - np.mean(resid)) / (n * sf * sr)
        return 2.0 * corr * dcorr


class PrecautionarySavings(Restriction):
    """#12: Precautionary savings motive.
    Higher uncertainty → higher savings → lower expected returns.
    """
    def __init__(self):
        super().__init__('precautionary_savings', 'consumption', 'A',
                         'Precautionary savings restriction')

    def penalty(self, f_hat, X, data_context):
        # Use consumption growth volatility as uncertainty proxy
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        # Rolling vol of consumption growth (approximate with squared deviation)
        cg_sq = (cg - np.mean(cg)) ** 2
        # Higher uncertainty should predict higher returns (risk premium)
        corr = np.corrcoef(f_hat, cg_sq)[0, 1] if np.std(cg_sq) > 0 else 0
        return max(0, -corr) ** 2  # penalize negative correlation

    def penalty_gradient(self, f_hat, X, data_context):
        cg = data_context.get('cons_growth', np.zeros_like(f_hat))
        cg_sq = (cg - np.mean(cg)) ** 2
        n = len(f_hat)
        corr = np.corrcoef(f_hat, cg_sq)[0, 1] if np.std(cg_sq) > 0 else 0
        if corr >= 0:
            return np.zeros(n)
        sf = np.std(f_hat, ddof=0)
        sc = np.std(cg_sq, ddof=0)
        if sf == 0 or sc == 0:
            return np.zeros(n)
        dcorr = (cg_sq - np.mean(cg_sq)) / (n * sf * sc)
        return -2.0 * corr * dcorr


class CayPredictability(Restriction):
    """#13: Lettau-Ludvigson cay predictability.
    cay predicts excess returns (consumption-wealth ratio).
    """
    def __init__(self):
        super().__init__('cay_predictability', 'consumption', 'A',
                         'cay consumption-wealth ratio predictability')

    def penalty(self, f_hat, X, data_context):
        cay = data_context.get('cay', np.zeros_like(f_hat))
        if np.std(cay) == 0:
            return 0.0
        # cay should positively predict returns
        corr = np.corrcoef(f_hat, cay)[0, 1]
        return max(0, -corr) ** 2  # penalize negative correlation

    def penalty_gradient(self, f_hat, X, data_context):
        cay = data_context.get('cay', np.zeros_like(f_hat))
        n = len(f_hat)
        if np.std(cay) == 0:
            return np.zeros(n)
        corr = np.corrcoef(f_hat, cay)[0, 1]
        if corr >= 0:
            return np.zeros(n)
        sf = np.std(f_hat, ddof=0)
        sc = np.std(cay, ddof=0)
        if sf == 0 or sc == 0:
            return np.zeros(n)
        dcorr = (cay - np.mean(cay)) / (n * sf * sc)
        return -2.0 * corr * dcorr


def register_consumption_restrictions(registry: RestrictionRegistry):
    """Register all 13 consumption restrictions."""
    restrictions = [
        EulerCAPM(),
        EulerHabit(),
        EulerLRR(),
        EulerEZCAPM(),
        ConsGrowthMonotonicity(),
        EulerConditionalCAPM(),
        EulerDurableNondurable(),
        ConsumptionBeta(),
        RecursiveUtilityEuler(),
        DisasterRiskEuler(),
        IntertemporalSubstitution(),
        PrecautionarySavings(),
        CayPredictability(),
    ]
    for r in restrictions:
        registry.register(r)
