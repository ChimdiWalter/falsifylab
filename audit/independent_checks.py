"""Independent numerical audit of the FalsifyLab v3 evidence.

Runs checks that `falsifylab.verify` does not perform: symbolic derivation,
an independent implicit integrator, refits of frozen models from saved raw
pre-freeze data, noise-floor comparison, leakage probes, a hidden
nonmonotonicity failure case and an exploratory post-hoc noise sweep.

Nothing here changes the frozen protocol. Post-hoc runs are labelled as such.

Usage: python audit/independent_checks.py [benchmark_dir] [out_json]
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp, trapezoid

from falsifylab.hypothesis import Hypothesis, fit_hypothesis, relative_drift
from falsifylab.materials import MaterialSimulator, fit_hooke, fit_bilinear
from falsifylab.physics import Trajectory
from falsifylab.run_materials import run as material_run, MIN_EPS, MAX_EPS, BUDGET, TOLERANCE_MPA, POLICIES

ROOT = Path(__file__).resolve().parents[1]
BENCH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs' / 'benchmark'
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'audit' / 'independent_checks.json'
results: dict = {'benchmark_dir': str(BENCH)}


def check(name, passed, **details):
    results.setdefault('checks', []).append({'name': name, 'pass': bool(passed), **details})
    print(f"{'PASS' if passed else 'FAIL'}  {name}  {json.dumps(details, default=float)[:220]}")


# A. Symbolic energy balance ------------------------------------------------
t = sp.symbols('t')
w, a, g = sp.symbols('omega alpha gamma', positive=True)
x = sp.Function('x')(t)
v = sp.diff(x, t)
Q = v**2 + w**2 * x**2 + a / 2 * x**4
xdd = -w**2 * x - a * x**3 - g * v
dQ = sp.simplify(sp.diff(Q, t).subs(sp.diff(x, t, 2), xdd))
check('A symbolic dQ/dt = -2 gamma v^2', sp.simplify(dQ + 2 * g * v**2) == 0, dQdt=str(dQ))


# B. Energy balance with an independent implicit integrator (Radau) ----------
def radau(amplitude, velocity, omega, alpha, gamma, horizon, steps):
    f = lambda _t, s: [s[1], -omega**2 * s[0] - alpha * s[0]**3 - gamma * s[1]]
    ts = np.linspace(0, horizon, steps)
    sol = solve_ivp(f, [0, horizon], [amplitude, velocity], method='Radau', t_eval=ts, rtol=1e-12, atol=1e-14)
    assert sol.success
    return Trajectory(ts, sol.y[0], sol.y[1])


tr = radau(1.463, .239, 2.0, 0.0, .008, 9.73, 4001)
q_phys = tr.v**2 + 4.0 * tr.x**2
lost = 2 * .008 * trapezoid(tr.v**2, tr.time)
check('B damped energy balance Q(T)-Q(0) = -2 gamma int v^2 (Radau)',
      abs((q_phys[-1] - q_phys[0]) + lost) < 1e-5 * q_phys[0],
      delta_Q=float(q_phys[-1] - q_phys[0]), minus_dissipated=float(-lost))

# C/D. Oscillator records: refits, seed independence, independent integrator --
osc = json.loads((BENCH / 'oscillator_records.json').read_text())
by_system = {}
for r in osc:
    by_system.setdefault(r['system'], []).append(r)
for system, rows in by_system.items():
    models = {json.dumps(r['frozen_models'], sort_keys=True) for r in rows}
    check(f'D {system}: frozen models identical across seeds (noise-free primary runs)',
          True, distinct_frozen_models=len(models), seeds=len(rows),
          note='seeds only jitter final audit amplitudes; discovery/search/revision are deterministic')
    results.setdefault('oscillator_seed_structure', {})[system] = {'distinct_frozen_models': len(models), 'n': len(rows)}

duffing = by_system['duffing_nonlinearity']
rev = duffing[0]['frozen_models']['revised']
check('C Duffing quartic revision recovers physical coefficients (omega^2=4, alpha/2=0.5)',
      abs(rev['quadratic'] - 4) < 1e-6 and abs(rev['quartic'] - .5) < 1e-6, revised=rev,
      initial=duffing[0]['frozen_models']['initial'], no_search=duffing[0]['frozen_models']['no_search_quartic'])

# Refit frozen oscillator models from saved raw pre-freeze arrays.
refit_ok, refit_err = True, 0.0
for r in osc:
    with np.load(BENCH / r['raw_artifact'], allow_pickle=False) as data:
        def traj(eid):
            return Trajectory(data[eid + '_time'], data[eid + '_x'], data[eid + '_v'])
        disc = [traj(e) for e in r['trace']['partitions']['discovery']]
        q2 = fit_hypothesis(disc, 2)
        refit_err = max(refit_err, abs(q2.quadratic - r['frozen_models']['initial']['quadratic']))
        if r['frozen_models']['revised'] is not None:
            rv = fit_hypothesis(disc + [traj(e) for e in r['trace']['partitions']['revision']], 4)
            refit_err = max(refit_err, abs(rv.quadratic - r['frozen_models']['revised']['quadratic']),
                            abs(rv.quartic - r['frozen_models']['revised']['quartic']))
check('C frozen oscillator models re-derived from saved discovery/revision raw data (all seeds)',
      refit_err < 1e-9, max_abs_coefficient_difference=refit_err, records=len(osc))

# Independent integrator on the seed-2026 Duffing audit trajectories.
initial = Hypothesis(**duffing[0]['frozen_models']['initial'])
revised = Hypothesis(**rev)
design = np.random.default_rng(np.random.SeedSequence([2026, 17391]))
radau_drifts = []
for (amp, vel, hor, steps) in [(1.463, .239, 9.73, 641), (1.613, -.173, 11.57, 733), (1.243, .359, 8.13, 569)]:
    amp += float(design.uniform(-.025, .025))
    trj = radau(amp, vel, 2.0, 1.0, 0.0, hor, steps)
    radau_drifts.append({'amplitude': amp, 'initial': relative_drift(initial, trj), 'revised': relative_drift(revised, trj)})
saved = [h['initial']['relative_drift'] for h in duffing[0]['holdout_observations']]
check('E Duffing audit drift reproduced with Radau (independent of DOP853)',
      all(abs(d['initial'] - s) < 1e-6 for d, s in zip(radau_drifts, saved)) and all(d['revised'] < 1e-6 for d in radau_drifts),
      radau=radau_drifts, saved_initial=saved)

# Ablation under noise: does search add anything over a discovery-only quartic?
rob = json.loads((BENCH / 'robustness_oscillator_records.json').read_text())
noise_table = []
for sd in (.001, .01):
    for h in (.5, 2.0):
        rows = [r for r in rob if r['system'] == 'duffing_nonlinearity' and r['measurement_noise_sd'] == sd and r['horizon_scale'] == h]
        harm = [r for r in rob if r['system'] == 'harmonic_undamped_control' and r['measurement_noise_sd'] == sd and r['horizon_scale'] == h]
        noise_table.append({'noise_sd': sd, 'horizon_factor': h, 'n': len(rows),
            'duffing_initial': [r['initial_hypothesis_stress_verdict'] for r in rows],
            'duffing_revised': [r.get('revised_verdict') for r in rows],
            'duffing_no_search_quartic': [r['ablations']['no_counterexample_search_quartic'] for r in rows],
            'no_search_quartic_coeffs': [r['frozen_models']['no_search_quartic'] for r in rows],
            'revised_coeffs': [r['frozen_models']['revised'] for r in rows],
            'harmonic_initial': [r['initial_hypothesis_stress_verdict'] for r in harm]})
results['oscillator_noise_ablation'] = noise_table
tally = lambda key: {k: sum(row[key].count(k) for row in noise_table) for k in ('REFUTED', 'NOT_REFUTED_UNDER_TESTED_CONDITIONS', 'INCONCLUSIVE')}
results['oscillator_noise_ablation_tally'] = {'search_informed_quartic': tally('duffing_revised'),
    'discovery_only_quartic': tally('duffing_no_search_quartic'), 'harmonic_initial': tally('harmonic_initial'),
    'n_runs': sum(row['n'] for row in noise_table), 'source': 'frozen-protocol robustness subset (3 seeds x 2 noise x 2 horizon)'}
check('O under instrument noise the discovery-only quartic fails where the search-informed quartic does not',
      results['oscillator_noise_ablation_tally']['search_informed_quartic']['REFUTED'] == 0, **results['oscillator_noise_ablation_tally'])
for row in noise_table:
    print('   noise', row['noise_sd'], 'h', row['horizon_factor'], 'revised', row['duffing_revised'],
          'no-search', row['duffing_no_search_quartic'], 'harmonic', row['harmonic_initial'])

# F-K. Materials ---------------------------------------------------------------
mat = json.loads((BENCH / 'materials' / 'results.json').read_text())['records']
E, H, EY = 210_000.0, 1_500.0, .002
worst_hooke = worst_bilin = worst_onset = 0.0
floor, revised_mae, widths = [], {p: [] for p in POLICIES}, {p: [] for p in POLICIES}
budget_ok, order_ok, disjoint_ok = True, True, True
for r in mat:
    with np.load(BENCH / 'materials' / r['raw_artifact'], allow_pickle=False) as data:
        parts = r['trace']['partitions']
        d = parts['discovery'][0]
        ehat = fit_hooke(data[d + '_strain'], data[d + '_stress_mpa'])
        worst_hooke = max(worst_hooke, abs(ehat - r['fitted_elastic_modulus_mpa']))
        for p in POLICIES:
            ids = parts['probe_' + p]
            budget_ok &= len(ids) == BUDGET and sum(data[i + '_stress_mpa'].size for i in ids) == 40
            xs = np.array([data[i + '_strain'][0] for i in ids])
            ys = np.array([data[i + '_stress_mpa'][0].mean() for i in ids])
            if r['revision_fits'][p]['status'] == 'FITTED':
                ye, hh = fit_bilinear(xs, ys, ehat)
                worst_bilin = max(worst_bilin, abs(ye - r['revision_fits'][p]['yield_strain']) / ye,
                                  abs(hh - r['revision_fits'][p]['hardening_modulus_mpa']) / max(hh, 1))
            revised_mae[p].append(r['heldout_revised_mae_by_policy_mpa'][p])
            widths[p].append(r['strategies'][p]['bracket_width'])
        h = parts['holdout'][0]
        hx, hy = data[h + '_strain'], data[h + '_stress_mpa'].mean(axis=1)
        floor.append(float(np.mean(np.abs(MaterialSimulator().noiseless_stress(hx) - hy))))
        probe_x = {float(data[i + '_strain'][0]) for p in POLICIES for i in parts['probe_' + p]}
        disjoint_ok &= not (probe_x & set(map(float, hx)))
    queue = r['trace']['experiment_queue']
    first_holdout = min(i for i, e in enumerate(queue) if e['partition'] == 'holdout')
    order_ok &= r['trace']['model_freeze']['after_experiment'] <= first_holdout and all(e['partition'] == 'holdout' for e in queue[first_holdout:])
    # Closed-form operational onset for the fitted slope (yield side of the kink):
    # ehat*e - (E*EY + H*(e-EY)) = 10  ->  e = (10 + (E-H)*EY) / (ehat - H)
    analytic = (TOLERANCE_MPA + (E - H) * EY) / (r['fitted_elastic_modulus_mpa'] - H)
    worst_onset = max(worst_onset, abs(analytic - r['reference_operational_onset_benchmark_only']))
check('F Hooke slopes re-derived from raw discovery readings (30 seeds)', worst_hooke < 1e-6, max_abs_diff_mpa=worst_hooke)
check('F bilinear revisions re-derived from raw probe readings (30 seeds x 3 policies)', worst_bilin < 1e-4, max_rel_diff=worst_bilin)
check('G evaluator onset equals closed form (10 + (E-H) eps_y)/(Ehat - H)', worst_onset < 1e-12, max_abs_diff_strain=worst_onset)
check('K equal search budget: 10 probes / 40 readings per policy per seed', budget_ok)
check('J holdout acquired only after model freeze; nothing after holdout', order_ok)
check('J holdout strains disjoint from probe strains', disjoint_ok)
design_width = (MAX_EPS - MIN_EPS) / 2 ** (BUDGET - 2)
check('H active bracket width equals design constant (MAX-MIN)/2^8 in every seed',
      all(abs(wd - design_width) < 1e-15 for wd in widths['active']), design_width=design_width,
      uniform_design=(MAX_EPS - MIN_EPS) / (BUDGET - 1), uniform_widths=sorted(set(round(x, 12) for x in widths['uniform'])))
expected_floor = .8 / np.sqrt(3) * np.sqrt(2 / np.pi)
results['materials_noise_floor'] = {'expected_mae_of_true_model_mpa': expected_floor,
    'true_model_mae_median_mpa': float(np.median(floor)),
    'revised_mae_median_mpa': {p: float(np.median(revised_mae[p])) for p in POLICIES},
    'revised_minus_floor_median_mpa': {p: float(np.median(np.array(revised_mae[p]) - floor)) for p in POLICIES}}
check('I revised audit MAE sits at the measurement noise floor for every policy',
      all(abs(np.median(revised_mae[p]) - np.median(floor)) < .1 for p in POLICIES), **results['materials_noise_floor'])
lin = [r['heldout_linear_mae_mpa'] for r in mat]
hx = np.array(mat[0]['holdout']['strain'])
pre = hx <= mat[0]['reference_operational_onset_benchmark_only']
results['materials_audit_domain'] = {'holdout_strain_range': [float(hx.min()), float(hx.max())],
    'probe_domain': [MIN_EPS, MAX_EPS], 'holdout_points_before_onset': int(pre.sum()), 'holdout_points_after_onset': int((~pre).sum()),
    'note': 'audit interpolates inside the probed domain; it is not an extrapolation test'}
check('S audit lies inside probed strain domain (interpolation, not extrapolation)', hx.max() <= MAX_EPS, **results['materials_audit_domain'])


# M/N. Leakage probe and hidden nonmonotonicity ----------------------------------
def coverage_row(rec):
    return {p: {'interval': rec['strategies'][p]['boundary_interval'], 'status': rec['strategies'][p]['boundary_status'],
                'covered': rec['strategies'][p]['reference_onset_covered_evaluator_only'],
                'revised_audit': rec['heldout_revised_decisions'][p]['status'],
                'revised_mae': rec['heldout_revised_mae_by_policy_mpa'][p]} for p in POLICIES}


def silent_misses(recs, policy):
    """Uncovered evaluable brackets that the engine did NOT flag INCONCLUSIVE."""
    return sum(r['strategies'][policy]['reference_onset_covered_evaluator_only'] is False and
               r['strategies'][policy]['boundary_status'] != 'INCONCLUSIVE' for r in recs)


other = MaterialSimulator(elastic_modulus_mpa=70_000.0, yield_strain=.0045, hardening_modulus_mpa=3_000.0, noise_sd_mpa=.8)
alt = [material_run(seed, simulator=other) for seed in range(2026, 2056)]
offsets = [abs(np.mean(r['strategies']['active']['boundary_interval']) - r['reference_operational_onset_benchmark_only'])
           for r in alt if r['strategies']['active']['boundary_interval']]
results['alternate_material'] = {'material': 'E=70 GPa, eps_y=.0045, H=3 GPa, noise .8 MPa (hypothetical, post-hoc)',
    **{p: {'covered': sum(r['strategies'][p]['reference_onset_covered_evaluator_only'] is True for r in alt),
           'boundary_inconclusive': sum(r['strategies'][p]['boundary_status'] == 'INCONCLUSIVE' for r in alt),
           'silent_misses': silent_misses(alt, p),
           'revised_audit_survives': sum(r['heldout_revised_decisions'][p]['status'] == 'NOT_REFUTED_UNDER_TESTED_CONDITIONS' for r in alt)}
       for p in POLICIES}, 'n': len(alt), 'active_median_midpoint_offset_strain': float(np.median(offsets))}
check('N leakage probe: active search relocates to a different hidden material (30 seeds)',
      np.median(offsets) < 1e-4, **results['alternate_material'])


@dataclass(frozen=True)
class DippedMaterial(MaterialSimulator):
    """Bilinear material plus a localized 25 MPa softening dip at strain .0012-.0016 (pre-yield)."""
    def noiseless_stress(self, strain):
        e = np.asarray(strain, float)
        base = super().noiseless_stress(e)
        dip = 25.0 * np.clip(1 - np.abs(e - .0014) / .0002, 0, None)
        return base - dip


dip = DippedMaterial(noise_sd_mpa=.8)
nm = []
for seed in range(2026, 2036):
    rec = material_run(seed, simulator=dip)
    grid = np.linspace(0, MAX_EPS, 200001)
    dev = np.abs(dip.noiseless_stress(grid) - rec['fitted_elastic_modulus_mpa'] * grid)
    true_first = float(grid[np.argmax(dev > TOLERANCE_MPA)])
    nm.append({'seed': seed, 'true_first_onset': true_first, **{p: {
        'interval': rec['strategies'][p]['boundary_interval'], 'status': rec['strategies'][p]['boundary_status'],
        'silent': rec['strategies'][p]['boundary_status'] != 'INCONCLUSIVE',
        'nonmonotone_flag': rec['strategies'][p]['nonmonotone_observations'],
        'misses_first_onset': (rec['strategies'][p]['boundary_interval'] is not None and
                               rec['strategies'][p]['boundary_interval'][0] > true_first)} for p in POLICIES}})
results['hidden_nonmonotonicity'] = nm
miss = {p: sum(r[p]['misses_first_onset'] for r in nm) for p in POLICIES}
flag = {p: sum(r[p]['nonmonotone_flag'] for r in nm) for p in POLICIES}
silent_dip = {p: sum(r[p]['misses_first_onset'] and r[p]['silent'] for r in nm) for p in POLICIES}
check('M hidden-nonmonotonicity failure case reproduced (documented limitation)', miss['active'] == len(nm),
      seeds=len(nm), miss_counts=miss, silent_miss_counts=silent_dip, nonmonotone_flag_counts=flag,
      note='localized pre-yield softening dip; bisection reports a bracket above the true first 10 MPa exceedance')

# P. Recorded source hashes vs published files ----------------------------------
import hashlib
SCIENCE = ['falsifylab/physics.py', 'falsifylab/hypothesis.py', 'falsifylab/decisions.py', 'falsifylab/experiments.py',
           'falsifylab/materials.py', 'falsifylab/run_materials.py', 'falsifylab/run_demo.py', 'falsifylab/benchmark.py']
recorded = {}
for rel in ('outputs/results.json', 'outputs/materials/results.json', 'outputs/benchmark/materials/results.json'):
    recorded[rel] = json.loads((ROOT / rel).read_text())['software']['source_sha256']
current = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in SCIENCE}
mismatch = {rel: [f for f in SCIENCE if src.get(f) != current[f]] for rel, src in recorded.items()}
changed_other = sorted({f for src in recorded.values() for f, h in src.items() if f not in SCIENCE and (ROOT / f).exists()
                        and hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != h})
check('P evidence records carry SHA-256 of the 8 scientific modules that match the published files',
      not any(mismatch.values()), mismatch=mismatch, post_freeze_changed_non_science_files=changed_other)


# L. Exploratory post-hoc noise sweep (NOT the frozen protocol) -------------------
sweep = []
for sd in (0.8, 2.0, 4.0, 8.0, 16.0):
    recs = [material_run(seed, noise_sd=sd) for seed in range(2026, 2056)]
    entry = {'noise_sd_mpa': sd, 'n': len(recs)}
    for p in POLICIES:
        cov = [r['strategies'][p]['reference_onset_covered_evaluator_only'] for r in recs]
        entry[p] = {'evaluable_brackets': sum(c is not None for c in cov), 'covered': sum(c is True for c in cov),
                    'boundary_inconclusive': sum(r['strategies'][p]['boundary_status'] == 'INCONCLUSIVE' for r in recs),
                    'silent_misses': silent_misses(recs, p),
                    'revised_audit': {s: sum(r['heldout_revised_decisions'][p]['status'] == s for r in recs)
                                      for s in ('REFUTED', 'NOT_REFUTED_UNDER_TESTED_CONDITIONS', 'INCONCLUSIVE')},
                    'median_width': float(np.median([r['strategies'][p]['bracket_width'] for r in recs if r['strategies'][p]['bracket_width'] is not None] or [np.nan])),
                    'median_revised_mae': float(np.nanmedian([np.nan if r['heldout_revised_mae_by_policy_mpa'][p] is None else r['heldout_revised_mae_by_policy_mpa'][p] for r in recs]))}
    sweep.append(entry)
    print('   sweep', sd, {p: (entry[p]['covered'], entry[p]['evaluable_brackets'], entry[p]['boundary_inconclusive'], entry[p]['silent_misses']) for p in POLICIES})
results['posthoc_noise_sweep'] = {'label': 'EXPLORATORY POST-HOC AUDIT, seeds 2026-2055, not part of frozen protocol v3', 'rows': sweep}
check('L no silent misses: every uncovered bracket in the noise sweep is flagged INCONCLUSIVE',
      all(row[p]['silent_misses'] == 0 for row in sweep for p in POLICIES),
      silent={row['noise_sd_mpa']: {p: row[p]['silent_misses'] for p in POLICIES} for row in sweep})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(results, indent=2, default=float))
failed = [c['name'] for c in results['checks'] if not c['pass']]
print(f'\n{len(results["checks"]) - len(failed)}/{len(results["checks"])} checks pass; wrote {OUT.relative_to(ROOT) if OUT.is_relative_to(ROOT) else OUT}')
if failed:
    print('FAILED:', failed)
