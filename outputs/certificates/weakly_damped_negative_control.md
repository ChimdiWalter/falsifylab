# Evidence trace: weakly_damped_negative_control

Run `e9c66502633e65d34495f5f0` · schema 1.0.0 · seed 2026

**This record is not a formal mathematical or statistical proof.**

Candidate: `Q = v^2 + 3.978267 x^2`

Initial audit status: **REFUTED**

Revised audit status: **REFUTED**

Observed counterexamples: 10. All readings are stored and hashed.

First observed counterexample:

```json
[
  {
    "amplitude": 0.2,
    "horizon": 6.0,
    "relative_drift": 0.049827224825221596,
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
    "fit_rmse_m2_s2": 0.06517550227335608,
    "normalization": "coefficient of v^2 fixed to 1; center within each trajectory",
    "samples": 864,
    "scaled_condition_number": 7.919952625578511
  },
  "coefficients": {
    "quadratic": 4.036365474222589,
    "quartic": -0.08120499059972312
  },
  "expression": "Q = v^2 + 4.036365 x^2 + -0.081205 x^4",
  "heldout_status": "REFUTED",
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
| discovery | 3 | 726 | 336 |
| holdout | 3 | 3886 | 3426 |
| probe | 15 | 12030 | 11949 |
| revision | 1 | 1002 | 1409 |

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
      "first_observed_failure_m": null,
      "horizon_s": 2.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": 1.7,
      "nonmonotone": false
    },
    {
      "first_observed_failure_m": 0.2,
      "horizon_s": 6.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": null,
      "nonmonotone": false
    },
    {
      "first_observed_failure_m": 0.2,
      "horizon_s": 12.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": null,
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
  "training_drift": 0.0034005290908395397,
  "initial_holdout_relative_drift": 0.07702141663944385,
  "revised_holdout_relative_drift": 0.10388152610181607,
  "threshold": 0.02,
  "threshold_kind": "DEMONSTRATION_THRESHOLD",
  "ablations": {
    "full_pre_audit_simulator_calls": 19,
    "no_counterexample_search_quartic": "REFUTED",
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
