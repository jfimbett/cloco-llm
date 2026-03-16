# Structural restrictions for Theory-Informed KRR
from .base import Restriction, RestrictionRegistry, adaptive_weights
from .consumption import register_consumption_restrictions
from .production import register_production_restrictions
from .intermediary import register_intermediary_restrictions
from .information import register_information_restrictions
from .demand import register_demand_restrictions
from .volatility import register_volatility_restrictions
from .behavioral import register_behavioral_restrictions
from .macro import register_macro_restrictions


def build_all_restrictions() -> RestrictionRegistry:
    """Build and return a registry with all 56 restrictions."""
    registry = RestrictionRegistry()
    register_consumption_restrictions(registry)
    register_production_restrictions(registry)
    register_intermediary_restrictions(registry)
    register_information_restrictions(registry)
    register_demand_restrictions(registry)
    register_volatility_restrictions(registry)
    register_behavioral_restrictions(registry)
    register_macro_restrictions(registry)
    return registry
