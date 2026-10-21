"""Constrained invariants fitted only from observations, with failure guards."""
from dataclasses import dataclass, field
import numpy as np
from .physics import Trajectory


@dataclass(frozen=True)
class Hypothesis:
    quadratic: float
    quartic: float = 0.0
    diagnostics: dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if not np.all(np.isfinite([self.quadratic, self.quartic])) or self.quadratic <= 0:
            raise ValueError('Finite coefficients and positive quadratic stiffness required')

    @property
    def expression(self) -> str:
        if abs(self.quartic) < 1e-8:
            return f'Q = v^2 + {self.quadratic:.6f} x^2'
        return f'Q = v^2 + {self.quadratic:.6f} x^2 + {self.quartic:.6f} x^4'

    def evaluate(self, tr: Trajectory) -> np.ndarray:
        return tr.v**2 + self.quadratic * tr.x**2 + self.quartic * tr.x**4


def fit_hypothesis(trajectories: list[Trajectory], degree: int) -> Hypothesis:
    if degree not in (2, 4) or not trajectories:
        raise ValueError('Use degree 2 or 4 with nonempty observations')
    matrices, targets = [], []
    for tr in trajectories:
        if np.ptp(tr.x) <= 1e-10 or np.ptp(tr.v) <= 1e-10:
            raise ValueError('No excitation: stationary/zero trajectories cannot identify an invariant')
        X = np.column_stack([tr.x**2] + ([tr.x**4] if degree == 4 else []))
        y = tr.v**2
        matrices.append(X - X.mean(axis=0, keepdims=True))
        targets.append(-(y - y.mean()))
    X, y = np.vstack(matrices), np.concatenate(targets)
    scales = np.linalg.norm(X, axis=0)
    if np.any(scales <= 1e-12) or np.linalg.matrix_rank(X) < X.shape[1]:
        raise ValueError('Not enough excitation to identify hypothesis')
    condition = float(np.linalg.cond(X / scales))
    if not np.isfinite(condition) or condition > 1e8:
        raise ValueError('Ill-conditioned hypothesis design')
    coefficients, *_ = np.linalg.lstsq(X, y, rcond=None)
    residual = X @ coefficients - y
    info = {'degree': degree, 'scaled_condition_number': condition,
            'fit_rmse_m2_s2': float(np.sqrt(np.mean(residual**2))),
            'samples': len(y), 'normalization': 'coefficient of v^2 fixed to 1; center within each trajectory'}
    return Hypothesis(float(coefficients[0]), float(coefficients[1]) if degree == 4 else 0.0, info)


def relative_drift(hypothesis: Hypothesis, tr: Trajectory) -> float:
    """Peak-to-peak / mean(abs(Q)); finite-sample heuristic, not a p-value."""
    if np.ptp(tr.x) <= 1e-10 or np.ptp(tr.v) <= 1e-10:
        raise ValueError('Degenerate trajectory: constant expressions are not evidence')
    values = hypothesis.evaluate(tr)
    denominator = float(np.mean(np.abs(values)))
    if not np.all(np.isfinite(values)) or denominator <= 1e-12:
        raise ValueError('Nonfinite or vanishing invariant')
    return float(np.ptp(values) / denominator)
