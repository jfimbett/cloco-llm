"""
Abstract Restriction base class and registry for structural penalties.

Each restriction implements a penalty C_j(f) that measures how much
a return prediction function f violates a structural economic restriction.
"""
import numpy as np
from abc import ABC, abstractmethod
from collections import defaultdict


class Restriction(ABC):
    """
    Abstract base class for structural restrictions.

    Subclasses implement penalty(), penalty_gradient(), and optionally
    penalty_hessian() for quadratic approximation.
    """

    def __init__(self, name: str, family: str, penalty_type: str, description: str = ''):
        """
        Parameters
        ----------
        name : unique identifier (e.g., 'euler_capm')
        family : restriction family ('consumption', 'production', etc.)
        penalty_type : 'A' (Euler), 'B' (production FOC),
                       'D' (demand equilibrium)
        description : human-readable description
        """
        self.name = name
        self.family = family
        self.penalty_type = penalty_type
        self.description = description

    @abstractmethod
    def penalty(
        self,
        f_hat: np.ndarray,
        X: np.ndarray,
        data_context: dict,
    ) -> float:
        """
        Compute the penalty C_j(f̂).

        Parameters
        ----------
        f_hat : (n,) predicted excess returns
        X : (n, p) feature matrix
        data_context : dict with keys like 'cons_growth', 'rf', 'mktrf', etc.
                       Each value is (n,) array aligned with f_hat.

        Returns
        -------
        penalty : non-negative scalar
        """
        ...

    @abstractmethod
    def penalty_gradient(
        self,
        f_hat: np.ndarray,
        X: np.ndarray,
        data_context: dict,
    ) -> np.ndarray:
        """
        Gradient of C_j w.r.t. f̂ (vector of length n).

        For quadratic penalties: ∂C_j/∂f̂ = 2 * H_j @ f̂ + linear term
        For non-quadratic: numerical or analytical gradient
        """
        ...

    def penalty_hessian(
        self,
        f_hat: np.ndarray,
        X: np.ndarray,
        data_context: dict,
    ) -> np.ndarray:
        """
        Hessian of C_j w.r.t. f̂ (n × n matrix).

        Only needed for quadratic approximation of non-quadratic penalties.
        Default: numerical approximation via finite differences on gradient.
        """
        n = len(f_hat)
        eps = 1e-6
        H = np.zeros((n, n))
        g0 = self.penalty_gradient(f_hat, X, data_context)
        for i in range(n):
            f_plus = f_hat.copy()
            f_plus[i] += eps
            g_plus = self.penalty_gradient(f_plus, X, data_context)
            H[:, i] = (g_plus - g0) / eps
        # Symmetrize
        return 0.5 * (H + H.T)

    def is_quadratic(self) -> bool:
        """Whether this penalty is quadratic in f̂ (can be solved in closed form)."""
        return self.penalty_type in ('A', 'B')

    def __repr__(self):
        return f"Restriction('{self.name}', family='{self.family}', type='{self.penalty_type}')"


class RestrictionRegistry:
    """Registry of all structural restrictions, queryable by family/type."""

    def __init__(self):
        self._restrictions: dict[str, Restriction] = {}
        self._by_family: dict[str, list[str]] = defaultdict(list)
        self._by_type: dict[str, list[str]] = defaultdict(list)

    def register(self, restriction: Restriction):
        """Add a restriction to the registry."""
        name = restriction.name
        if name in self._restrictions:
            raise ValueError(f"Restriction '{name}' already registered")
        self._restrictions[name] = restriction
        self._by_family[restriction.family].append(name)
        self._by_type[restriction.penalty_type].append(name)

    def get(self, name: str) -> Restriction:
        return self._restrictions[name]

    def get_family(self, family: str) -> list[Restriction]:
        return [self._restrictions[n] for n in self._by_family.get(family, [])]

    def get_type(self, ptype: str) -> list[Restriction]:
        return [self._restrictions[n] for n in self._by_type.get(ptype, [])]

    def all(self) -> list[Restriction]:
        return list(self._restrictions.values())

    def families(self) -> list[str]:
        return list(self._by_family.keys())

    def __len__(self):
        return len(self._restrictions)

    def __repr__(self):
        return f"RestrictionRegistry({len(self)} restrictions, families={self.families()})"

