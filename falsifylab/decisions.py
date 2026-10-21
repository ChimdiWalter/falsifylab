"""Conservative heuristic abstention. These bounds have no coverage guarantee."""
import numpy as np
from .hypothesis import relative_drift

REFUTED = 'REFUTED'
SURVIVES = 'NOT_REFUTED_UNDER_TESTED_CONDITIONS'
INCONCLUSIVE = 'INCONCLUSIVE'
DEMONSTRATION_THRESHOLD = 0.02


def drift_decision(law, trajectory, *, noise_sd: float = 0.0, threshold: float = DEMONSTRATION_THRESHOLD) -> dict:
    if not np.isfinite(noise_sd) or noise_sd < 0 or not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Finite nonnegative noise and positive threshold required')
    try:
        score = relative_drift(law, trajectory)
        q = law.evaluate(trajectory)
        # First-order instrument-noise propagation for x and v (same numeric SD,
        # different units). Six standard deviations plus second-order allowance.
        propagation = np.sqrt((2 * trajectory.v * noise_sd)**2 +
            ((2 * law.quadratic * trajectory.x + 4 * law.quartic * trajectory.x**3) * noise_sd)**2)
        bound = float((6 * np.max(propagation) + 12 * (1 + abs(law.quadratic)) * noise_sd**2) /
                      np.mean(np.abs(q)))
        if abs(score - threshold) <= bound:
            status = INCONCLUSIVE
        else:
            status = REFUTED if score > threshold else SURVIVES
        return {'relative_drift': score, 'uncertainty_allowance': bound, 'status': status,
                'threshold': threshold, 'threshold_kind': 'DEMONSTRATION_THRESHOLD',
                'uncertainty_kind': 'uncalibrated conservative instrument-noise heuristic'}
    except (ValueError, FloatingPointError) as error:
        return {'relative_drift': None, 'uncertainty_allowance': None, 'status': INCONCLUSIVE,
                'threshold': threshold, 'reason': str(error)}


def mae_decision(mae, noise_sd, *, replicates=3, tolerance=10.0):
    """Heuristic allowance on MAE against noisy replicate means, not a CI."""
    allowance = 3 * float(noise_sd) / np.sqrt(replicates)
    if mae is None or abs(mae - tolerance) <= allowance:
        status = INCONCLUSIVE
    else:
        status = REFUTED if mae > tolerance else SURVIVES
    return {'mae_mpa': mae, 'uncertainty_allowance_mpa': allowance, 'status': status,
            'threshold_mpa': tolerance, 'threshold_kind': 'DEMONSTRATION_THRESHOLD'}
