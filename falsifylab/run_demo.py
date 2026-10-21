"""Logged observe -> stress -> restricted revision -> frozen independent audit."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .artifacts import write_json, provenance
from .decisions import drift_decision, DEMONSTRATION_THRESHOLD, REFUTED, SURVIVES, INCONCLUSIVE
from .experiments import ExperimentLog, OscillatorObserver
from .hypothesis import fit_hypothesis
from .physics import simulate

THRESHOLD = DEMONSTRATION_THRESHOLD
CASES = [
    ('harmonic_undamped_control', dict(omega=2.0, alpha=0.0, gamma=0.0), False),
    ('duffing_nonlinearity', dict(omega=2.0, alpha=1.0, gamma=0.0), True),
    ('weakly_damped_negative_control', dict(omega=2.0, alpha=0.0, gamma=0.008), True),
]


def make_observer(params, log, seed, noise_sd, solver):
    # Coefficients are confined to this environment adapter. Search/fitting only
    # receive an observation callable and observed state arrays.
    streams = {part: np.random.default_rng(np.random.SeedSequence([seed, 310, i]))
               for i, part in enumerate(('discovery', 'probe', 'revision', 'holdout'))}
    def observe(*, amplitude, initial_velocity=0.0, horizon, steps, partition):
        knobs = dict(amplitude=float(amplitude), initial_velocity=float(initial_velocity),
                     horizon=float(horizon), steps=int(steps), noise_sd_x_m=noise_sd,
                     noise_sd_v_m_s=noise_sd, **solver)
        return log.acquire(partition, knobs, lambda: simulate(amplitude=amplitude,
            initial_velocity=initial_velocity, horizon=horizon, steps=steps, **params, **solver),
            kind='oscillator', noise_sd=noise_sd, rng=streams[partition])
    return observe


def make_initial_observations(observe: OscillatorObserver):
    return [observe(amplitude=a, initial_velocity=v, horizon=0.8, steps=121, partition='discovery')
            for a, v in [(0.12, 0.0), (0.20, 0.06), (0.27, -0.04)]]


def find_counterexample(law, observe: OscillatorObserver, *, noise_sd=0.0, horizon_scale=1.0):
    catalog = [(a, duration * horizon_scale) for a in (0.2, 0.5, 0.9, 1.3, 1.7)
               for duration in (2.0, 6.0, 12.0)]
    scored = []
    for a, duration in catalog:
        tr = observe(amplitude=a, initial_velocity=0.0, horizon=duration, steps=401, partition='probe')
        decision = drift_decision(law, tr, noise_sd=noise_sd)
        scored.append(dict(amplitude=a, horizon=duration, **decision))
    counterexamples = [s for s in scored if s['status'] == REFUTED]
    best = max(counterexamples or scored, key=lambda s: s['relative_drift'] or -1)
    boundaries = []
    for duration in sorted({s['horizon'] for s in scored}):
        line = [s for s in scored if s['horizon'] == duration]
        failures = [s['amplitude'] for s in line if s['status'] == REFUTED]
        passes = [s['amplitude'] for s in line if s['status'] == SURVIVES]
        lower = max([a for a in passes if not failures or a < min(failures)], default=None)
        upper = min(failures, default=None)
        nonmonotone = bool(passes and failures and max(passes) > min(failures))
        boundaries.append({'horizon_s': duration, 'last_observed_pass_m': lower,
                           'first_observed_failure_m': upper, 'nonmonotone': nonmonotone,
                           'interpretation': 'finite grid only; no guaranteed continuous validity region'})
    return {'max_probe_drift': best['relative_drift'], 'amplitude': best['amplitude'],
            'horizon': best['horizon'], 'probes': len(scored), 'observations': scored,
            'counterexamples': counterexamples, 'validity_grid': boundaries,
            'selection_policy': 'predeclared exhaustive 5-amplitude by 3-horizon catalog; select largest refuted drift'}


def combine(decisions):
    statuses = [d['status'] for d in decisions]
    return REFUTED if REFUTED in statuses else INCONCLUSIVE if INCONCLUSIVE in statuses else SURVIVES


def run_case(label, params, revise, *, seed=2026, noise_sd=0.0, horizon_scale=1.0,
             solver=None, raw_path: Path | None = None):
    solver = solver or {'rtol': 2e-11, 'atol': 1e-13}
    log = ExperimentLog()
    observe = make_observer(params, log, seed, noise_sd, solver)
    initial = make_initial_observations(observe)
    quadratic = fit_hypothesis(initial, 2)
    training = [drift_decision(quadratic, tr, noise_sd=noise_sd) for tr in initial]
    probe = find_counterexample(quadratic, observe, noise_sd=noise_sd, horizon_scale=horizon_scale)
    revised = None
    revision_error = None
    if revise and probe['counterexamples']:
        explanatory = observe(amplitude=probe['amplitude'], initial_velocity=0.0,
                              horizon=probe['horizon'], steps=501, partition='revision')
        try:
            revised = fit_hypothesis(initial + [explanatory], 4)
        except (ValueError, RuntimeError) as error:
            revision_error = str(error)
    # Scientific ablation: the richer family can also be fitted on discovery
    # alone. It can succeed without any stress query on this noise-free toy.
    try:
        no_search = fit_hypothesis(initial, 4)
    except ValueError:
        no_search = None
    frozen = {'initial': {'quadratic': quadratic.quadratic, 'quartic': quadratic.quartic},
              'revised': None if revised is None else {'quadratic': revised.quadratic, 'quartic': revised.quartic},
              'no_search_quartic': None if no_search is None else {'quadratic': no_search.quadratic, 'quartic': no_search.quartic}}
    log.freeze(frozen)
    # V3 protocol is fixed before running any final evaluation. The original
    # amplitude=1.39/horizon=10.7 data are explicitly development data.
    design = np.random.default_rng(np.random.SeedSequence([seed, 17391]))
    audits, trajectories = [], []
    for a, v, horizon, steps in [(1.463, .239, 9.73, 641), (1.613, -.173, 11.57, 733), (1.243, .359, 8.13, 569)]:
        a += float(design.uniform(-0.025, 0.025))
        tr = observe(amplitude=a, initial_velocity=v, horizon=horizon * horizon_scale,
                     steps=steps, partition='holdout')
        trajectories.append(tr)
        audits.append({'experiment_id': log.experiments[-1]['id'],
                       'initial': drift_decision(quadratic, tr, noise_sd=noise_sd),
                       'revised': None if revised is None else drift_decision(revised, tr, noise_sd=noise_sd),
                       'no_search_quartic': None if no_search is None else drift_decision(no_search, tr, noise_sd=noise_sd)})
    result = {'system': label, 'system_version': 'synthetic-oscillator-v3', 'seed': seed,
              'measurement_noise_sd': noise_sd, 'horizon_scale': horizon_scale,
              'units': {'time': 's', 'x': 'm', 'v': 'm/s', 'Q': 'm^2/s^2',
                        'quadratic_coefficient': 's^-2', 'quartic_coefficient': 'm^-2 s^-2'},
              'initial_hypothesis': quadratic.expression, 'frozen_models': frozen,
              'initial_fit': quadratic.diagnostics,
              'initial_training_relative_drift': max(d['relative_drift'] for d in training),
              'training_decisions': training, 'stress_search': probe,
              'heldout_initial_relative_drift': audits[0]['initial']['relative_drift'],
              'initial_hypothesis_stress_verdict': combine([a['initial'] for a in audits]),
              'heldout_independent_of_search': True, 'audit_protocol': 'v3-fresh-final',
              'audit_threshold': THRESHOLD, 'holdout_observations': audits,
              'revision_fit': None if revised is None else revised.diagnostics,
              'revision_failure': revision_error,
              'ablations': {'no_revision': combine([a['initial'] for a in audits]),
                            'no_counterexample_search_quartic': INCONCLUSIVE if no_search is None else combine([a['no_search_quartic'] for a in audits]),
                            'no_search_fit_uses_discovery_only': True,
                            'no_search_pre_audit_simulator_calls': 3,
                            'full_pre_audit_simulator_calls': len(log.experiments) - 3},
              'trace': log.manifest(),
              'evaluator_only_environment': params}
    if revised is not None:
        result.update(revised_hypothesis=revised.expression,
                      revised_heldout_relative_drift=audits[0]['revised']['relative_drift'],
                      revised_verdict=combine([a['revised'] for a in audits]))
    if raw_path is not None:
        log.save(raw_path)
        result['raw_artifact'] = raw_path.name
    return result, trajectories[0], quadratic, revised


def make_plot(holdout, quadratic, revised, output_dir):
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    for law, label in [(quadratic, 'Initial quadratic'), (revised, 'Constrained quartic revision')]:
        if law is not None:
            q = law.evaluate(holdout)
            ax.plot(holdout.time, (q - q[0]) / abs(q[0]), label=label, lw=2)
    ax.axhline(0, color='gray', ls='--', lw=.7)
    ax.set(xlabel='Time (s, nominal)', ylabel='Change in Q / |Q(0)| (dimensionless)',
           title='Independent Duffing audit: a limited repair of a failed invariant')
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / 'duffing_counterexample.png', dpi=175)
    plt.close(fig)


def execute(out: Path, seed=2026):
    out.mkdir(parents=True, exist_ok=True)
    payload = {'project': 'FalsifyLab', 'protocol_version': '3.0.0', 'software': provenance(),
               'threshold_warning': '2% drift is heuristic, NOT a statistical significance test', 'cases': []}
    for label, params, revise in CASES:
        result, holdout, law, revised = run_case(label, params, revise, seed=seed, raw_path=out / f'{label}_raw.npz')
        payload['cases'].append(result)
        print(f"{label}: initial={result['initial_hypothesis_stress_verdict']}; "
              f"heldout drift={result['heldout_initial_relative_drift']:.6%}; "
              f"revised={result.get('revised_verdict', 'NOT_ATTEMPTED')}")
        if label == 'duffing_nonlinearity':
            make_plot(holdout, law, revised, out)
    write_json(out / 'results.json', payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('outputs'))
    parser.add_argument('--seed', type=int, default=2026)
    args = parser.parse_args()
    execute(args.output, args.seed)
    print(f'Saved results to {args.output}/results.json')

if __name__ == '__main__':
    main()
