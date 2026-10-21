"""Versioned inspectable evidence traces. Never mathematical/statistical proofs."""
from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import numpy as np
from jsonschema import Draft202012Validator, FormatChecker
from .artifacts import digest, fingerprint, write_json
from .decisions import REFUTED, SURVIVES, INCONCLUSIVE

SCHEMA_VERSION = '1.0.0'
SCHEMA_PATH = Path(__file__).with_name('schema.json')


@dataclass
class EvidenceCertificate:
    run_id: str
    schema_version: str
    created_at_utc: str
    seed: int
    software: dict
    physical_system: dict
    candidate: dict
    validity_domain: dict
    partition_manifest: dict
    experiment_queue: list
    resource_costs: dict
    selection_policy: dict
    counterexamples: list
    revision: dict
    final_holdout: dict
    metrics: dict
    status: str
    numerical_sensitivity: dict
    artifacts: list
    limitations: list
    reproduce: str
    record_type: str = 'reproducible_experiment_provenance_NOT_formal_proof'


def artifact(path, certificate_path, kind):
    return {'path': os.path.relpath(path, certificate_path.parent), 'sha256': digest(path),
            'bytes': path.stat().st_size, 'kind': kind}


def validate(doc, *, certificate_path=None, artifact_root=None):
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(doc)
    queue = doc['experiment_queue']
    ids = [e['id'] for e in queue]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate experiment IDs')
    partitions = doc['partition_manifest']['partitions']
    flat = [i for values in partitions.values() for i in values]
    if len(flat) != len(set(flat)) or set(flat) != set(ids):
        raise ValueError('Partition overlap or missing experiments')
    for name, values in partitions.items():
        if set(values) != {e['id'] for e in queue if e['partition'] == name}:
            raise ValueError('Partition manifest disagrees with queue')
    freeze = doc['partition_manifest']['model_freeze']
    if freeze['fingerprint'] != fingerprint(freeze['models']):
        raise ValueError('Frozen model fingerprint mismatch')
    holdouts = [i for i, e in enumerate(queue) if e['partition'] == 'holdout']
    if not holdouts or min(holdouts) < freeze['after_experiment']:
        raise ValueError('Holdout acquired before model freeze')
    if any(e['partition'] != 'holdout' for e in queue[min(holdouts):]):
        raise ValueError('Search or fitting acquisition after holdout')
    for partition, costs in doc['resource_costs'].items():
        for metric, total in costs.items():
            if total != sum(e[metric] for e in queue if e['partition'] == partition):
                raise ValueError('Resource-cost mismatch')
    models = freeze['models']
    if doc['physical_system']['name'] == 'synthetic_bilinear_material':
        if doc['candidate']['coefficients']['elastic_modulus_mpa'] != models['initial_modulus_mpa'] or doc['revision']['fit'] != models['revisions']['active']:
            raise ValueError('Certificate candidate/revision differs from frozen models')
    else:
        if doc['candidate']['coefficients'] != models['initial'] or doc['revision']['coefficients'] != models['revised']:
            raise ValueError('Certificate candidate/revision differs from frozen models')
    if certificate_path is not None:
        root = (artifact_root or certificate_path.parent.parent).resolve()
        raw_files = []
        for source in doc['artifacts']:
            path = (certificate_path.parent / source['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f'Missing artifact or path outside allowed root: {source["path"]}')
            if digest(path) != source['sha256'] or path.stat().st_size != source['bytes']:
                raise ValueError(f'Artifact checksum/size mismatch: {source["path"]}')
            if source['kind'] == 'results':
                payload = json.loads(path.read_text())
                if 'cases' in payload:
                    record = next(r for r in payload['cases'] if r['system'] == doc['physical_system']['name'] and r['seed'] == doc['seed'])
                    if doc['final_holdout']['decisions'] != record['holdout_observations'] or doc['status'] != record['initial_hypothesis_stress_verdict']:
                        raise ValueError('Certificate audit disagrees with source evidence')
                    metric_pairs = [('initial_holdout_relative_drift','heldout_initial_relative_drift'),
                                    ('revised_holdout_relative_drift','revised_heldout_relative_drift')]
                else:
                    record = next(r for r in payload['records'] if r['seed'] == doc['seed'])
                    if doc['final_holdout'] != record['holdout'] or doc['status'] != record['heldout_initial_decision']['status']:
                        raise ValueError('Certificate audit disagrees with source evidence')
                    metric_pairs = [('initial_holdout_mae_mpa','heldout_linear_mae_mpa'),
                                    ('revised_holdout_mae_mpa','heldout_revised_mae_mpa')]
                for reported, stored in metric_pairs:
                    if doc['metrics'].get(reported) != record.get(stored):
                        raise ValueError('Certificate metric disagrees with source evidence')
            if source['kind'] == 'raw_measurements':
                raw_files.append(path)
        if not raw_files:
            raise ValueError('A certificate must contain real raw measurements')
        available = {}
        for path in raw_files:
            with np.load(path, allow_pickle=False) as data:
                for key in data.files:
                    if not np.all(np.isfinite(data[key])):
                        raise ValueError('Nonfinite stored data')
                    available[key] = data[key]
        for event in queue:
            if event['status'] == 'COMPLETED':
                if not set(event['raw_keys']).issubset(available):
                    raise ValueError('Experiment refers to missing raw arrays')
                if event['kind'] == 'oscillator':
                    count = available[event['id'] + '_x'].size + available[event['id'] + '_v'].size
                else:
                    count = available[event['id'] + '_stress_mpa'].size
                if count != event['measurements']:
                    raise ValueError('Raw data measurement-count mismatch')
    return doc


def build(record, result_file, raw_file, output_path, software, *, materials=False, sensitivity=None):
    trace = record['trace']
    if materials:
        candidate = {'expression': f"stress = {record['fitted_elastic_modulus_mpa']:.9g} * strain",
                     'coefficients': {'elastic_modulus_mpa': record['fitted_elastic_modulus_mpa']},
                     'variable_units': record['units']}
        counterexamples = [o for o in record['strategies']['active']['observations'] if o['status'] == REFUTED]
        revision = {'family': 'predeclared continuous bilinear', 'fit': record['revision_fits']['active'],
                    'frozen_before_holdout': True, 'fit_inputs': trace['partitions']['probe_active']}
        initial_mae, revised_mae = record['heldout_linear_mae_mpa'], record['heldout_revised_mae_mpa']
        # Compare aggregate MAE only to an explicit engineering tolerance, with
        # a conservative noise allowance. Not an inferential test.
        allowance = record['heldout_initial_decision']['uncertainty_allowance_mpa']
        revised_status = record['heldout_revised_decisions']['active']['status']
        status = record['heldout_initial_decision']['status']
        revision['heldout_status'] = revised_status
        validity = {'discovery_strain': [.0002, .0008], 'probed_strain': [.001, .014],
                    'operational_tolerance_mpa': record['tolerance_mpa'],
                    'empirical_boundary': record['strategies']['active']['boundary_interval'],
                    'uncertainty': record['strategies']['active']['uncertainty_aware_observed_interval'],
                    'boundary_status': record['strategies']['active']['boundary_status'],
                    'interpretation': 'observed error-tolerance boundary, not physical yield or a confidence interval'}
        policy = {'name': 'adaptive bisection; equal-budget uniform/random controls',
                  'assumptions': [record['strategies']['active']['assumption']],
                  'query_budget_per_policy': 10, 'replicates_per_query': 4,
                  'rng_streams': 'SeedSequence namespaces: 1729 observation, 4793 random selection; per-role independent'}
        metrics = {'initial_holdout_mae_mpa': initial_mae, 'revised_holdout_mae_mpa': revised_mae,
                   'all_policies': record['strategies'], 'mae_uncertainty_allowance_mpa': float(allowance),
                   'threshold_kind': 'DEMONSTRATION_THRESHOLD'}
        holdout = record['holdout']
        limitations = ['One synthetic bilinear material; no real alloy measurements',
                       'Preselected revision family; monotonic deviation assumption',
                       'Empirical bracket need not cover noiseless onset; narrowness alone is not accuracy',
                       'Instrument and slope uncertainty are heuristic, not calibrated sequential error control',
                       'Revised audit status tests aggregate MAE against 10 MPa, not a pointwise error guarantee']
        system = {'name': 'synthetic_bilinear_material', 'version': record['system_version']}
        reproduce = 'python -m falsifylab.run_materials --seeds 30 --out outputs/materials'
    else:
        candidate = {'expression': record['initial_hypothesis'], 'coefficients': record['frozen_models']['initial'],
                     'variable_units': record['units']}
        counterexamples = record['stress_search']['counterexamples']
        revision = {'family': 'v^2 + a*x^2 + b*x^4', 'fit': record['revision_fit'],
                    'coefficients': record['frozen_models']['revised'],
                    'expression': record.get('revised_hypothesis'),
                    'heldout_status': record.get('revised_verdict', INCONCLUSIVE),
                    'failure': record['revision_failure'], 'fit_inputs': trace['partitions'].get('revision', []),
                    'frozen_before_holdout': True}
        status = record['initial_hypothesis_stress_verdict']
        validity = {'discovery_amplitudes_m': [.12, .20, .27], 'discovery_horizon_s': .8,
                    'sampled_grid': record['stress_search']['validity_grid'],
                    'uncertainty': {'noise_sd_x_m_and_v_m_s': record['measurement_noise_sd'],
                                    'interpretation': 'uncalibrated propagation allowance'},
                    'warning': 'finite grid cannot establish a continuous validity region'}
        policy = {'name': record['stress_search']['selection_policy'], 'assumptions': [], 'query_budget': 15}
        holdout = {'decisions': record['holdout_observations'], 'raw_ids': trace['partitions']['holdout'],
                   'protocol': record['audit_protocol']}
        metrics = {'training_drift': record['initial_training_relative_drift'],
                   'initial_holdout_relative_drift': record['heldout_initial_relative_drift'],
                   'revised_holdout_relative_drift': record.get('revised_heldout_relative_drift'),
                   'threshold': record['audit_threshold'], 'threshold_kind': 'DEMONSTRATION_THRESHOLD',
                   'ablations': record['ablations']}
        limitations = ['Synthetic textbook mechanics with nominal SI units',
                       'Hand-specified degree-2/4 family and exhaustive fixed search',
                       'Peak-to-peak drift depends on sample count, noise and horizon',
                       '2% threshold and uncertainty allowances have no statistical error guarantee',
                       'A discovery-only quartic fit can succeed without stress search in a noiseless correctly specified problem']
        system = {'name': record['system'], 'version': record['system_version']}
        reproduce = 'python -m falsifylab.run_demo'
    doc = asdict(EvidenceCertificate(
        run_id=fingerprint({'raw_sha256': digest(raw_file), 'candidate': candidate, 'system': system})[:24],
        schema_version=SCHEMA_VERSION, created_at_utc=datetime.now(timezone.utc).isoformat(),
        seed=record['seed'], software=software, physical_system=system, candidate=candidate,
        validity_domain=validity, partition_manifest={k: trace[k] for k in ('partitions', 'model_freeze', 'holdout_policy')},
        experiment_queue=trace['experiment_queue'], resource_costs=trace['costs'], selection_policy=policy,
        counterexamples=counterexamples, revision=revision, final_holdout=holdout, metrics=metrics,
        status=status, numerical_sensitivity=sensitivity or {'status': 'NOT_RUN_IN_THIS_COMMAND',
            'reproduce': 'python -m falsifylab.benchmark --seeds 30'},
        artifacts=[artifact(result_file, output_path, 'results'), artifact(raw_file, output_path, 'raw_measurements')],
        limitations=limitations, reproduce=reproduce))
    return doc


def write_certificate(doc, path, *, artifact_root):
    validate(doc, certificate_path=path, artifact_root=artifact_root)
    write_json(path, doc)
    lines = [f"# Evidence trace: {doc['physical_system']['name']}", '',
             f"Run `{doc['run_id']}` · schema {SCHEMA_VERSION} · seed {doc['seed']}", '',
             '**This record is not a formal mathematical or statistical proof.**', '',
             f"Candidate: `{doc['candidate']['expression']}`", '', f"Initial audit status: **{doc['status']}**", '',
             f"Revised audit status: **{doc['revision']['heldout_status']}**", '',
             f"Observed counterexamples: {len(doc['counterexamples'])}. All readings are stored and hashed.", '',
             'First observed counterexample:', '', '```json',
             json.dumps(doc['counterexamples'][:1], indent=2), '```', '',
             'Constrained revision:', '', '```json', json.dumps(doc['revision'], indent=2), '```', '',
             'Resource costs by partition:', '', '| Partition | Simulator calls | Scalar readings | RHS evaluations |',
             '|---|---:|---:|---:|']
    lines += [f"| {p} | {c['simulator_calls']} | {c['measurements']} | {c['rhs_evaluations']} |"
              for p, c in doc['resource_costs'].items()]
    lines += ['', 'Validity and uncertainty:', '', '```json', json.dumps(doc['validity_domain'], indent=2), '```', '',
              'Metrics:', '', '```json', json.dumps({k:v for k,v in doc['metrics'].items() if k != 'all_policies'}, indent=2), '```', '',
              'Limitations:', ''] + ['- ' + item for item in doc['limitations']]
    lines += ['', 'Reproduce:', '', f"`{doc['reproduce']}`", '']
    path.with_suffix('.md').write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Validate certificate schemas, partitions, costs and artifact checksums')
    parser.add_argument('certificates', type=Path, nargs='+')
    parser.add_argument('--artifact-root', type=Path)
    args = parser.parse_args()
    for path in args.certificates:
        doc = validate(json.loads(path.read_text()), certificate_path=path, artifact_root=args.artifact_root)
        print(f"VALID {path}: {doc['run_id']} ({doc['status']})")

if __name__ == '__main__':
    main()
