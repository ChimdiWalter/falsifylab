import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import matplotlib.pyplot as plt
    from falsifylab.physics import simulate
    from falsifylab.hypothesis import fit_hypothesis
    from falsifylab.decisions import drift_decision
    from falsifylab.materials import predict_bilinear
    from falsifylab.run_materials import TOLERANCE_MPA
    from notebooks.exploration import MATERIAL_PRESETS, SYSTEMS, explore_material, explore_oscillator

    return (
        MATERIAL_PRESETS,
        SYSTEMS,
        TOLERANCE_MPA,
        drift_decision,
        explore_material,
        explore_oscillator,
        fit_hypothesis,
        mo,
        np,
        plt,
        predict_bilinear,
        simulate,
    )


@app.cell
def _(mo):
    mo.md("""
    # FalsifyLab / explore counterexamples with the Python engine

    Every control below reruns the **actual tested engine** (`falsifylab.run_materials.run`
    and `falsifylab.run_demo.run_case`) with unchanged thresholds, budgets and families.
    These are **exploratory reruns**. The frozen submission evidence stays in `outputs/`.
    The oscillator audit reuses the v3 final conditions, so a rerun here is not a new
    untouched evaluation. No paid service or LLM is called.
    """)
    return


@app.cell
def _(MATERIAL_PRESETS, mo):
    preset = mo.ui.dropdown(options=list(MATERIAL_PRESETS), value='Benchmark surrogate (E 210 GPa)', label='Hidden material')
    noise = mo.ui.slider(0.0, 16.0, step=0.2, value=0.8, label='Instrument noise SD (MPa)', show_value=True)
    mseed = mo.ui.number(start=0, stop=1_000_000, step=1, value=2026, label='Seed')
    policy = mo.ui.dropdown(options=['active', 'uniform', 'random'], value='active', label='Show probes for policy')
    mo.vstack([mo.md('## 1 · Materials: where does Hooke\'s law stop working?'), mo.hstack([preset, noise, mseed, policy], justify='start', wrap=True)])
    return mseed, noise, policy, preset


@app.cell
def _(explore_material, mseed, noise, preset):
    material = explore_material(preset.value, noise.value, mseed.value)
    return (material,)


@app.cell
def _(TOLERANCE_MPA, material, mo, np, plt, policy, predict_bilinear):
    _rec, _sim = material['record'], material['simulator']
    _s = _rec['strategies'][policy.value]
    _E = _rec['fitted_elastic_modulus_mpa']
    _fig, (_a, _b) = plt.subplots(1, 2, figsize=(11, 4.2))
    _x = np.linspace(.0009, .0141, 600)
    _a.plot(_x * 100, np.maximum(np.abs(_sim.noiseless_stress(_x) - _E * _x), .05), '--', color='gray', lw=1, label='Hidden truth (evaluator only)')
    for _i, _o in enumerate(_s['observations']):
        _c = {'REFUTED': '#d03b3b', 'NOT_REFUTED_UNDER_TESTED_CONDITIONS': '#0ca30c'}.get(_o['status'], '#fab219')
        _a.errorbar(_o['strain'] * 100, max(_o['absolute_deviation_mpa'], .05), yerr=[[min(_o['uncertainty_allowance_mpa'], max(_o['absolute_deviation_mpa'], .05) - .03)], [_o['uncertainty_allowance_mpa']]],
                    fmt='x' if _o['status'] == 'REFUTED' else 'o', color=_c, ms=8, capsize=2)
        _a.annotate(str(_i + 1), (_o['strain'] * 100, max(_o['absolute_deviation_mpa'], .05)), textcoords='offset points', xytext=(0, 7), ha='center', fontsize=8)
    _a.axhline(TOLERANCE_MPA, color='#d03b3b', ls=':', lw=1.2, label='10 MPa tolerance')
    if _s['boundary_interval']:
        _a.axvspan(*(np.array(_s['boundary_interval']) * 100), color='#6250d6', alpha=.2, label='Observed onset bracket')
    if material['first_exceedance'] is not None:
        _a.axvline(material['first_exceedance'] * 100, color='gray', ls=':', lw=1, label='True first exceedance (evaluator)')
    _a.set(yscale='log', xlabel='Engineering strain (%)', ylabel='|mean − Hooke prediction| (MPa)', title=f'{policy.value}: 10 probes × 4 readings')
    _a.legend(fontsize=7.5, loc='lower right')
    _xs = np.linspace(0, .0145, 300)
    _b.plot(_xs * 100, _E * _xs, '--', color='#eb6834', label='Candidate: Hooke law')
    _fit = _rec['revision_fits'][policy.value]
    if _fit['status'] == 'FITTED':
        _b.plot(_xs * 100, predict_bilinear(_xs, _E, _fit['yield_strain'], _fit['hardening_modulus_mpa']), color='#2a78d6', label='Bilinear revision (frozen)')
    _b.plot(np.array(_rec['holdout']['strain']) * 100, _rec['holdout']['stress_mean_mpa'], 'o', mfc='none', color='#1baf7a', ms=3.5, label='Independent audit means')
    _b.set(xlabel='Engineering strain (%)', ylabel='Stress (MPa)', ylim=(-20, max(_rec['holdout']['stress_mean_mpa']) * 1.3 + 40), title='Revision and independent audit')
    _b.legend(fontsize=7.5)
    _fig.tight_layout()
    _row = next(r for r in material['policies'] if r['policy'] == policy.value)
    _miss = ('**Silent miss:** the bracket misses the true first exceedance without being flagged. This is the documented monotonic-prior limitation.'
             if _row['silent_miss'] else 'No silent miss for this policy: the bracket covers the true onset or is flagged INCONCLUSIVE.')
    mo.vstack([_fig, mo.md(f"""
    Candidate law fitted on 40 discovery readings: **σ = {_E:,.1f} MPa · ε**. Initial audit MAE
    **{_rec['heldout_linear_mae_mpa']:,.1f} MPa** ({_rec['heldout_initial_decision']['status']}).
    Readings used in this run: **{material['readings_total']}** (40 setup + 3 × 40 probes + 249 audit).
    {_miss}
    """), mo.ui.table(material['policies'], selection=None, label='All three policies, equal budget (evaluator columns use hidden truth)')])
    return


@app.cell
def _(SYSTEMS, mo):
    system = mo.ui.dropdown(options=list(SYSTEMS), value='duffing_nonlinearity', label='System')
    onoise = mo.ui.dropdown(options=['0', '0.001', '0.01'], value='0', label='Instrument noise SD (x in m, v in m/s)')
    horizon = mo.ui.dropdown(options=['0.5', '1.0', '2.0'], value='1.0', label='Observation-horizon factor')
    oseed = mo.ui.number(start=0, stop=1_000_000, step=1, value=2026, label='Seed')
    mo.vstack([mo.md('## 2 · Oscillator: is the quadratic energy really conserved?'), mo.hstack([system, onoise, horizon, oseed], justify='start', wrap=True)])
    return horizon, onoise, oseed, system


@app.cell
def _(explore_oscillator, horizon, onoise, oseed, system):
    oscillator = explore_oscillator(system.value, float(onoise.value), float(horizon.value), oseed.value)
    return (oscillator,)


@app.cell
def _(mo, oscillator, plt):
    _r, _tr = oscillator['result'], oscillator['audit_trajectory']
    _fig, _ax = plt.subplots(figsize=(10, 3.6))
    for _law, _label, _c in [(oscillator['quadratic'], 'Initial quadratic', '#eb6834'), (oscillator['revised'], 'Quartic revision', '#2a78d6')]:
        if _law is not None:
            _q = _law.evaluate(_tr)
            _ax.plot(_tr.time, (_q - _q[0]) / abs(_q[0]), label=_label, color=_c)
    _ax.axhline(0, color='gray', lw=.7, ls='--')
    _ax.set(xlabel='Time (s)', ylabel='(Q − Q(0)) / |Q(0)|', title='First independent audit trajectory')
    _ax.legend(fontsize=8)
    _fig.tight_layout()
    _catalog = [{'amplitude_m': o['amplitude'], 'horizon_s': o['horizon'], 'relative_drift': o['relative_drift'], 'status': o['status']}
                for o in _r['stress_search']['observations']]
    _cost = {k: v['simulator_calls'] for k, v in oscillator['costs'].items()}
    mo.vstack([mo.md(f"""
    Candidate: `{_r['initial_hypothesis']}` → audit **{_r['initial_hypothesis_stress_verdict']}**.
    Counterexamples in the 15-condition catalog: **{len(_r['stress_search']['counterexamples'])}**.
    Revision: `{_r.get('revised_hypothesis', 'not attempted')}` → **{_r.get('revised_verdict', 'NOT_ATTEMPTED')}**.
    Discovery-only quartic (no search): **{_r['ablations']['no_counterexample_search_quartic']}**.
    Simulator calls by partition: {_cost}.
    """), _fig, mo.ui.table(_catalog, selection=None, label='Stress catalog (2% demonstration threshold)')])
    return


@app.cell
def _(mo):
    amplitude = mo.ui.slider(.2, 2.0, step=.1, value=1.4, label='Your stress amplitude (m, nominal)', show_value=True)
    mo.vstack([mo.md('## 3 · Choose your own stress experiment (Duffing)\nA low amplitude may find no counterexample, and then the engine declines to revise.'), amplitude])
    return (amplitude,)


@app.cell
def _(amplitude, drift_decision, fit_hypothesis, mo, simulate):
    _discovery = [simulate(amplitude=_a, horizon=.8, steps=121, alpha=1.) for _a in (.12, .20, .27)]
    _initial = fit_hypothesis(_discovery, 2)
    _probe = simulate(amplitude=float(amplitude.value), horizon=6., steps=401, alpha=1.)
    _probe_decision = drift_decision(_initial, _probe)
    _revised = fit_hypothesis(_discovery + [_probe], 4) if _probe_decision['status'] == 'REFUTED' else None
    # Coefficients are fitted before this exploratory audit trajectory is simulated.
    _audit = simulate(amplitude=1.463, initial_velocity=.239, horizon=9.73, steps=641, alpha=1.)
    mo.md(f"""
    Probe at **{amplitude.value} m**: drift {_probe_decision['relative_drift']:.3%} → **{_probe_decision['status']}**.
    {'Revision: `' + _revised.expression + '`; audit ' + drift_decision(_revised, _audit)['status'] + '.' if _revised else 'No counterexample, so no revision is attempted.'}
    Initial quadratic on the audit trajectory: {drift_decision(_initial, _audit)['status']}.
    Cost: 5 simulator calls (3 discovery, 1 probe, 1 audit).
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    **Limits.** Synthetic systems only; hand-specified families that contain the truth;
    heuristic 2% drift and 10 MPa tolerances with no calibrated error control; the onset
    bracket is neither a confidence interval nor the physical yield point. A discovery-only
    quartic also fits the noise-free Duffing invariant. See `docs/INDEPENDENT_AUDIT.md`.
    """)
    return


if __name__ == "__main__":
    app.run()
