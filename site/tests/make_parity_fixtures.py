"""Export recorded Python runs as replay fixtures for the JS engine parity test.

Materials: every primary seed (0.8 MPa) plus the frozen robustness records at
0, 0.8, 8 and 80 MPa, with raw readings replayed in acquisition order.
Oscillator: the three noise-free seed-2026 cases with recorded audit amplitudes.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'outputs' / 'benchmark'


def material_case(rec, raw_path):
    with np.load(raw_path, allow_pickle=False) as raw:
        parts = rec['trace']['partitions']
        d, h = parts['discovery'][0], parts['holdout'][0]
        probes = {p: [raw[i + '_stress_mpa'][0].tolist() for i in parts['probe_' + p]] for p in ('active', 'uniform', 'random')}
        return {'seed': rec['seed'], 'noise_sd': rec['noise_sd_mpa'],
                'replay': {'discovery': raw[d + '_stress_mpa'].tolist(), 'probes': probes,
                           'randomLocations': [o['strain'] for o in rec['strategies']['random']['observations'][2:]],
                           'holdout': raw[h + '_stress_mpa'].tolist()},
                'expected': {'ehat': rec['fitted_elastic_modulus_mpa'], 'slope_se': rec['elastic_slope_standard_error_mpa'],
                             'initial_mae': rec['heldout_linear_mae_mpa'],
                             'strategies': {p: {'strains': [o['strain'] for o in s['observations']],
                                                'statuses': [o['status'] for o in s['observations']],
                                                'interval': s['boundary_interval'], 'boundary_status': s['boundary_status'],
                                                'uncertainty_interval': s['uncertainty_aware_observed_interval'],
                                                'nonmonotone': s['nonmonotone_observations']}
                                            for p, s in rec['strategies'].items()},
                             'fits': rec['revision_fits'], 'mae': rec['heldout_revised_mae_by_policy_mpa'],
                             'decisions': {p: d['status'] for p, d in rec['heldout_revised_decisions'].items()},
                             'initial_decision': rec['heldout_initial_decision']['status']}}


def main():
    primary = json.loads((BENCH / 'materials' / 'results.json').read_text())['records']
    cases = [material_case(r, BENCH / 'materials' / r['raw_artifact']) for r in primary]
    for r in json.loads((BENCH / 'robustness_materials_records.json').read_text()):
        cases.append(material_case(r, BENCH / r['raw_artifact']))
    osc = []
    for case in json.loads((ROOT / 'outputs' / 'results.json').read_text())['cases']:
        queue = {e['id']: e for e in case['trace']['experiment_queue']}
        osc.append({'system': case['system'], 'seed': case['seed'],
                    'audit_amplitudes': [queue[i]['knobs']['amplitude'] for i in case['trace']['partitions']['holdout']],
                    'frozen_models': case['frozen_models'],
                    'catalog': [{'drift': o['relative_drift'], 'status': o['status']} for o in case['stress_search']['observations']],
                    'selected': [case['stress_search']['amplitude'], case['stress_search']['horizon']],
                    'audits': [{k: None if a[k] is None else {'drift': a[k]['relative_drift'], 'status': a[k]['status']}
                                for k in ('initial', 'revised', 'no_search_quartic')} for a in case['holdout_observations']],
                    'initial_verdict': case['initial_hypothesis_stress_verdict'], 'revised_verdict': case.get('revised_verdict')})
    out = ROOT / 'site' / 'tests' / 'fixtures' / 'parity.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'materials': cases, 'oscillator': osc}))
    print(f'wrote {out.relative_to(ROOT)}: {len(cases)} material runs, {len(osc)} oscillator cases')


if __name__ == '__main__':
    main()
