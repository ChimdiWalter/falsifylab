"""Post-hoc audit of failure modes found in the final adversarial review.

EXPLORATORY, NOT PART OF FROZEN PROTOCOL v3. Uses the unchanged engine.
  1. Valid harmonic control under instrument noise: how often is the true law refuted?
  2. Hidden softening dip: does the frozen bilinear revision pass the mean-error audit,
     and how large is its worst local error against the hidden truth?
  3. Miss decomposition of the post-hoc noise sweep in audit/independent_checks.json.

Usage: PYTHONPATH=. python audit/posthoc_controls.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from falsifylab.materials import predict_bilinear
from falsifylab.run_demo import CASES, run_case
from notebooks.exploration import explore_material

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'audit' / 'posthoc_controls.json'
SEEDS = range(2026, 2056)

params, revise = next((p, r) for label, p, r in CASES if label == 'harmonic_undamped_control')
harmonic = []
for noise in (0.001, 0.01):
    for horizon in (0.5, 1.0, 2.0):
        verdicts = {s: run_case('harmonic_undamped_control', params, revise, seed=s, noise_sd=noise, horizon_scale=horizon)[0]['initial_hypothesis_stress_verdict'] for s in SEEDS}
        row = {'noise_sd': noise, 'horizon_factor': horizon, 'n': len(verdicts),
               'refuted': sum(v == 'REFUTED' for v in verdicts.values()),
               'inconclusive': sum(v == 'INCONCLUSIVE' for v in verdicts.values()),
               'not_refuted': sum(v == 'NOT_REFUTED_UNDER_TESTED_CONDITIONS' for v in verdicts.values()),
               'refuted_seeds': [s for s, v in verdicts.items() if v == 'REFUTED']}
        harmonic.append(row)
        print('harmonic', row)

dip = []
grid = np.linspace(0.0, 0.014, 14001)
for seed in range(2026, 2036):
    out = explore_material('Hidden softening dip (breaks monotonicity)', 0.8, seed)
    rec, sim = out['record'], out['simulator']
    truth = sim.noiseless_stress(grid)
    for row in out['policies']:
        fit = rec['revision_fits'][row['policy']]
        worst = None
        if fit['status'] == 'FITTED':
            pred = predict_bilinear(grid, rec['fitted_elastic_modulus_mpa'], fit['yield_strain'], fit['hardening_modulus_mpa'])
            worst = float(np.max(np.abs(pred - truth)))
        dip.append({'seed': seed, 'policy': row['policy'], 'audit_mae_mpa': row['audit_mae_mpa'], 'audit_status': row['audit_status'],
                    'max_abs_error_vs_truth_mpa': worst})
dip_summary = {'runs': len(dip), 'audit_not_refuted': sum(d['audit_status'] == 'NOT_REFUTED_UNDER_TESTED_CONDITIONS' for d in dip),
               'audit_mae_range_mpa': [min(d['audit_mae_mpa'] for d in dip), max(d['audit_mae_mpa'] for d in dip)],
               'max_local_error_range_mpa': [min(d['max_abs_error_vs_truth_mpa'] for d in dip), max(d['max_abs_error_vs_truth_mpa'] for d in dip)]}
print('dip', dip_summary)

sweep = json.loads((ROOT / 'audit' / 'independent_checks.json').read_text())['posthoc_noise_sweep']['rows']
cells = []
for r in sweep:
    for p in ('active', 'uniform', 'random'):
        q = r[p]
        cells.append({'noise_sd_mpa': r['noise_sd_mpa'], 'policy': p, 'evaluable': q['evaluable_brackets'], 'missed': q['evaluable_brackets'] - q['covered'],
                      'flagged_inconclusive': q['boundary_inconclusive'], 'n': r['n']})
misses = sum(c['missed'] for c in cells)
miss_cells = [c for c in cells if c['missed']]
decomp = {'runs': sum(c['n'] for c in cells), 'runs_above_nominal_noise': sum(c['n'] for c in cells if c['noise_sd_mpa'] > 0.8),
          'evaluable_brackets': sum(c['evaluable'] for c in cells), 'missed': misses,
          'missed_reported_resolved': sum(c['missed'] for c in cells if c['flagged_inconclusive'] < c['n']),
          'all_misses_in_cells_with_full_abstention': all(c['flagged_inconclusive'] == c['n'] for c in miss_cells),
          'active_2mpa_abstained_while_covering': next(c for c in cells if c['noise_sd_mpa'] == 2.0 and c['policy'] == 'active')['flagged_inconclusive'],
          'cells': cells}
print('miss decomposition', {k: v for k, v in decomp.items() if k != 'cells'})
OUT.write_text(json.dumps({'label': 'EXPLORATORY POST-HOC AUDIT; not part of frozen protocol v3', 'harmonic_noise': harmonic,
                           'dip': {'summary': dip_summary, 'runs': dip}, 'miss_decomposition': decomp}, indent=2))
print('wrote', OUT.relative_to(ROOT))
