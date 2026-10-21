import numpy as np
from falsifylab.materials import MaterialSimulator, fit_hooke, predict_bilinear
from falsifylab.run_materials import run, BUDGET, REPLICATES


def test_simulator_continuity_at_yield():
    m = MaterialSimulator()
    values = m.noiseless_stress([m.yield_strain - 1e-9, m.yield_strain, m.yield_strain + 1e-9])
    assert abs(values[1] - m.elastic_modulus_mpa * m.yield_strain) < 1e-8
    assert values[0] < values[1] < values[2]


def test_fit_hooke_on_elastic_region():
    m = MaterialSimulator(noise_sd_mpa=0)
    x = np.array([0.0001, 0.0004, 0.0008])
    y = m.observe(x, np.random.default_rng(10))
    assert abs(fit_hooke(x, y) - m.elastic_modulus_mpa) < 1e-8


def test_search_budget_and_no_leakage():
    r = run(2026)
    for method in ('active', 'uniform', 'random'):
        s = r['strategies'][method]
        assert s['probes'] == BUDGET
        assert s['measurements'] == BUDGET * REPLICATES
        assert s['boundary_interval'][0] < s['boundary_interval'][1]


def test_repaired_fit_reduces_independent_holdout_mae():
    r = run(2026)
    assert r['heldout_revised_mae_mpa'] < r['heldout_linear_mae_mpa']
    assert 0.001 < r['fitted_yield_strain'] < 0.003


def test_physical_bilinear_prediction():
    m = MaterialSimulator()
    x = np.linspace(0, 0.016, 30)
    y = predict_bilinear(x, m.elastic_modulus_mpa, m.yield_strain, m.hardening_modulus_mpa)
    np.testing.assert_allclose(y, m.noiseless_stress(x), atol=1e-12)
