"""Synthetic laboratory for x'' = -omega² x - alpha x³ - gamma x'.

SI units are nominal: x in m, time in s, v in m/s; no measured apparatus.
Generating coefficients stay in the laboratory, never in hypothesis fitting.
"""
from dataclasses import dataclass, field
import numpy as np
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class Trajectory:
    time: np.ndarray
    x: np.ndarray
    v: np.ndarray
    units: tuple[str, str, str] = ('s', 'm', 'm/s')
    solver: dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        arrays = [np.asarray(value, dtype=float) for value in (self.time, self.x, self.v)]
        if any(a.ndim != 1 for a in arrays) or len({len(a) for a in arrays}) != 1 or len(arrays[0]) < 4:
            raise ValueError('Expected paired one-dimensional time/x/v arrays of length >= 4')
        if any(not np.all(np.isfinite(a)) for a in arrays) or np.any(np.diff(arrays[0]) <= 0):
            raise ValueError('Trajectory must be finite and time strictly increasing')
        if self.units != ('s', 'm', 'm/s'):
            raise ValueError('Incompatible units: convert to s, m, m/s before fitting')
        for name, value in zip(('time', 'x', 'v'), arrays):
            object.__setattr__(self, name, value)


def simulate(*, amplitude: float, initial_velocity: float = 0.0,
             omega: float = 2.0, alpha: float = 0.0, gamma: float = 0.0,
             horizon: float = 8.0, steps: int = 501,
             rtol: float = 2e-11, atol: float = 1e-13) -> Trajectory:
    values = [amplitude, initial_velocity, omega, alpha, gamma, horizon, rtol, atol]
    if not np.all(np.isfinite(values)) or horizon <= 0 or omega <= 0 or not isinstance(steps, int) or steps < 4:
        raise ValueError('Finite parameters, positive horizon/omega, integer steps >= 4 required')
    if not 1e-14 <= rtol < 1 or not 0 < atol < 1 or gamma < 0:
        raise ValueError('Invalid tolerances or negative damping')

    def dynamics(_t, state):
        x, v = state
        return [v, -(omega * omega) * x - alpha * x**3 - gamma * v]

    times = np.linspace(0.0, horizon, steps)
    solution = solve_ivp(dynamics, [0.0, horizon], [amplitude, initial_velocity],
                         t_eval=times, method='DOP853', rtol=rtol, atol=atol)
    if not solution.success or solution.y.shape != (2, steps):
        raise RuntimeError(solution.message)
    return Trajectory(times, solution.y[0], solution.y[1], solver={
        'method': 'DOP853', 'rtol': rtol, 'atol': atol, 'nfev': int(solution.nfev)})
