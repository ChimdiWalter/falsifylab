"""Exploration helpers for the marimo notebook. They call the unchanged engine.

Nothing here alters thresholds, budgets, families or the frozen v3 protocol.
Results are exploratory reruns, not new untouched evaluation data.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from falsifylab.materials import MaterialSimulator
from falsifylab.run_materials import run as material_run, MIN_EPS, MAX_EPS, TOLERANCE_MPA, POLICIES
from falsifylab.run_demo import CASES, run_case

MATERIAL_PRESETS = {
    'Benchmark surrogate (E 210 GPa)': dict(elastic_modulus_mpa=210_000.0, yield_strain=.002, hardening_modulus_mpa=1_500.0),
    'Softer hypothetical alloy (E 70 GPa)': dict(elastic_modulus_mpa=70_000.0, yield_strain=.0045, hardening_modulus_mpa=3_000.0),
    'Hidden softening dip (breaks monotonicity)': dict(elastic_modulus_mpa=210_000.0, yield_strain=.002, hardening_modulus_mpa=1_500.0, dip=True),
}
SYSTEMS = {label: (params, revise) for label, params, revise in CASES}


@dataclass(frozen=True)
class DippedMaterial(MaterialSimulator):
    """Bilinear material with a localized 25 MPa pre-yield softening dip at strain .0012-.0016."""
    def noiseless_stress(self, strain):
        e = np.asarray(strain, float)
        return super().noiseless_stress(e) - 25.0 * np.clip(1 - np.abs(e - .0014) / .0002, 0, None)


def make_material(preset: str, noise_sd: float) -> MaterialSimulator:
    params = dict(MATERIAL_PRESETS[preset])
    cls = DippedMaterial if params.pop('dip', False) else MaterialSimulator
    return cls(noise_sd_mpa=float(noise_sd), **params)


def first_exceedance(sim: MaterialSimulator, slope: float) -> float | None:
    """Evaluator-only: first strain in [MIN_EPS, MAX_EPS] where the noiseless error exceeds 10 MPa."""
    grid = np.linspace(MIN_EPS, MAX_EPS, 130_001)
    above = np.abs(sim.noiseless_stress(grid) - slope * grid) > TOLERANCE_MPA
    return float(grid[np.argmax(above)]) if above.any() else None


def explore_material(preset: str, noise_sd: float, seed: int) -> dict:
    sim = make_material(preset, noise_sd)
    record = material_run(int(seed), noise_sd=float(noise_sd), simulator=sim)
    onset = first_exceedance(sim, record['fitted_elastic_modulus_mpa'])
    rows = []
    for name in POLICIES:
        s = record['strategies'][name]
        interval = s['boundary_interval']
        covered = None if interval is None or onset is None else interval[0] <= onset <= interval[1]
        rows.append({'policy': name, 'probes': s['probes'], 'readings': s['measurements'],
                     'bracket_low_strain': None if interval is None else interval[0],
                     'bracket_high_strain': None if interval is None else interval[1],
                     'boundary_status': s['boundary_status'],
                     'revision': record['revision_fits'][name]['status'],
                     'audit_mae_mpa': record['heldout_revised_mae_by_policy_mpa'][name],
                     'audit_status': record['heldout_revised_decisions'][name]['status'],
                     'evaluator_covers_first_exceedance': covered,
                     'silent_miss': bool(covered is False and s['boundary_status'] != 'INCONCLUSIVE')})
    return {'record': record, 'simulator': sim, 'first_exceedance': onset, 'policies': rows,
            'readings_total': sum(c['measurements'] for c in record['trace']['costs'].values())}


def explore_oscillator(system: str, noise_sd: float, horizon_scale: float, seed: int) -> dict:
    params, revise = SYSTEMS[system]
    result, audit_trajectory, quadratic, revised = run_case(system, params, revise, seed=int(seed),
                                                            noise_sd=float(noise_sd), horizon_scale=float(horizon_scale))
    return {'result': result, 'audit_trajectory': audit_trajectory, 'quadratic': quadratic, 'revised': revised,
            'costs': result['trace']['costs']}
