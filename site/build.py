"""Build the static FalsifyLab workbench data bundle from committed evidence.

Every number the site shows as RECORDED comes from files under outputs/ or audit/.
The bundle lists each input file with its SHA-256 so a reader can check provenance.
Nothing here runs or modifies the scientific engine.

Usage: python site/build.py
"""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
OUT = ROOT / 'outputs'
used: dict[str, str] = {}


def load(rel: str):
    path = ROOT / rel
    used[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text()) if path.suffix == '.json' else np.load(path, allow_pickle=False)


def r(x, n=6):
    """Round floats for the bundle while keeping enough precision for display."""
    if x is None:
        return None
    return float(f'{float(x):.{n}g}')


def decimate(arr, n=360):
    arr = np.asarray(arr, float)
    idx = np.unique(np.linspace(0, len(arr) - 1, min(n, len(arr))).round().astype(int))
    return idx


def materials_bundle():
    res = load('outputs/benchmark/materials/results.json')
    rec = res['records'][0]
    raw = load('outputs/benchmark/materials/' + rec['raw_artifact'])
    parts = rec['trace']['partitions']
    d = parts['discovery'][0]
    discovery = {'strain': raw[d + '_strain'].tolist(), 'readings_mpa': np.round(raw[d + '_stress_mpa'], 4).tolist()}
    policies = {}
    for name, s in rec['strategies'].items():
        policies[name] = {
            'observations': [{'strain': o['strain'], 'readings_mpa': [round(v, 4) for v in o['stress_readings_mpa']],
                              'mean_mpa': round(o['mean_stress_mpa'], 4), 'deviation_mpa': round(o['absolute_deviation_mpa'], 4),
                              'allowance_mpa': round(o['uncertainty_allowance_mpa'], 4), 'status': o['status'],
                              'rejected': o['rejected']} for o in s['observations']],
            'interval': s['boundary_interval'], 'width': s['bracket_width'], 'boundary_status': s['boundary_status'],
            'uncertainty_interval': s['uncertainty_aware_observed_interval'], 'covered': s['reference_onset_covered_evaluator_only'],
            'nonmonotone': s['nonmonotone_observations'], 'fit': rec['revision_fits'][name],
            'audit_mae_mpa': rec['heldout_revised_mae_by_policy_mpa'][name],
            'audit_decision': rec['heldout_revised_decisions'][name]}
    seeds = []
    for x in res['records']:
        seeds.append({'seed': x['seed'], 'ehat': r(x['fitted_elastic_modulus_mpa'], 8), 'onset': r(x['reference_operational_onset_benchmark_only'], 8),
                      'linear_mae': r(x['heldout_linear_mae_mpa']),
                      **{p: {'width': r(x['strategies'][p]['bracket_width']), 'covered': x['strategies'][p]['reference_onset_covered_evaluator_only'],
                             'boundary_status': x['strategies'][p]['boundary_status'],
                             'interval': x['strategies'][p]['boundary_interval'],
                             'mae': r(x['heldout_revised_mae_by_policy_mpa'][p])} for p in ('active', 'uniform', 'random')}})
    return {'seed': rec['seed'], 'noise_sd_mpa': rec['noise_sd_mpa'], 'tolerance_mpa': rec['tolerance_mpa'],
            'ehat_mpa': rec['fitted_elastic_modulus_mpa'], 'slope_se_mpa': rec['elastic_slope_standard_error_mpa'],
            'discovery': discovery, 'policies': policies,
            'holdout': {'strain': rec['holdout']['strain'], 'mean_mpa': [round(v, 4) for v in rec['holdout']['stress_mean_mpa']], 'replicates': 3},
            'initial_audit_mae_mpa': rec['heldout_linear_mae_mpa'], 'initial_audit_decision': rec['heldout_initial_decision'],
            'evaluator_only': {**rec['evaluator_only_environment'], 'reference_onset': rec['reference_operational_onset_benchmark_only']},
            'costs': rec['trace']['costs'], 'aggregate': {k: v for k, v in res.items() if k not in ('records', 'software')},
            'per_seed': seeds}


def oscillator_bundle():
    res = load('outputs/results.json')
    cases = []
    for case in res['cases']:
        raw = load('outputs/' + case['raw_artifact'])
        parts = case['trace']['partitions']
        models = case['frozen_models']
        def traj(eid, n=360):
            t, x, v = raw[eid + '_time'], raw[eid + '_x'], raw[eid + '_v']
            i = decimate(t, n)
            out = {'t': np.round(t[i], 5).tolist(), 'x': np.round(x[i], 6).tolist(), 'v': np.round(v[i], 6).tolist()}
            for name in ('initial', 'revised', 'no_search_quartic'):
                m = models.get(name)
                if m:
                    q = v**2 + m['quadratic'] * x**2 + m['quartic'] * x**4
                    out['q_' + name] = [r(val, 10) for val in ((q - q[0]) / abs(q[0]))[i]]
            return out
        audits = []
        for eid, h in zip(parts['holdout'], case['holdout_observations']):
            audits.append({'id': eid, 'knobs': next(e['knobs'] for e in case['trace']['experiment_queue'] if e['id'] == eid),
                           'trajectory': traj(eid),
                           **{k: (None if h[k] is None else {'drift': h[k]['relative_drift'], 'status': h[k]['status']})
                              for k in ('initial', 'revised', 'no_search_quartic')}})
        cases.append({'system': case['system'], 'params_evaluator_only': case['evaluator_only_environment'],
                      'initial_expression': case['initial_hypothesis'], 'revised_expression': case.get('revised_hypothesis'),
                      'frozen_models': models, 'training_drift': case['initial_training_relative_drift'],
                      'discovery': [traj(e, 120) for e in parts['discovery']],
                      'catalog': [{'amplitude': o['amplitude'], 'horizon': o['horizon'], 'drift': o['relative_drift'], 'status': o['status']}
                                  for o in case['stress_search']['observations']],
                      'selected': {'amplitude': case['stress_search']['amplitude'], 'horizon': case['stress_search']['horizon'],
                                   'drift': case['stress_search']['max_probe_drift']},
                      'n_counterexamples': len(case['stress_search']['counterexamples']),
                      'initial_verdict': case['initial_hypothesis_stress_verdict'], 'revised_verdict': case.get('revised_verdict'),
                      'ablations': case['ablations'], 'audits': audits, 'costs': case['trace']['costs']})
    return {'seed': res['cases'][0]['seed'], 'threshold': res['cases'][0]['audit_threshold'], 'cases': cases}


def certificates_bundle():
    certs = {}
    for name in ('materials', 'oscillator', 'harmonic_undamped_control', 'weakly_damped_negative_control'):
        doc = load(f'outputs/certificates/{name}.json')
        certs[name] = doc
    return certs


def main():
    metrics = load('outputs/benchmark/metrics.json')
    checks = load('audit/independent_checks.json')
    excitation = load('audit/posthoc_oscillator_excitation.json')
    controls = load('audit/posthoc_controls.json')
    bundle = {
        'materials': materials_bundle(),
        'oscillator': oscillator_bundle(),
        'benchmark': {k: metrics[k] for k in ('protocol_version', 'seed_count', 'seed_ids', 'oscillator', 'robustness', 'solver_sensitivity', 'ablations', 'interpretation')},
        'certificates': certificates_bundle(),
        'posthoc_audit': {'label': 'Independent audit (post-hoc, exploratory; not part of frozen protocol v3)',
                         'checks': [{'name': c['name'], 'pass': c['pass']} for c in checks['checks']],
                         'noise_sweep': checks['posthoc_noise_sweep'], 'alternate_material': checks['alternate_material'],
                         'noise_floor': checks['materials_noise_floor'],
                         'hidden_nonmonotonicity': {p: {'misses': sum(x[p]['misses_first_onset'] for x in checks['hidden_nonmonotonicity']),
                                                        'silent': sum(x[p]['misses_first_onset'] and x[p]['silent'] for x in checks['hidden_nonmonotonicity'])}
                                                    for p in ('active', 'uniform', 'random')},
                         'hidden_nonmonotonicity_n': len(checks['hidden_nonmonotonicity']),
                         'oscillator_noise_tally': checks['oscillator_noise_ablation_tally'],
                         'excitation': excitation['summary'], 'excitation_label': excitation['label'],
                         'harmonic_noise': controls['harmonic_noise'], 'dip': controls['dip']['summary'],
                         'misses': {k: v for k, v in controls['miss_decomposition'].items() if k != 'cells'}},
    }
    logs = {}
    for key, rel in (('pytest', 'docs/logs/audit/pytest-final-branch.txt'), ('parity', 'docs/logs/audit/engine-parity.txt'),
                     ('verify', 'docs/logs/audit/verify-final.txt'), ('rerun', 'docs/logs/audit/benchmark-rerun-comparison.txt')):
        path = ROOT / rel
        if path.exists():
            lines = [line for line in path.read_text().splitlines() if line.strip() and not line.startswith(('real', 'user', 'sys', 'note:', 'worst'))]
            logs[key] = {'summary': lines[-1] if lines else '', 'path': rel}
    bundle['logs'] = logs
    head = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    bundle['provenance'] = {'built_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                            'site_build_commit': head or None,
                            'evidence_git_sha': bundle['certificates']['materials']['software'].get('git_sha'),
                            'inputs_sha256': dict(sorted(used.items()))}
    (SITE / 'data').mkdir(parents=True, exist_ok=True)
    text = json.dumps(bundle, separators=(',', ':'), allow_nan=False)
    (SITE / 'data' / 'evidence.js').write_text('window.FALSIFYLAB_EVIDENCE=' + text + ';\n')
    (SITE / 'data' / 'evidence.json').write_text(text)
    vendor = SITE / 'assets' / 'vendor' / 'plotly-3.5.0.min.js'
    if not vendor.exists():
        import plotly
        vendor.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(plotly.__file__).parent / 'package_data' / 'plotly.min.js', vendor)
    print(f'wrote site/data/evidence.js ({len(text) / 1024:.0f} KiB) from {len(used)} evidence files')


if __name__ == '__main__':
    main()
