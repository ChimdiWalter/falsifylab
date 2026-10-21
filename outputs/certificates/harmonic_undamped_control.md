# Evidence trace: harmonic_undamped_control

Run `ef565c7681cf5c6702dc54c2` · schema 1.0.0 · seed 2026

**This record is not a formal mathematical or statistical proof.**

Candidate: `Q = v^2 + 4.000000 x^2`

Initial audit status: **NOT_REFUTED_UNDER_TESTED_CONDITIONS**

Revised audit status: **INCONCLUSIVE**

Observed counterexamples: 0. All readings are stored and hashed.

First observed counterexample:

```json
[]
```

Constrained revision:

```json
{
  "family": "v^2 + a*x^2 + b*x^4",
  "fit": null,
  "coefficients": null,
  "expression": null,
  "heldout_status": "INCONCLUSIVE",
  "failure": null,
  "fit_inputs": [],
  "frozen_before_holdout": true
}
```

Resource costs by partition:

| Partition | Simulator calls | Scalar readings | RHS evaluations |
|---|---:|---:|---:|
| discovery | 3 | 726 | 336 |
| holdout | 3 | 3886 | 3441 |
| probe | 15 | 12030 | 11994 |

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
      "first_observed_failure_m": null,
      "horizon_s": 6.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": 1.7,
      "nonmonotone": false
    },
    {
      "first_observed_failure_m": null,
      "horizon_s": 12.0,
      "interpretation": "finite grid only; no guaranteed continuous validity region",
      "last_observed_pass_m": 1.7,
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
  "training_drift": 1.2550844815665679e-10,
  "initial_holdout_relative_drift": 1.2444263050600548e-10,
  "revised_holdout_relative_drift": null,
  "threshold": 0.02,
  "threshold_kind": "DEMONSTRATION_THRESHOLD",
  "ablations": {
    "full_pre_audit_simulator_calls": 18,
    "no_counterexample_search_quartic": "NOT_REFUTED_UNDER_TESTED_CONDITIONS",
    "no_revision": "NOT_REFUTED_UNDER_TESTED_CONDITIONS",
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
