"""Synthetic continuous bilinear constitutive environment and observation-only fits."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import numpy as np
from scipy.optimize import least_squares


class MaterialObserver(Protocol):
    def __call__(self, strain, rng: np.random.Generator, replicates: int, partition: str) -> np.ndarray: ...


@dataclass(frozen=True)
class MaterialSimulator:
    elastic_modulus_mpa: float = 210_000.0
    yield_strain: float = 0.002
    hardening_modulus_mpa: float = 1_500.0
    noise_sd_mpa: float = 0.8

    def __post_init__(self):
        if not np.all(np.isfinite([self.elastic_modulus_mpa, self.yield_strain, self.hardening_modulus_mpa, self.noise_sd_mpa])):
            raise ValueError('Finite material parameters required')
        if self.elastic_modulus_mpa <= 0 or not 0 < self.yield_strain <= .03 or not 0 <= self.hardening_modulus_mpa <= self.elastic_modulus_mpa or self.noise_sd_mpa < 0:
            raise ValueError('Invalid elastic/plastic parameters or noise')

    def noiseless_stress(self, strain):
        e = np.asarray(strain, float)
        if not np.all(np.isfinite(e)) or np.any((e < 0) | (e > .03)):
            raise ValueError('Finite dimensionless strain in [0, .03] required')
        return self.elastic_modulus_mpa * np.minimum(e, self.yield_strain) + self.hardening_modulus_mpa * np.maximum(e - self.yield_strain, 0.0)

    def observe(self, strain, rng, replicates=4):
        if not isinstance(replicates, int) or replicates < 1:
            raise ValueError('Positive integer replicates required')
        e = np.atleast_1d(np.asarray(strain, float))
        if e.ndim != 1:
            raise ValueError('One-dimensional strain required')
        return self.noiseless_stress(e)[:, None] + rng.normal(0, self.noise_sd_mpa, (len(e), replicates))


def _paired(strain, stress):
    x, y = np.asarray(strain, float), np.asarray(stress, float)
    if x.ndim != 1 or y.ndim not in (1, 2) or len(x) != len(y) or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError('Finite paired strain/stress arrays required')
    if np.any(x < 0) or len(x) < 2 or np.ptp(x) < 1e-8:
        raise ValueError('Insufficient strain excitation')
    return x, y


def fit_hooke(strain, stress_mpa) -> float:
    x, y = _paired(strain, stress_mpa)
    if y.ndim == 2:
        x, y = np.repeat(x, y.shape[1]), y.reshape(-1)
    if x @ x < 1e-12:
        raise ValueError('Insufficient strain signal')
    slope = float((x @ y) / (x @ x))
    if not np.isfinite(slope) or slope <= 0:
        raise ValueError('Unphysical or unstable elastic slope')
    return slope


def hooke_uncertainty(strain, readings, slope, noise_sd):
    x = np.repeat(np.asarray(strain), readings.shape[1])
    residuals = readings.reshape(-1) - slope * x
    sd = max(float(noise_sd), float(np.sqrt(np.sum(residuals**2) / max(len(x) - 1, 1))))
    return sd / float(np.sqrt(x @ x))


def fit_bilinear(strain, stress_mpa, elastic_modulus_mpa):
    x, y = _paired(strain, stress_mpa)
    if y.ndim != 1 or len(x) < 4 or not np.isfinite(elastic_modulus_mpa) or elastic_modulus_mpa <= 0:
        raise ValueError('At least four paired means and positive modulus required')
    if np.max(np.abs(y - elastic_modulus_mpa * x)) < 1e-6:
        raise ValueError('No identifiable change point in a linear response')
    def residual(params):
        ey, hardening = params
        return predict_bilinear(x, elastic_modulus_mpa, ey, hardening) - y
    best = None
    for q in (.15, .35, .55, .75):
        for h in (0.0, .15 * elastic_modulus_mpa, .5 * elastic_modulus_mpa):
            fit = least_squares(residual, [float(np.quantile(x, q)), h],
                bounds=([1e-6, 0.0], [max(float(np.max(x)) * 1.001, 1e-5), elastic_modulus_mpa]), max_nfev=3000)
            if fit.success and (best is None or np.sum(fit.fun**2) < np.sum(best.fun**2)):
                best = fit
    if best is None:
        raise RuntimeError('Bilinear fit failed on every start')
    norms = np.linalg.norm(best.jac, axis=0)
    if np.any(norms < 1e-10) or np.linalg.cond(best.jac / norms) > 1e8:
        raise ValueError('Unidentifiable/ill-conditioned bilinear fit')
    if np.count_nonzero(x > best.x[0]) < 2 or np.count_nonzero(x < best.x[0]) < 1:
        raise ValueError('Insufficient observations on both sides of change point')
    return float(best.x[0]), float(best.x[1])


def predict_bilinear(strain, elastic_modulus_mpa, yield_strain, hardening_modulus_mpa):
    e = np.asarray(strain, float)
    parameters = [elastic_modulus_mpa, yield_strain, hardening_modulus_mpa]
    if not np.all(np.isfinite(e)) or not np.all(np.isfinite(parameters)) or elastic_modulus_mpa <= 0 or yield_strain <= 0 or not 0 <= hardening_modulus_mpa <= elastic_modulus_mpa:
        raise ValueError('Finite, physically constrained bilinear model required')
    return elastic_modulus_mpa * np.minimum(e, yield_strain) + hardening_modulus_mpa * np.maximum(e - yield_strain, 0.0)
