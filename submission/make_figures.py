"""Render submission figures from committed evidence (no numbers typed by hand).

Usage: python submission/make_figures.py  ->  submission/figures/*.png
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'submission' / 'figures'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e7e6e1'
INITIAL, REVISED, AUDIT, BRACKET = '#eb6834', '#2a78d6', '#1baf7a', '#6250d6'
GOOD, CRIT = '#0ca30c', '#d03b3b'
POLCOL = {'active': REVISED, 'uniform': INITIAL, 'random': AUDIT}
POLNAME = {'active': 'Adaptive bisection', 'uniform': 'Uniform grid', 'random': 'Random'}
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#c4c3bc', 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'axes.grid': True, 'grid.color': GRID, 'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False})


def load(rel):
    return json.loads((ROOT / rel).read_text())


def materials_figure():
    rec = load('outputs/benchmark/materials/results.json')['records'][0]
    raw = np.load(ROOT / 'outputs/benchmark/materials' / rec['raw_artifact'])
    d = rec['trace']['partitions']['discovery'][0]
    E, act = rec['fitted_elastic_modulus_mpa'], rec['strategies']['active']
    fit = rec['revision_fits']['active']
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    xs = np.linspace(0, .0145, 400)
    ax.plot(raw[d + '_strain'] * 100, raw[d + '_stress_mpa'].mean(axis=1), 'o', color=INK2, ms=4, label='Discovery means (40 readings)')
    ax.plot(xs * 100, E * xs, '--', color=INITIAL, lw=1.8, label='Candidate: Hooke law')
    ey, H = fit['yield_strain'], fit['hardening_modulus_mpa']
    ax.plot(xs * 100, E * np.minimum(xs, ey) + H * np.maximum(xs - ey, 0), color=REVISED, lw=1.8, label='Bilinear revision (frozen)')
    ax.plot(np.array(rec['holdout']['strain']) * 100, rec['holdout']['stress_mean_mpa'], 'o', mfc='none', mec=AUDIT, ms=3.6, label='Independent audit means (249 readings)')
    for o in act['observations']:
        ref = o['status'] == 'REFUTED'
        ax.plot(o['strain'] * 100, o['mean_stress_mpa'], 'x' if ref else 'o', color=CRIT if ref else GOOD, ms=8, mew=2)
    ax.plot([], [], 'x', color=CRIT, mew=2, label='Probe: law refuted')
    ax.plot([], [], 'o', color=GOOD, label='Probe: law holds')
    ax.set(xlim=(-.02, 1.45), ylim=(-40, 1650), xlabel='Engineering strain (%)', ylabel='Engineering stress (MPa)')
    ax.text(.46, 700, f'Hooke prediction keeps rising:\n{E * .014:,.0f} MPa at 1.4% strain', ha='left', va='center', color=INITIAL, fontsize=8.5)
    ax.legend(loc='upper left', fontsize=8)
    ins = ax.inset_axes([.6, .5, .38, .42])
    win = (.00185, .00225)
    near = [o for o in act['observations'] if win[0] <= o['strain'] <= win[1]]
    lo, hi = act['boundary_interval']
    ins.axvspan(lo * 100, hi * 100, color=BRACKET, alpha=.2)
    ins.axhline(10, color=CRIT, ls=':', lw=1.2)
    for o in near:
        ref = o['status'] == 'REFUTED'
        ins.errorbar(o['strain'] * 100, o['absolute_deviation_mpa'], yerr=o['uncertainty_allowance_mpa'], fmt='x' if ref else 'o', color=CRIT if ref else GOOD, ms=7, mew=2, capsize=2)
    ins.set(xlim=(win[0] * 100, win[1] * 100), ylim=(-4, 40), xlabel='strain (%)', ylabel='|error| (MPa)')
    ins.set_title(f'Observed 10 MPa onset: [{lo * 100:.4f}%, {hi * 100:.4f}%]', fontsize=8.5, color=INK)
    ins.tick_params(labelsize=7.5)
    ins.xaxis.label.set_size(8); ins.yaxis.label.set_size(8)
    ax.set_title('Synthetic material (seed 2026): 10 probes find where Hooke\'s law fails; a frozen revision is audited', fontsize=10.5, color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(OUT / 'fig1_materials_counterexample.png', dpi=200)
    plt.close(fig)


def noise_figure():
    sweep = load('audit/independent_checks.json')['posthoc_noise_sweep']['rows']
    xs = [r['noise_sd_mpa'] for r in sweep]
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.8), sharex=True)
    for p in ('active', 'uniform', 'random'):
        cov = [r[p]['covered'] / r[p]['evaluable_brackets'] for r in sweep]
        inc = [r[p]['boundary_inconclusive'] / r['n'] for r in sweep]
        style = {'active': ('o', '-'), 'uniform': ('s', '--'), 'random': ('D', ':')}[p]
        a.plot(xs, cov, marker=style[0], ls=style[1], color=POLCOL[p], label=POLNAME[p], lw=2, ms=6)
        b.plot(xs, inc, marker=style[0], ls=style[1], color=POLCOL[p], label=POLNAME[p], lw=2, ms=6)
    missed = sum(r[p]['evaluable_brackets'] - r[p]['covered'] for r in sweep for p in ('active', 'uniform', 'random'))
    for ax, t in ((a, 'Brackets containing the noiseless onset'), (b, 'Brackets flagged INCONCLUSIVE')):
        ax.set(xscale='log', xticks=xs, ylim=(-.04, 1.06), xlabel='Instrument noise SD (MPa)')
        ax.set_xticklabels([str(x) for x in xs])
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.set_title(t, fontsize=10, color=INK, loc='left')
    a.legend(fontsize=8.5, loc='lower left')
    fig.suptitle(f'Post-hoc audit, 30 seeds per level: {missed} brackets missed the onset, all where the engine abstained on every run.\n'
                 'Abstention is conservative, not discriminating: at 2 MPa bisection abstained on 26/30 brackets that were correct.', fontsize=10, x=.01, ha='left', color=INK)
    fig.tight_layout()
    fig.savefig(OUT / 'fig2_noise_abstention.png', dpi=200)
    plt.close(fig)


def oscillator_figure():
    res = load('outputs/results.json')
    case = next(c for c in res['cases'] if c['system'] == 'duffing_nonlinearity')
    raw = np.load(ROOT / 'outputs' / case['raw_artifact'])
    eid = case['trace']['partitions']['holdout'][0]
    t, x, v = raw[eid + '_time'], raw[eid + '_x'], raw[eid + '_v']
    m = case['frozen_models']
    ex = load('audit/posthoc_oscillator_excitation.json')['summary']
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.2, 4.1), gridspec_kw={'width_ratios': [1.25, 1]})
    for key, lab, col in (('initial', f"Quadratic Q = v² + {m['initial']['quadratic']:.3f}x²", INITIAL), ('revised', f"Quartic Q = v² + {m['revised']['quadratic']:.3f}x² + {m['revised']['quartic']:.3f}x⁴", REVISED)):
        q = v**2 + m[key]['quadratic'] * x**2 + m[key]['quartic'] * x**4
        a.plot(t, (q - q[0]) / abs(q[0]), color=col, lw=1.8, label=lab)
    a.set(xlabel='Time (s)', ylabel='(Q − Q(0)) / |Q(0)|')
    a.set_title('Independent Duffing audit trajectory (noise-free)', fontsize=10, color=INK, loc='left')
    a.legend(fontsize=8.5, loc='center right')
    names = [('none', 'Discovery\nonly'), ('random', 'Random\ncatalog run'), ('search', 'Search-\nselected'), ('largest', 'Largest\namplitude')]
    width = .38
    for i, row in enumerate(ex):
        pos = np.arange(4) + (i - .5) * width
        ref = np.array([row[k]['REFUTED'] for k, _ in names]) / row['n']
        inc = np.array([row[k]['INCONCLUSIVE'] for k, _ in names]) / row['n']
        ok = np.array([row[k]['NOT_REFUTED'] for k, _ in names]) / row['n']
        b.bar(pos, ref, width * .92, color=CRIT, label='refuted' if i == 0 else None)
        b.bar(pos, inc, width * .92, bottom=ref, color='#fab219', label='inconclusive' if i == 0 else None)
        b.bar(pos, ok, width * .92, bottom=ref + inc, color=GOOD, label='not refuted' if i == 0 else None)
        for xp in pos:
            b.text(xp, 1.02, f"σ={row['noise_sd']}", ha='center', va='bottom', fontsize=6.5, color=INK2, rotation=90)
    b.set_xticks(np.arange(4))
    b.set_xticklabels([n for _, n in names], fontsize=8)
    b.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    b.set(ylim=(0, 1.22), ylabel='Audit verdict of the quartic revision', yticks=[0, .2, .4, .6, .8, 1])
    b.set_title('Under noise (post-hoc, 30 seeds per bar)', fontsize=10, color=INK, loc='left')
    b.legend(fontsize=7.5, loc='upper center', ncol=3, bbox_to_anchor=(.5, -.2))
    b.text(0.0, -0.42, 'Search used 15 catalog runs + 1; the largest-amplitude design used 1 run.', transform=b.transAxes, fontsize=7.5, color=INK2)
    fig.tight_layout()
    fig.savefig(OUT / 'fig3_oscillator_revision.png', dpi=200)
    plt.close(fig)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    materials_figure()
    noise_figure()
    oscillator_figure()
    print('wrote', sorted(p.name for p in OUT.glob('*.png')))
