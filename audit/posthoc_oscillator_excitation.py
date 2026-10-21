"""Post-hoc audit: does counterexample *selection* matter for the quartic revision?

EXPLORATORY, NOT PART OF FROZEN PROTOCOL v3. Uses the unchanged engine functions.
For each seed and instrument-noise level the quartic family is fitted on the
three discovery trajectories plus one extra 501-sample trajectory chosen by:
  none    - discovery only (the existing no-search ablation)
  search  - the catalog trajectory with the largest refuted drift (the engine's choice)
  random  - a uniformly random catalog condition (independent RNG namespace 9001)
  largest - the largest-amplitude, longest-horizon catalog condition (1.7 m, 12 s)
All variants are frozen before the same three v3-style final trajectories are acquired.

Usage: python audit/posthoc_oscillator_excitation.py [out_json]
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
from falsifylab.decisions import drift_decision, REFUTED, SURVIVES, INCONCLUSIVE
from falsifylab.experiments import ExperimentLog
from falsifylab.hypothesis import fit_hypothesis
from falsifylab.run_demo import make_observer, make_initial_observations, find_counterexample, combine

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('posthoc_oscillator_excitation.json')
PARAMS = dict(omega=2.0, alpha=1.0, gamma=0.0)
CATALOG = [(a, d) for a in (0.2, 0.5, 0.9, 1.3, 1.7) for d in (2.0, 6.0, 12.0)]
VARIANTS = ('none', 'search', 'random', 'largest')


def trial(seed, noise):
    log = ExperimentLog()
    observe = make_observer(PARAMS, log, seed, noise, {'rtol': 2e-11, 'atol': 1e-13})
    initial = make_initial_observations(observe)
    quadratic = fit_hypothesis(initial, 2)
    probe = find_counterexample(quadratic, observe, noise_sd=noise)
    pick = np.random.default_rng(np.random.SeedSequence([seed, 9001])).integers(len(CATALOG))
    extra = {'search': (probe['amplitude'], probe['horizon']) if probe['counterexamples'] else None,
             'random': CATALOG[pick], 'largest': (1.7, 12.0)}
    models = {}
    try:
        models['none'] = fit_hypothesis(initial, 4)
    except ValueError:
        models['none'] = None
    for name in ('search', 'random', 'largest'):
        if extra[name] is None:
            models[name] = None
            continue
        tr = observe(amplitude=extra[name][0], initial_velocity=0.0, horizon=extra[name][1], steps=501, partition='revision')
        try:
            models[name] = fit_hypothesis(initial + [tr], 4)
        except ValueError:
            models[name] = None
    log.freeze({k: None if m is None else [m.quadratic, m.quartic] for k, m in models.items()})
    design = np.random.default_rng(np.random.SeedSequence([seed, 17391]))
    audits = {k: [] for k in VARIANTS}
    for a, v, horizon, steps in [(1.463, .239, 9.73, 641), (1.613, -.173, 11.57, 733), (1.243, .359, 8.13, 569)]:
        a += float(design.uniform(-0.025, 0.025))
        tr = observe(amplitude=a, initial_velocity=v, horizon=horizon, steps=steps, partition='holdout')
        for k, m in models.items():
            audits[k].append({'status': INCONCLUSIVE} if m is None else drift_decision(m, tr, noise_sd=noise))
    return {'seed': seed, 'noise_sd': noise, 'extra_condition': {k: extra.get(k) for k in VARIANTS},
            'coefficients': {k: None if m is None else [m.quadratic, m.quartic] for k, m in models.items()},
            'verdict': {k: combine(audits[k]) for k in VARIANTS}}


rows = [trial(seed, noise) for noise in (0.001, 0.01) for seed in range(2026, 2056)]
summary = []
for noise in (0.001, 0.01):
    subset = [r for r in rows if r['noise_sd'] == noise]
    entry = {'noise_sd': noise, 'n': len(subset)}
    for k in VARIANTS:
        verdicts = [r['verdict'][k] for r in subset]
        quart = [r['coefficients'][k][1] for r in subset if r['coefficients'][k] is not None]
        entry[k] = {'REFUTED': verdicts.count(REFUTED), 'NOT_REFUTED': verdicts.count(SURVIVES),
                    'INCONCLUSIVE': verdicts.count(INCONCLUSIVE),
                    'quartic_coeff_median': float(np.median(quart)) if quart else None,
                    'quartic_coeff_iqr': [float(np.quantile(quart, .25)), float(np.quantile(quart, .75))] if quart else None}
    entry['search_selected_conditions'] = sorted({tuple(r['extra_condition']['search']) for r in subset if r['extra_condition']['search']})
    summary.append(entry)
    print(json.dumps(entry))
OUT.write_text(json.dumps({'label': 'EXPLORATORY POST-HOC AUDIT; not part of frozen protocol v3; true quartic coefficient alpha/2 = 0.5',
                           'summary': summary, 'rows': rows}, indent=2, default=float))
print('wrote', OUT.name)
