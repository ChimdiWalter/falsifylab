# Evidence trace: duffing_nonlinearity

Run `22f332ecd751c4d679e9d039` · schema 1.0.0 · seed 2026

**This record is not a formal mathematical or statistical proof.**

Candidate: `Q = v^2 + 4.031008 x^2`

Initial audit status: **REFUTED**

Revised audit status: **NOT_REFUTED_UNDER_TESTED_CONDITIONS**

Observed counterexamples: 12. All readings are stored and hashed.

First observed counterexample:

```json
[
  {
    "amplitude": 0.5,
    "horizon": 2.0,
    "relative_drift": 0.02345700894698942,
    "status": "REFUTED",
    "threshold": 0.02,
    "threshold_kind": "DEMONSTRATION_THRESHOLD",
    "uncertainty_allowance": 0.0,
    "uncertainty_kind": "uncalibrated conservative instrument-noise heuristic"
  }
]
```

Constrained revision:

```json
{
  "family": "v^2 + a*x^2 + b*x^4",
  "fit": {
    "degree": 4,
    "fit_rmse_m2_s2": 1.144301526310809e-10,
    "normalization": "coefficient of v^2 fixed to 1; center within each trajectory",
    "samples": 864,
    "scaled_condition_number": 8.068529097450531
  },
  "coefficients": {
    "quadratic": 4.000000000023097,
    "quartic": 0.49999999999973976
  },
  "expression": "Q = v^2 + 4.000000 x^2 + 0.500000 x^4",
  "heldout_status": "NOT_REFUTED_UNDER_TESTED_CONDITIONS",
  "failure": null,
  "fit_inputs": [
    "e0018"
  ],
  "frozen_before_holdout": true
}
```

Resource costs by partition:

| Partition | Simulator calls | Scalar readings | RHS evaluations |
|---|---:|---:|---:|
| discovery | 3 | 726 | 366 |
| holdout | 3 | 3886 | 7410 |
| probe | 15 | 12030 | 20238 |
| revision | 1 | 1002 | 3230 |

Validity and uncertainty:

```json
{
  "discovery_amplitudes_m": [
    0.12,
    0.2,
    0.27
  ],
  "discovery_horizon_s": 0.8,
  "sampled_grid": [
    {
      "first_observed_failure_m": 0.5,
      "horizon_s": 2.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": 0.2,
      "nonmonotone": false
    },
    {
      "first_observed_failure_m": 0.5,
      "horizon_s": 6.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": 0.2,
      "nonmonotone": false
    },
    {
      "first_observed_failure_m": 0.5,
      "horizon_s": 12.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": 0.2,
      "nonmonotone": false
    }
  ],
  "uncertainty": {
    "noise_sd_x_m_and_v_m_s": 0.0,
    "interpretation": "uncalibrated propagation allowance"
  },
  "warning": "finite grid cannot establish a continuous validity region"
}
```

Metrics:

```json
{
  "training_drift": 0.005922706734546034,
  "initial_holdout_relative_drift": 0.22142525131342197,
  "revised_holdout_relative_drift": 5.3706473298583903e-11,
  "threshold": 0.02,
  "threshold_kind": "DEMONSTRATION_THRESHOLD",
  "ablations": {
    "full_pre_audit_simulator_calls": 19,
    "no_counterexample_search_quartic": "NOT_REFUTED_UNDER_TESTED_CONDITIONS",
    "no_revision": "REFUTED",
    "no_search_fit_uses_discovery_only": true,
    "no_search_pre_audit_simulator_calls": 3
  }
}
```

Limitations:

- Synthetic textbook mechanics with nominal SI units
- Hand-specified degree-2/4 family and exhaustive fixed search
- Peak-to-peak drift depends on sample count, noise and horizon
- 2% threshold and uncertainty allowances have no statistical error guarantee
- A discovery-only quartic fit can succeed without stress search in a noiseless correctly specified problem

Reproduce:

`python -m falsifylab.run_demo`
