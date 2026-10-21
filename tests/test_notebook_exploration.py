from notebooks.exploration import MATERIAL_PRESETS, SYSTEMS, explore_material, explore_oscillator


def test_material_exploration_covers_and_audits_benchmark_preset():
    out = explore_material('Benchmark surrogate (E 210 GPa)', 0.8, 2026)
    active = next(r for r in out['policies'] if r['policy'] == 'active')
    assert active['readings'] == 40 and out['readings_total'] == 40 + 3 * 40 + 249
    assert active['evaluator_covers_first_exceedance'] is True and not active['silent_miss']
    assert active['audit_status'] == 'NOT_REFUTED_UNDER_TESTED_CONDITIONS'


def test_hidden_dip_reproduces_documented_silent_miss():
    out = explore_material('Hidden softening dip (breaks monotonicity)', 0.8, 2026)
    active = next(r for r in out['policies'] if r['policy'] == 'active')
    assert out['first_exceedance'] < 0.0014
    assert active['silent_miss'] is True


def test_high_noise_abstains_instead_of_silent_miss():
    for preset in MATERIAL_PRESETS:
        if 'dip' in preset:
            continue
        out = explore_material(preset, 16.0, 2027)
        assert not any(r['silent_miss'] for r in out['policies'])


def test_oscillator_exploration_controls_behave():
    duffing = explore_oscillator('duffing_nonlinearity', 0.0, 1.0, 2026)['result']
    assert duffing['initial_hypothesis_stress_verdict'] == 'REFUTED'
    assert duffing['revised_verdict'] == 'NOT_REFUTED_UNDER_TESTED_CONDITIONS'
    harmonic = explore_oscillator('harmonic_undamped_control', 0.0, 1.0, 2026)['result']
    assert harmonic['initial_hypothesis_stress_verdict'] == 'NOT_REFUTED_UNDER_TESTED_CONDITIONS'
    damped = explore_oscillator('weakly_damped_negative_control', 0.0, 1.0, 2026)['result']
    assert damped['revised_verdict'] == 'REFUTED'
    assert set(SYSTEMS) == {'harmonic_undamped_control', 'duffing_nonlinearity', 'weakly_damped_negative_control'}
