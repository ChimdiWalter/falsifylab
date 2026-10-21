# Evidence trace: synthetic_bilinear_material

Run `455c914dd64a4a8d1c9261f1` · schema 1.0.0 · seed 2026

**This record is not a formal mathematical or statistical proof.**

Candidate: `stress = 209960.24 * strain`

Initial audit status: **REFUTED**

Revised audit status: **NOT_REFUTED_UNDER_TESTED_CONDITIONS**

Observed counterexamples: 7. All readings are stored and hashed.

First observed counterexample:

```json
[
  {
    "absolute_deviation_mpa": 2501.8978020563636,
    "mean_stress_mpa": 437.5455571499811,
    "rejected": true,
    "status": "REFUTED",
    "strain": 0.014,
    "stress_readings_mpa": [
      437.5135889725402,
      437.08402453699614,
      437.67061856958776,
      437.91399652080025
    ],
    "uncertainty_allowance_mpa": 9.96222568475837
  }
]
```

Constrained revision:

```json
{
  "family": "predeclared continuous bilinear",
  "fit": {
    "family": "continuous bilinear with nonnegative hardening <= elastic slope",
    "fit_observations": 10,
    "fit_rmse_mpa": 0.35178352713120686,
    "hardening_modulus_mpa": 1436.1990224249514,
    "status": "FITTED",
    "yield_strain": 0.0020019918033424814
  },
  "frozen_before_holdout": true,
  "fit_inputs": [
    "e0001",
    "e0002",
    "e0003",
    "e0004",
    "e0005",
    "e0006",
    "e0007",
    "e0008",
    "e0009",
    "e0010"
  ],
  "heldout_status": "NOT_REFUTED_UNDER_TESTED_CONDITIONS"
}
```

Resource costs by partition:

| Partition | Simulator calls | Scalar readings | RHS evaluations |
|---|---:|---:|---:|
| discovery | 1 | 40 | 0 |
| holdout | 1 | 249 | 0 |
| probe_active | 10 | 40 | 0 |
| probe_random | 10 | 40 | 0 |
| probe_uniform | 10 | 40 | 0 |

Validity and uncertainty:

```json
{
  "discovery_strain": [
    0.0002,
    0.0008
  ],
  "probed_strain": [
    0.001,
    0.014
  ],
  "operational_tolerance_mpa": 10.0,
  "empirical_boundary": [
    0.002015625,
    0.00206640625
  ],
  "uncertainty": [
    0.002015625,
    0.00206640625
  ],
  "boundary_status": "NOT_REFUTED_UNDER_TESTED_CONDITIONS",
  "interpretation": "observed error-tolerance boundary, not physical yield or a confidence interval"
}
```

Metrics:

```json
{
  "initial_holdout_mae_mpa": 1064.1159925465554,
  "revised_holdout_mae_mpa": 0.4078301071063974,
  "mae_uncertainty_allowance_mpa": 1.385640646055102,
  "threshold_kind": "DEMONSTRATION_THRESHOLD"
}
```

Limitations:

- One synthetic bilinear material; no real alloy measurements
- Preselected revision family; monotonic deviation assumption
- Empirical bracket need not cover noiseless onset; narrowness alone is not accuracy
- Instrument and slope uncertainty are heuristic, not calibrated sequential error control
- Revised audit status tests aggregate MAE against 10 MPa, not a pointwise error guarantee

Reproduce:

`python -m falsifylab.run_materials --seeds 30 --out outputs/materials`
