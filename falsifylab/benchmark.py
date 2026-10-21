"""Predeclared CPU benchmark: controls, ablations, noise, horizon and solver checks."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .artifacts import write_json, digest, provenance
from .decisions import REFUTED, SURVIVES, INCONCLUSIVE
from .run_demo import CASES, run_case
from .run_materials import execute as materials_execute, run as materials_run, aggregate, summary


PROTOCOL = {
    'version': 'v3-frozen-2026-10-21',
    'development_data': 'legacy v1 retained in baseline and v2 smoke tests in /tmp are development; not final evaluation',
    'oscillator_final': '3 predeclared new trajectories, seed-specific +/- .025 m amplitude jitter',
    'materials_final': '83 predeclared new strains with 3 readings each; independent SeedSequence stream',
    'thresholds': {'oscillator_relative_drift': .02, 'materials_operational_deviation_mpa': 10.0},
    'noise_robustness': {'seed_count_cap': 3, 'oscillator_sd': [.001, .01], 'horizon_factors': [.5, 2.0],
                         'materials_sd_mpa': [0.0, .8, 8.0, 80.0]},
    'solver_settings': [{'rtol': 2e-11, 'atol': 1e-13}, {'rtol': 1e-7, 'atol': 1e-9}],
    'choices': 'All thresholds, model families and robustness settings predeclared in code; no optimization on final holdout',
}


def oscillator_summary(records):
    rows = []
    for name, _, _ in CASES:
        subset = [r for r in records if r['system'] == name]
        if not subset:
            continue
        n = len(subset)
        initial = [r['initial_hypothesis_stress_verdict'] for r in subset]
        revised = [r.get('revised_verdict', INCONCLUSIVE) for r in subset]
        rows.append({'system': name, 'n': n,
            'initial_refutation_rate': initial.count(REFUTED) / n,
            'initial_inconclusive_fraction': initial.count(INCONCLUSIVE) / n,
            'initial_false_refutation_rate_valid_control': initial.count(REFUTED) / n if name == CASES[0][0] else None,
            'negative_control_revised_refutation_rate': revised.count(REFUTED) / n if name == CASES[2][0] else None,
            'revised_survival_rate': revised.count(SURVIVES) / n if name != CASES[0][0] else None,
            'revised_inconclusive_fraction': revised.count(INCONCLUSIVE) / n if name != CASES[0][0] else None,
            'initial_drift': summary([r['heldout_initial_relative_drift'] for r in subset]),
            'revised_drift': summary([r.get('revised_heldout_relative_drift') for r in subset]),
            'no_search_quartic_survival_rate': sum(r['ablations']['no_counterexample_search_quartic'] == SURVIVES for r in subset) / n,
            'no_revision_survival_rate': initial.count(SURVIVES) / n,
            'costs_example': subset[0]['trace']['costs']})
    return rows


def comparison_plot(metrics, path):
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.7))
    methods = metrics['materials']['methods']
    names = list(methods)
    medians = [methods[n]['bracket_width_summary']['median'] for n in names]
    q25 = [methods[n]['bracket_width_summary']['q25'] for n in names]
    q75 = [methods[n]['bracket_width_summary']['q75'] for n in names]
    axes[0].bar(names, medians, color=['#16837b', '#466ea3', '#a57943'],
        yerr=[np.array(medians) - q25, np.array(q75) - medians], capsize=5)
    axes[0].set(ylabel='Empirical bracket width (strain)', title='Equal budget: 10 probes / 40 readings')
    axes[0].ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
    initial = metrics['materials']['holdout_linear_mae_mpa']['median']
    revised = metrics['materials']['holdout_revised_mae_mpa']['median']
    axes[1].bar(['Initial / no revision', 'Bilinear repair'], [initial, revised], color=['#a45b50', '#16837b'])
    axes[1].set(yscale='log', ylabel='Independent audit MAE (MPa, log scale)', title='Predeclared family on one synthetic material')
    fig.suptitle(f"FalsifyLab: {metrics['seed_count']} noise seeds; bars median, whiskers IQR")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def execute(out: Path, seeds=30, start_seed=2026):
    out.mkdir(parents=True, exist_ok=True)
    # Save protocol before any final observation. The benchmark does not tune.
    write_json(out / 'protocol.json', PROTOCOL)
    material_report = materials_execute(out / 'materials', seeds, start_seed)
    oscillator_records = []
    for seed in range(start_seed, start_seed + seeds):
        for label, params, revise in CASES:
            row, *_ = run_case(label, params, revise, seed=seed,
                               raw_path=out / f'osc_{label}_{seed}.npz')
            oscillator_records.append(row)
        print(f'Oscillator controls: {seed - start_seed + 1}/{seeds} seeds', flush=True)
    write_json(out / 'oscillator_records.json', oscillator_records)
    robustness_osc, robustness_mat = [], []
    nrobust = min(3, seeds)
    for seed in range(start_seed, start_seed + nrobust):
        for noise in PROTOCOL['noise_robustness']['oscillator_sd']:
            for horizon in PROTOCOL['noise_robustness']['horizon_factors']:
                for label, params, revise in CASES:
                    row, *_ = run_case(label, params, revise, seed=seed, noise_sd=noise, horizon_scale=horizon,
                        raw_path=out / f'noise_osc_{label}_{seed}_{noise}_{horizon}.npz')
                    robustness_osc.append(row)
        for noise in PROTOCOL['noise_robustness']['materials_sd_mpa']:
            row = materials_run(seed, noise_sd=noise, raw_path=out / f'noise_material_{seed}_{noise}.npz')
            robustness_mat.append(row)
        print(f'Noise/horizon checks: {seed - start_seed + 1}/{nrobust} seeds', flush=True)
    write_json(out / 'robustness_oscillator_records.json', robustness_osc)
    write_json(out / 'robustness_materials_records.json', robustness_mat)
    sensitivity_records, sensitivity = [], []
    for setting in PROTOCOL['solver_settings']:
        for label, params, revise in CASES:
            row, *_ = run_case(label, params, revise, seed=start_seed, solver=setting,
                raw_path=out / f'solver_{label}_{setting["rtol"]}.npz')
            sensitivity_records.append(row)
            sensitivity.append({'system': label, **setting,
                'initial_drift': row['heldout_initial_relative_drift'],
                'revised_drift': row.get('revised_heldout_relative_drift'),
                'initial_status': row['initial_hypothesis_stress_verdict'],
                'revised_status': row.get('revised_verdict'),
                'rhs_evaluations': sum(c['rhs_evaluations'] for c in row['trace']['costs'].values())})
    write_json(out / 'solver_records.json', sensitivity_records)
    noise_summary_osc = []
    for noise in PROTOCOL['noise_robustness']['oscillator_sd']:
        for horizon in PROTOCOL['noise_robustness']['horizon_factors']:
            noise_summary_osc.append({'noise_sd_x_and_v': noise, 'horizon_factor': horizon,
                'systems': oscillator_summary([r for r in robustness_osc if r['measurement_noise_sd'] == noise and r['horizon_scale'] == horizon])})
    noise_summary_mat = []
    for noise in PROTOCOL['noise_robustness']['materials_sd_mpa']:
        noise_summary_mat.append({'noise_sd_mpa': noise, **aggregate([r for r in robustness_mat if r['noise_sd_mpa'] == noise])})
    metrics = {'protocol_version': PROTOCOL['version'], 'seed_count': seeds,
        'seed_ids': list(range(start_seed, start_seed + seeds)),
        'materials': {k: v for k, v in material_report.items() if k not in ('software', 'records')},
        'oscillator': oscillator_summary(oscillator_records),
        'robustness': {'oscillator': noise_summary_osc, 'materials': noise_summary_mat},
        'solver_sensitivity': sensitivity,
        'ablations': {'materials_no_search_and_no_revision': material_report['holdout_linear_mae_mpa'],
            'oscillator_no_search': 'Quartic fit from discovery only; same holdout. Can succeed without search in noiseless toy; see per-system survival rates.',
            'independent_audit': 'No audit ablation is conceptual only: removing it hides the failed quadratic claim; no holdout was used for fitting.'},
        'interpretation': ['Control rates are descriptive across simulation/noise seeds, not calibrated p-values',
            'No claim of superiority over active learning or symbolic regression',
            'Boundary width alone is not accuracy: inspect coverage and inconclusive fractions',
            'Repeated seeds refer to one physical system per case, not independent materials'],
        'failures': [{'system': r['system'], 'seed': r['seed'], 'reason': r['revision_failure']}
                     for r in oscillator_records + robustness_osc if r['revision_failure']]}
    write_json(out / 'metrics.json', metrics)
    with (out / 'metrics.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['task','method','metric','median','q25','q75','units','n'])
        writer.writeheader()
        for method, values in metrics['materials']['methods'].items():
            for metric, name, units in [('bracket_width_summary','boundary_width','strain'), ('holdout_revised_mae_mpa','revised_mae','MPa')]:
                s = values[metric]
                writer.writerow(dict(task='materials', method=method, metric=name, median=s['median'], q25=s['q25'], q75=s['q75'], units=units, n=s['n']))
        for row in metrics['oscillator']:
            for metric in ('initial_refutation_rate','initial_inconclusive_fraction','revised_survival_rate','no_search_quartic_survival_rate'):
                writer.writerow(dict(task=row['system'], method='polynomial', metric=metric, median=row[metric], units='fraction', n=row['n']))
    with (out / 'solver_sensitivity.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sensitivity[0]))
        writer.writeheader()
        writer.writerows(sensitivity)
    comparison_plot(metrics, out / 'comparison.png')
    write_json(out / 'environment.json', provenance())
    # All generated data files, including raw arrays, have a portable checksum.
    paths = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'checksums.json')
    write_json(out / 'checksums.json', {str(p.relative_to(out)): digest(p) for p in paths})
    print(f'Saved {out}/metrics.json and metrics.csv; {len(oscillator_records)} primary oscillator trials', flush=True)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=30)
    parser.add_argument('--start-seed', type=int, default=2026)
    parser.add_argument('--out', type=Path, default=Path('outputs/benchmark'))
    args = parser.parse_args()
    if args.seeds < 1 or args.start_seed < 0:
        parser.error('Positive seeds and nonnegative start seed required')
    execute(args.out, args.seeds, args.start_seed)

if __name__ == '__main__':
    main()
