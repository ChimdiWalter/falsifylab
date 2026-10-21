"""Equal-budget operational-deviation search; all readings and costs retained."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from .artifacts import write_json, provenance
from .decisions import REFUTED, SURVIVES, INCONCLUSIVE, mae_decision
from .experiments import ExperimentLog
from .materials import MaterialSimulator, fit_hooke, hooke_uncertainty, fit_bilinear, predict_bilinear

MIN_EPS, MAX_EPS = .001, .014
BUDGET, REPLICATES, TOLERANCE_MPA = 10, 4, 10.0
POLICIES = ('active', 'uniform', 'random')


def search_boundary(observe, elastic_modulus, rng, strategy, *, selection_rng=None,
                    slope_se=0.0, noise_sd=.8):
    """Search sees only observations and public instrument uncertainty.

    Empirical mean classifications drive bisection. Uncertain branches are
    explicitly flagged, and a separate conservative observed bracket is saved.
    Neither interval has a statistical coverage guarantee.
    """
    if strategy not in POLICIES or not np.all(np.isfinite([elastic_modulus, slope_se, noise_sd])) or elastic_modulus <= 0 or min(slope_se, noise_sd) < 0:
        raise ValueError('Invalid strategy, slope or uncertainty')
    selection_rng = selection_rng or np.random.default_rng(0)
    observations = []
    def query(e):
        values = observe([e], rng, REPLICATES, 'probe_' + strategy)[0]
        mean = float(values.mean())
        deviation = abs(mean - elastic_modulus * e)
        sd = max(noise_sd, float(values.std(ddof=1)))
        allowance = 3 * float(np.hypot(sd / np.sqrt(REPLICATES), e * slope_se))
        nominal_failure = deviation > TOLERANCE_MPA
        status = REFUTED if deviation - allowance > TOLERANCE_MPA else SURVIVES if deviation + allowance <= TOLERANCE_MPA else INCONCLUSIVE
        observations.append({'strain': float(e), 'stress_readings_mpa': values.tolist(),
            'mean_stress_mpa': mean, 'absolute_deviation_mpa': deviation,
            'uncertainty_allowance_mpa': allowance, 'rejected': bool(nominal_failure), 'status': status})
        return nominal_failure
    lo_fail, hi_fail = query(MIN_EPS), query(MAX_EPS)
    bracket_ok = not lo_fail and hi_fail
    if strategy == 'active' and bracket_ok:
        lower, upper = MIN_EPS, MAX_EPS
        for _ in range(BUDGET - 2):
            middle = (lower + upper) / 2
            if query(middle):
                upper = middle
            else:
                lower = middle
    else:
        locations = (selection_rng.uniform(MIN_EPS, MAX_EPS, BUDGET - 2) if strategy == 'random'
                     else np.linspace(MIN_EPS, MAX_EPS, BUDGET)[1:-1])
        for e in locations:
            query(float(e))
    passes = [o['strain'] for o in observations if not o['rejected']]
    fails = [o['strain'] for o in observations if o['rejected']]
    nonmono = bool(passes and fails and max(passes) >= min(fails))
    valid = bracket_ok and passes and fails and not nonmono
    bounds = [max(passes), min(fails)] if valid else None
    certain_pass = [o['strain'] for o in observations if o['status'] == SURVIVES]
    certain_fail = [o['strain'] for o in observations if o['status'] == REFUTED]
    uncertainty_bounds = ([max(certain_pass), min(certain_fail)] if certain_pass and certain_fail
                          and max(certain_pass) < min(certain_fail) else None)
    uncertain = sum(o['status'] == INCONCLUSIVE for o in observations)
    return {'strategy': strategy, 'probes': len(observations), 'measurements': len(observations) * REPLICATES,
            'boundary_interval': bounds, 'bracket_width': bounds[1] - bounds[0] if bounds else None,
            'boundary_status': SURVIVES if valid and not uncertain else INCONCLUSIVE,
            'uncertainty_aware_observed_interval': uncertainty_bounds,
            'uncertain_probe_count': uncertain, 'initial_bracket_satisfied': bool(bracket_ok),
            'nonmonotone_observations': nonmono,
            'assumption': 'Absolute deviation has one pass-to-fail transition over the strain domain; unchecked between observations',
            'interval_kind': 'empirical operational bracket, not a confidence interval and not physical yield',
            'fallback': 'uniform remaining probes' if strategy == 'active' and not bracket_ok else None,
            'observations': observations}


def run(seed=2026, *, noise_sd=.8, raw_path: Path | None = None, simulator=None):
    sim = simulator or MaterialSimulator(noise_sd_mpa=noise_sd)
    log = ExperimentLog()
    streams = {name: np.random.default_rng(np.random.SeedSequence([seed, 1729, i]))
               for i, name in enumerate(('discovery', *POLICIES, 'holdout'))}
    def observe(strain, rng, replicates, partition):
        return log.acquire(partition, {'strain': list(map(float, strain)), 'replicates': replicates,
                'noise_sd_mpa': noise_sd}, lambda: sim.observe(strain, rng, replicates), kind='materials')
    strains = np.linspace(.0002, .0008, 8)
    readings = observe(strains, streams['discovery'], 5, 'discovery')
    ehat = fit_hooke(strains, readings)
    slope_se = hooke_uncertainty(strains, readings, ehat, noise_sd)
    strategies, fits = {}, {}
    for i, name in enumerate(POLICIES):
        strategy = search_boundary(observe, ehat, streams[name], name,
            selection_rng=np.random.default_rng(np.random.SeedSequence([seed, 4793, i])),
            slope_se=slope_se, noise_sd=noise_sd)
        strategies[name] = strategy
        x = np.array([o['strain'] for o in strategy['observations']])
        y = np.array([o['mean_stress_mpa'] for o in strategy['observations']])
        try:
            if not any(o['status'] == REFUTED for o in strategy['observations']):
                raise ValueError('No uncertainty-resolved counterexample: decline revision')
            ye, hardening = fit_bilinear(x, y, ehat)
            fitted = predict_bilinear(x, ehat, ye, hardening)
            fits[name] = {'yield_strain': ye, 'hardening_modulus_mpa': hardening,
                          'fit_rmse_mpa': float(np.sqrt(np.mean((fitted - y)**2))),
                          'fit_observations': len(x), 'status': 'FITTED',
                          'family': 'continuous bilinear with nonnegative hardening <= elastic slope'}
        except (ValueError, RuntimeError) as error:
            fits[name] = {'status': INCONCLUSIVE, 'reason': str(error)}
    # The no-search ablation retains the discovery-only linear law. A bilinear
    # change point is not identifiable from elastic-only discovery observations.
    log.freeze({'initial_modulus_mpa': ehat, 'revisions': fits})
    heldout_strain = np.linspace(.000161, MAX_EPS - .000219, 83)
    heldout_readings = observe(heldout_strain, streams['holdout'], 3, 'holdout')
    heldout = heldout_readings.mean(axis=1)
    initial_predictions = ehat * heldout_strain
    initial_mae = float(np.mean(np.abs(initial_predictions - heldout)))
    heldout_errors = {}
    for name, fit in fits.items():
        if fit['status'] == 'FITTED':
            prediction = predict_bilinear(heldout_strain, ehat, fit['yield_strain'], fit['hardening_modulus_mpa'])
            heldout_errors[name] = float(np.mean(np.abs(prediction - heldout)))
        else:
            heldout_errors[name] = None
    # EVALUATOR ONLY: compute noiseless crossing for the *fitted* initial law.
    # The former reference used true E, which is a different target when Ehat
    # varies. Coefficients below are never read by selection or fitting.
    reference_onset = None
    deviation = lambda e: abs(float(sim.noiseless_stress(e)) - ehat * e) - TOLERANCE_MPA
    if deviation(MIN_EPS) < 0 < deviation(MAX_EPS):
        reference_onset = float(brentq(deviation, MIN_EPS, MAX_EPS, xtol=1e-14))
    for s in strategies.values():
        bounds = s['boundary_interval']
        s['reference_onset_covered_evaluator_only'] = (None if bounds is None or reference_onset is None
                else bool(bounds[0] <= reference_onset <= bounds[1]))
    active_fit = fits['active']
    record = {'seed': seed, 'system_version': 'synthetic-material-v3',
        'dataset_type': 'synthetic_noisy_bilinear_elastoplastic_surrogate',
        'units': {'strain': 'dimensionless', 'stress': 'MPa'},
        'noise_sd_mpa': noise_sd, 'tolerance_mpa': TOLERANCE_MPA,
        'training_measurements': int(readings.size), 'fitted_elastic_modulus_mpa': ehat,
        'elastic_slope_standard_error_mpa': slope_se,
        'strategies': strategies, 'revision_fits': fits,
        'true_yield_strain_benchmark_only': sim.yield_strain,
        'reference_operational_onset_benchmark_only': reference_onset,
        'fitted_yield_strain': active_fit.get('yield_strain'),
        'fitted_hardening_modulus_mpa': active_fit.get('hardening_modulus_mpa'),
        'heldout_linear_mae_mpa': initial_mae, 'heldout_revised_mae_mpa': heldout_errors['active'],
        'heldout_initial_decision': mae_decision(initial_mae, noise_sd),
        'heldout_revised_decisions': {name: mae_decision(value, noise_sd) for name, value in heldout_errors.items()},
        'heldout_revised_mae_by_policy_mpa': heldout_errors,
        'holdout': {'strain': heldout_strain.tolist(), 'stress_mean_mpa': heldout.tolist(),
                    'initial_predictions_mpa': initial_predictions.tolist(), 'replicates': 3,
                    'protocol': 'v3 final split; legacy v1 and v2 are development'},
        'ablations': {'no_counterexample_search_mae_mpa': initial_mae, 'no_revision_mae_mpa': initial_mae},
        'trace': log.manifest(), 'evaluator_only_environment': {
            'elastic_modulus_mpa': sim.elastic_modulus_mpa, 'hardening_modulus_mpa': sim.hardening_modulus_mpa,
            'yield_strain': sim.yield_strain, 'noise_sd_mpa': noise_sd}}
    if raw_path is not None:
        log.save(raw_path)
        record['raw_artifact'] = raw_path.name
    return record


def summary(values):
    available = [v for v in values if v is not None and np.isfinite(v)]
    if not available:
        return {'n': 0, 'median': None, 'q25': None, 'q75': None, 'iqr': None}
    q25, median, q75 = np.quantile(available, [.25, .5, .75])
    return {'n': len(available), 'median': float(median), 'q25': float(q25), 'q75': float(q75), 'iqr': float(q75 - q25)}


def aggregate(records):
    methods = {}
    for name in POLICIES:
        rows = [r['strategies'][name] for r in records]
        widths = summary([s['bracket_width'] for s in rows])
        coverage = [s['reference_onset_covered_evaluator_only'] for s in rows if s['reference_onset_covered_evaluator_only'] is not None]
        methods[name] = {'median_bracket_width_strain': widths['median'], 'bracket_width_summary': widths,
            'probes_per_seed': BUDGET, 'measurements_per_seed': BUDGET * REPLICATES,
            'nonmonotone_replicates': sum(s['nonmonotone_observations'] for s in rows),
            'inconclusive_boundary_fraction': sum(s['boundary_status'] == INCONCLUSIVE for s in rows) / len(rows),
            'reference_onset_coverage_fraction': float(np.mean(coverage)) if coverage else None,
            'coverage_denominator': len(coverage),
            'holdout_revised_mae_mpa': summary([r['heldout_revised_mae_by_policy_mpa'][name] for r in records]),
            'revision_audit_inconclusive_fraction': sum(r['heldout_revised_decisions'][name]['status'] == INCONCLUSIVE for r in records) / len(records),
            'revision_audit_survival_fraction': sum(r['heldout_revised_decisions'][name]['status'] == SURVIVES for r in records) / len(records)}
    initial = summary([r['heldout_linear_mae_mpa'] for r in records])
    revised = summary([r['heldout_revised_mae_mpa'] for r in records])
    return {'seed_count': len(records), 'seed_ids': [r['seed'] for r in records], 'methods': methods,
            'holdout_linear_mae_mpa': initial, 'holdout_revised_mae_mpa': revised,
            'median_holdout_linear_mae_mpa': initial['median'], 'median_holdout_revised_mae_mpa': revised['median'],
            'budget': {'common_training_measurements': 40, 'per_policy_probe_measurements': 40,
                       'common_final_audit_measurements': 249},
            'scientific_limits': ['One synthetic material, repeated noise seeds, not independent physical materials',
                'Monotonic prior; intervals are not confidence intervals',
                'Bilinear family predeclared; no comparison with state-of-the-art constitutive fitting',
                'MAE is against independent three-reading means, which include instrument noise']}


def make_plot(record, path):
    environment = record['evaluator_only_environment']
    sim = MaterialSimulator(**environment)
    strains = np.linspace(0, MAX_EPS, 300)
    E = record['fitted_elastic_modulus_mpa']
    fig, ax = plt.subplots(figsize=(8.6, 5))
    ax.plot(strains * 100, sim.noiseless_stress(strains), label='Reference: evaluator-only simulator truth', lw=2.5)
    ax.plot(strains * 100, E * strains, '--', label='Initial linear fit', lw=1.8)
    if record['fitted_yield_strain'] is not None:
        ax.plot(strains * 100, predict_bilinear(strains, E, record['fitted_yield_strain'], record['fitted_hardening_modulus_mpa']),
                label='Predeclared bilinear revision', lw=2)
    bounds = record['strategies']['active']['boundary_interval']
    if bounds:
        ax.axvspan(bounds[0] * 100, bounds[1] * 100, color='orange', alpha=.3, label='Empirical 10-MPa deviation bracket')
    obs = record['strategies']['active']['observations']
    ax.scatter([o['strain'] * 100 for o in obs], [o['mean_stress_mpa'] for o in obs], s=18, color='black', label='Active probe means (4 readings)')
    ax.axvline(sim.yield_strain * 100, ls=':', color='gray', label='Yield: evaluator-only; different from deviation onset')
    ax.set(xlabel='Engineering strain (%)', ylabel='Engineering stress (MPa)', title='Synthetic material: search, limited repair, independent audit')
    ax.legend(fontsize=7.5, loc='upper left')
    fig.tight_layout()
    fig.savefig(path, dpi=175)
    plt.close(fig)


def execute(out, seeds=30, start_seed=2026):
    out.mkdir(parents=True, exist_ok=True)
    records = [run(seed, raw_path=out / f'seed_{seed}_raw.npz') for seed in range(start_seed, start_seed + seeds)]
    report = {**aggregate(records), 'protocol_version': '3.0.0', 'software': provenance(), 'records': records}
    write_json(out / 'results.json', report)
    make_plot(records[0], out / 'stress_strain_boundary.png')
    print(f'Synthetic material: {seeds} noise seeds; each policy {BUDGET} probes / {BUDGET * REPLICATES} readings')
    for name, s in report['methods'].items():
        width = s['median_bracket_width_strain']
        print(f"  {name}: median bracket={width}; reference coverage={s['reference_onset_coverage_fraction']}; inconclusive boundary={s['inconclusive_boundary_fraction']}")
    print(f"  Independent median MAE (MPa): linear={report['median_holdout_linear_mae_mpa']:.6f}; revised={report['median_holdout_revised_mae_mpa']}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=30)
    parser.add_argument('--start-seed', type=int, default=2026)
    parser.add_argument('--out', type=Path, default=Path('outputs/materials'))
    args = parser.parse_args()
    if args.seeds < 1 or args.start_seed < 0:
        parser.error('Positive seed count and nonnegative start seed required')
    execute(args.out, args.seeds, args.start_seed)

if __name__ == '__main__':
    main()
