import numpy as np
from falsifylab.hypothesis import fit_hypothesis, relative_drift
from falsifylab.physics import simulate
from falsifylab.run_demo import run_case


def test_undamped_harmonic_conservation():
    tr = [simulate(amplitude=x, omega=2.0, horizon=5) for x in (0.7, 1.1, 1.5)]
    law = fit_hypothesis(tr[:2], 2)
    assert abs(law.quadratic - 4.0) < 1e-6
    assert relative_drift(law, tr[2]) < 1e-7


def test_duffing_needs_quartic():
    params = dict(omega=2.0, alpha=1.0, gamma=0.0)
    tr = [simulate(amplitude=x, horizon=6, **params) for x in (0.8, 1.1, 1.6)]
    law = fit_hypothesis(tr[:2], 4)
    assert abs(law.quadratic - 4.0) < 1e-5
    assert abs(law.quartic - 0.5) < 1e-5
    assert relative_drift(law, tr[2]) < 1e-7


def test_adversarial_refinement_generalizes():
    params = dict(omega=2.0, alpha=1.0, gamma=0.0)
    result, _, _, _ = run_case("duffing", params, True)
    assert result["initial_hypothesis_stress_verdict"] == "REFUTED"
    assert result["revised_verdict"] == "NOT_REFUTED_UNDER_TESTED_CONDITIONS"


def test_weak_damping_refutes_conservation():
    params = dict(omega=2.0, alpha=0.0, gamma=0.008)
    result, _, _, _ = run_case("damped", params, True)
    assert result["initial_hypothesis_stress_verdict"] == "REFUTED"
    assert result["revised_verdict"] == "REFUTED"
