"""Recompute saved evidence metrics from raw measurements and frozen models."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from .artifacts import digest, fingerprint
from .certificates import validate
from .decisions import drift_decision
from .hypothesis import Hypothesis, relative_drift
from .physics import Trajectory
from .materials import predict_bilinear


def close(actual, expected):
    if actual is None or expected is None:
        if actual != expected:
            raise ValueError('Missing metric mismatch')
    elif not np.isclose(actual, expected, rtol=1e-10, atol=1e-12):
        raise ValueError(f'Recomputed metric differs: {actual} vs {expected}')


def verify_oscillator(record, raw_path):
    with np.load(raw_path, allow_pickle=False) as data:
        models = record['frozen_models']
        if fingerprint(models) != record['trace']['model_freeze']['fingerprint']:
            raise ValueError('Frozen oscillator model mismatch')
        probe_ids = record['trace']['partitions']['probe']
        initial = Hypothesis(**models['initial'])
        for key, saved in zip(probe_ids, record['stress_search']['observations']):
            tr = Trajectory(data[key + '_time'], data[key + '_x'], data[key + '_v'])
            decision = drift_decision(initial, tr, noise_sd=record['measurement_noise_sd'])
            close(decision['relative_drift'], saved['relative_drift'])
            if decision['status'] != saved['status']:
                raise ValueError('Saved probe verdict differs from raw data')
        for audit in record['holdout_observations']:
            key = audit['experiment_id']
            tr = Trajectory(data[key + '_time'], data[key + '_x'], data[key + '_v'])
            for name, model in models.items():
                if model is None:
                    continue
                decision = drift_decision(Hypothesis(**model), tr, noise_sd=record['measurement_noise_sd'])
                saved = audit[name]
                close(decision['relative_drift'], saved['relative_drift'])
                if decision['status'] != saved['status']:
                    raise ValueError('Saved oscillator verdict differs from raw data')


def verify_material(record, raw_path):
    freeze = record['trace']['model_freeze']
    models = {'initial_modulus_mpa': record['fitted_elastic_modulus_mpa'], 'revisions': record['revision_fits']}
    if fingerprint(models) != freeze['fingerprint']:
        raise ValueError('Frozen material model mismatch')
    key = record['trace']['partitions']['holdout'][0]
    with np.load(raw_path, allow_pickle=False) as data:
        x, y = data[key + '_strain'], data[key + '_stress_mpa'].mean(axis=1)
        E = record['fitted_elastic_modulus_mpa']
        for name, strategy in record['strategies'].items():
            ids = record['trace']['partitions']['probe_' + name]
            for event_id, observation in zip(ids, strategy['observations']):
                raw = data[event_id + '_stress_mpa'][0]
                if raw.tolist() != observation['stress_readings_mpa']:
                    raise ValueError('Probe raw readings differ from saved observations')
                close(float(raw.mean()), observation['mean_stress_mpa'])
                close(abs(float(raw.mean())-E*observation['strain']), observation['absolute_deviation_mpa'])
        close(float(np.mean(np.abs(E*x-y))), record['heldout_linear_mae_mpa'])
        for name, fit in record['revision_fits'].items():
            if fit['status'] == 'FITTED':
                pred = predict_bilinear(x, E, fit['yield_strain'], fit['hardening_modulus_mpa'])
                close(float(np.mean(np.abs(pred-y))), record['heldout_revised_mae_by_policy_mpa'][name])


def verify(root: Path):
    count = 0
    for path in sorted((root / 'certificates').glob('*.json')):
        validate(json.loads(path.read_text()), certificate_path=path, artifact_root=root)
        count += 1
    if not count:
        raise ValueError('No certificates found')
    osc = json.loads((root / 'results.json').read_text())
    for record in osc['cases']:
        verify_oscillator(record, root / record['raw_artifact'])
    mat = json.loads((root / 'materials/results.json').read_text())
    for record in mat['records']:
        verify_material(record, root / 'materials' / record['raw_artifact'])
    benchmark_dir = root / 'benchmark'
    if (benchmark_dir / 'checksums.json').exists():
        for relative, checksum in json.loads((benchmark_dir / 'checksums.json').read_text()).items():
            path = (benchmark_dir / relative).resolve()
            if not path.is_relative_to(benchmark_dir.resolve()) or digest(path) != checksum:
                raise ValueError(f'Benchmark checksum mismatch: {relative}')
        for name in ('oscillator_records.json','robustness_oscillator_records.json','solver_records.json'):
            for record in json.loads((benchmark_dir / name).read_text()):
                verify_oscillator(record, benchmark_dir / record['raw_artifact'])
        for record in json.loads((benchmark_dir / 'robustness_materials_records.json').read_text()):
            verify_material(record, benchmark_dir / record['raw_artifact'])
        for record in json.loads((benchmark_dir / 'materials/results.json').read_text())['records']:
            verify_material(record, benchmark_dir / 'materials' / record['raw_artifact'])
    print(f'VERIFIED {count} certificates, all saved holdout metrics, raw-data checksums and frozen models')
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, nargs='?', default=Path('outputs'))
    args = parser.parse_args()
    verify(args.root)

if __name__ == '__main__':
    main()
