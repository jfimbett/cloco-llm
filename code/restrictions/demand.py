"""
Type D: Demand-system restrictions (#38-43).

Based on Koijen-Yogo (2019) demand-system asset pricing,
Gabaix-Koijen-Richmond-Yogo (2024) asset embeddings,
and market clearing conditions.
"""
import numpy as np
from .base import Restriction, RestrictionRegistry


class MarketClearing(Restriction):
    """#38: Market clearing condition.
    Value-weighted average expected excess return should be close to
    the equity premium implied by aggregate risk.
    """
    def __init__(self, target_premium: float = 0.005):
        super().__init__('market_clearing', 'demand', 'D',
                         'Market clearing: VW expected return ≈ equity premium')
        self.target_premium = target_premium  # monthly equity premium

    def penalty(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        if me is None:
            vw_mean = np.mean(f_hat)
        else:
            mask = np.isfinite(me) & np.isfinite(f_hat)
            if mask.sum() < 10:
                return 0.0
            w = me[mask] / me[mask].sum()
            vw_mean = np.dot(w, f_hat[mask])
        return (vw_mean - self.target_premium) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        n = len(f_hat)
        me = data_context.get('me', None)
        if me is None:
            vw_mean = np.mean(f_hat)
            w = np.ones(n) / n
            return 2.0 * (vw_mean - self.target_premium) * w
        mask = np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        w = np.zeros(n)
        w[mask] = me[mask] / me[mask].sum()
        vw_mean = np.dot(w, f_hat)
        return 2.0 * (vw_mean - self.target_premium) * w

    def is_quadratic(self):
        return False


class DemandElasticity(Restriction):
    """#39: Koijen-Yogo demand elasticity.
    Demand curves slope down: higher price → lower demand → lower expected return.
    """
    def __init__(self):
        super().__init__('demand_elasticity', 'demand', 'D',
                         'Koijen-Yogo demand elasticity restriction')

    def penalty(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        bm = data_context.get('bm', None)
        if me is None or bm is None:
            return 0.0
        mask = np.isfinite(me) & np.isfinite(bm) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        price_ratio = np.log(np.maximum(me[mask], 1e-6)) - np.log(np.maximum(bm[mask], 1e-6))
        if np.std(price_ratio) == 0:
            return 0.0
        corr = np.corrcoef(f_hat[mask], price_ratio)[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        bm = data_context.get('bm', None)
        n = len(f_hat)
        if me is None or bm is None:
            return np.zeros(n)
        mask = np.isfinite(me) & np.isfinite(bm) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return np.zeros(n)
        price_ratio = np.log(np.maximum(me[mask], 1e-6)) - np.log(np.maximum(bm[mask], 1e-6))
        sp = np.std(price_ratio)
        if sp == 0:
            return np.zeros(n)
        corr = np.corrcoef(f_hat[mask], price_ratio)[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        if sf == 0:
            return grad
        nm = mask.sum()
        dcorr = (price_ratio - np.mean(price_ratio)) / (nm * sf * sp)
        grad[mask] = 2.0 * corr * dcorr
        return grad

    def is_quadratic(self):
        return False


class InelasticMarkets(Restriction):
    """#40: Gabaix-Koijen inelastic markets hypothesis.
    Market-level flows → disproportionate price impact → return predictability.
    """
    def __init__(self, multiplier: float = 5.0):
        super().__init__('inelastic_markets', 'demand', 'D',
                         'Gabaix-Koijen inelastic markets')
        self.multiplier = multiplier

    def penalty(self, f_hat, X, data_context):
        mktrf = data_context.get('mktrf', None)
        if mktrf is None:
            return 0.0
        mask = np.isfinite(mktrf) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        pred_var = np.var(f_hat[mask])
        mkt_var = np.var(mktrf[mask])
        if mkt_var == 0:
            return 0.0
        vol_ratio = pred_var / mkt_var
        return max(0, 1.0 - vol_ratio) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        mktrf = data_context.get('mktrf', None)
        n = len(f_hat)
        if mktrf is None:
            return np.zeros(n)
        mask = np.isfinite(mktrf) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        pred_var = np.var(f_hat[mask])
        mkt_var = np.var(mktrf[mask])
        if mkt_var == 0:
            return np.zeros(n)
        vol_ratio = pred_var / mkt_var
        if vol_ratio >= 1.0:
            return np.zeros(n)
        grad = np.zeros(n)
        nm = mask.sum()
        # d(vol_ratio)/d(f_i) = 2(f_i - mean(f))/nm / mkt_var
        d_vr = 2.0 * (f_hat[mask] - np.mean(f_hat[mask])) / (nm * mkt_var)
        # d(penalty)/d(f_i) = -2(1-vr) * d_vr
        grad[mask] = -2.0 * (1.0 - vol_ratio) * d_vr
        return grad

    def is_quadratic(self):
        return False


class AssetEmbeddingConsistency(Restriction):
    """#41: Gabaix et al. (2024) asset embeddings.
    Similar assets (by characteristics) should have similar expected returns.
    """
    def __init__(self):
        super().__init__('asset_embedding', 'demand', 'D',
                         'Asset embedding consistency (similar assets → similar returns)')

    def penalty(self, f_hat, X, data_context):
        if X.shape[0] < 10:
            return 0.0
        # Smoothness penalty: ||∇f||² ≈ Σ_ij w_ij (f_i - f_j)²
        # where w_ij = exp(-||x_i - x_j||² / (2h²))
        n = min(X.shape[0], 200)  # subsample for speed
        idx = np.random.choice(X.shape[0], n, replace=False)
        X_sub = X[idx]
        f_sub = f_hat[idx]

        # Pairwise distances
        from scipy.spatial.distance import cdist
        dists = cdist(X_sub, X_sub, 'sqeuclidean')
        h = np.median(np.sqrt(dists[np.triu_indices(n, k=1)]))
        if h == 0:
            h = 1.0
        W = np.exp(-dists / (2 * h ** 2))
        np.fill_diagonal(W, 0)

        # Smoothness: Σ w_ij (f_i - f_j)²
        diff = f_sub[:, None] - f_sub[None, :]
        smoothness = np.sum(W * diff ** 2) / (2 * n)
        # Normalize by variance of f
        var_f = np.var(f_sub)
        if var_f == 0:
            return 0.0
        return smoothness / var_f

    def penalty_gradient(self, f_hat, X, data_context):
        # Smoothness penalty gradient: d/df_i [Σ w_ij (f_i - f_j)²]
        # = 2 Σ_j w_ij (f_i - f_j) = 2 (D_i f_i - Σ_j w_ij f_j) where D_i = Σ_j w_ij
        # This is the graph Laplacian: grad = 2 * L @ f / n, where L = D - W
        n = len(f_hat)
        if X.shape[0] < 10:
            return np.zeros(n)
        var_f = np.var(f_hat)
        if var_f == 0:
            return np.zeros(n)
        ns = min(X.shape[0], 200)
        idx = np.random.choice(X.shape[0], ns, replace=False)
        X_sub = X[idx]
        f_sub = f_hat[idx]
        from scipy.spatial.distance import cdist
        dists = cdist(X_sub, X_sub, 'sqeuclidean')
        h = np.median(np.sqrt(dists[np.triu_indices(ns, k=1)]))
        if h == 0:
            h = 1.0
        W = np.exp(-dists / (2 * h ** 2))
        np.fill_diagonal(W, 0)
        D = np.diag(W.sum(axis=1))
        L = D - W
        grad_sub = 2.0 * L @ f_sub / ns
        # Map back to full gradient
        grad = np.zeros(n)
        grad[idx] = grad_sub / var_f
        return grad

    def is_quadratic(self):
        return False


class SubstitutionPattern(Restriction):
    """#42: Asset substitution patterns.
    Close substitutes should have similar expected returns (no-arbitrage).
    """
    def __init__(self):
        super().__init__('substitution_pattern', 'demand', 'D',
                         'Asset substitution pattern consistency')

    def penalty(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        bm = data_context.get('bm', None)
        if me is None or bm is None:
            return 0.0
        mask = np.isfinite(me) & np.isfinite(bm) & np.isfinite(f_hat)
        if mask.sum() < 20:
            return 0.0
        me_rank = np.argsort(np.argsort(me[mask])) / mask.sum()
        bm_rank = np.argsort(np.argsort(bm[mask])) / mask.sum()

        within_var = 0.0
        count = 0
        for i_me in range(5):
            for i_bm in range(5):
                group_mask = (
                    (me_rank >= i_me / 5) & (me_rank < (i_me + 1) / 5)
                    & (bm_rank >= i_bm / 5) & (bm_rank < (i_bm + 1) / 5)
                )
                if group_mask.sum() > 1:
                    within_var += np.var(f_hat[mask][group_mask])
                    count += 1
        if count == 0:
            return 0.0
        within_var /= count
        total_var = np.var(f_hat[mask])
        if total_var == 0:
            return 0.0
        return within_var / total_var

    def penalty_gradient(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        bm = data_context.get('bm', None)
        n = len(f_hat)
        if me is None or bm is None:
            return np.zeros(n)
        mask = np.isfinite(me) & np.isfinite(bm) & np.isfinite(f_hat)
        nm = mask.sum()
        if nm < 20:
            return np.zeros(n)
        me_rank = np.argsort(np.argsort(me[mask])) / nm
        bm_rank = np.argsort(np.argsort(bm[mask])) / nm
        total_var = np.var(f_hat[mask])
        if total_var == 0:
            return np.zeros(n)

        # d(within_var)/d(f_i) = 2(f_i - group_mean) / (n_group * count)
        grad_masked = np.zeros(nm)
        count = 0
        for i_me in range(5):
            for i_bm in range(5):
                gm = (
                    (me_rank >= i_me / 5) & (me_rank < (i_me + 1) / 5)
                    & (bm_rank >= i_bm / 5) & (bm_rank < (i_bm + 1) / 5)
                )
                ng = gm.sum()
                if ng > 1:
                    count += 1
                    gmean = np.mean(f_hat[mask][gm])
                    grad_masked[gm] += 2.0 * (f_hat[mask][gm] - gmean) / ng

        if count == 0:
            return np.zeros(n)
        grad_masked /= count
        # d(penalty)/d(f) = d(wv/tv)/d(f) ≈ grad_wv/tv (ignoring d(tv)/d(f) for simplicity)
        grad = np.zeros(n)
        grad[mask] = grad_masked / total_var
        return grad

    def is_quadratic(self):
        return False


class SizeEffectDemand(Restriction):
    """#43: Demand-based size effect.
    Small stocks have inelastic demand → higher expected returns.
    """
    def __init__(self):
        super().__init__('size_demand', 'demand', 'D',
                         'Demand-based size effect')

    def penalty(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        if me is None:
            return 0.0
        mask = np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return 0.0
        # Negative relationship: smaller → higher returns
        log_me = np.log(np.maximum(me[mask], 1e-6))
        corr = np.corrcoef(f_hat[mask], log_me)[0, 1]
        return max(0, corr) ** 2

    def penalty_gradient(self, f_hat, X, data_context):
        me = data_context.get('me', None)
        n = len(f_hat)
        if me is None:
            return np.zeros(n)
        mask = np.isfinite(me) & np.isfinite(f_hat)
        if mask.sum() < 10:
            return np.zeros(n)
        log_me = np.log(np.maximum(me[mask], 1e-6))
        corr = np.corrcoef(f_hat[mask], log_me)[0, 1]
        if corr <= 0:
            return np.zeros(n)
        grad = np.zeros(n)
        sf = np.std(f_hat[mask])
        sm = np.std(log_me)
        if sf == 0 or sm == 0:
            return grad
        nm = mask.sum()
        grad[mask] = 2.0 * corr * (log_me - np.mean(log_me)) / (nm * sf * sm)
        return grad

    def is_quadratic(self):
        return False


def register_demand_restrictions(registry: RestrictionRegistry):
    """Register all 6 demand restrictions."""
    restrictions = [
        MarketClearing(),
        DemandElasticity(),
        InelasticMarkets(),
        AssetEmbeddingConsistency(),
        SubstitutionPattern(),
        SizeEffectDemand(),
    ]
    for r in restrictions:
        registry.register(r)
