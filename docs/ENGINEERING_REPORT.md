# Engineering report

## Required engineering work

| P0 item | Status | Evidence |
|---|---|---|
| A — scientific audit and hardening | DONE | Exact reproduction of supplied results; guarded fits, units and excitation; damped energy balance; fresh frozen final split; noise/horizon checks and two solver settings |
| B — evidence certificates | DONE | Schema 1.0.0, four JSON/Markdown traces, raw NPZ files, source/artifact hashes, partitions, freeze guard, queue, costs, revisions, final audit and validation CLI |
| C — fair evaluation | DONE | 30 seeds, equal 10-probe/40-reading search budgets, medians/IQR, controls, noise robustness, no-revision/no-search ablations, coverage and inconclusive fractions |
| D — visible artifacts | DONE | Measured figures, local `outputs/demo.html`, evaluation report, README, four-minute storyboard and generated submission drafts |
| E — engineering gates | DONE | 34 tests pass in project and isolated environments; CLIs exercised; raw metrics recomputed; clean reproduction; desktop/mobile report and live marimo UI checked |

Optional marimo: DONE. `notebooks/explore.py` was actually executed programmatically
at stress/no-counterexample settings, and through its live UI experiment button.
Logs and real rendered previews are under `docs/logs/` and `outputs/`. The core
workflow remains independent of marimo. No Valency, Adaption or cloud AI integration
was used. No claim about sponsor-track eligibility is made.

## Commands and exact result locations

```bash
source ~/.venvs/lesegenv/bin/activate
python -m pytest -q
python -m falsifylab
python -m falsifylab.benchmark --seeds 30 --out outputs/benchmark
python -m falsifylab.make_report
python -m falsifylab.verify outputs
python -m falsifylab.submission
python -m falsifylab.package
```

Recorded test output (`docs/logs/final-tests.txt`):

```text
..................................                                       [100%]
34 passed in 33.62s
```

Isolated-environment test output (`docs/logs/clean-final-tests.txt`):

```text
..................................                                       [100%]
34 passed in 36.88s
```

Verification output (`docs/logs/final-verification.txt`):

```text
VERIFIED 4 certificates, all saved holdout metrics, raw-data checksums and frozen models
```

Full scientific stdout is saved in `docs/logs/final-benchmark.txt`,
`final-oscillator.txt`, and `final-materials.txt`. Both supplied original numeric
records reproduced exactly before changes; `baseline/` preserves them.

## Measured final result summary

- One synthetic bilinear material, seeds 2026–2055, nominal noise SD 0.8 MPa.
- Median empirical onset bracket: active **0.00005078125 strain**, uniform
  **0.00144444444**, random **0.00156088987**. All nominal empirical brackets
  covered the noiseless crossing for the fitted initial slope in these 30 trials.
- Active linear→bilinear median independent-audit MAE:
  **1064.7931676310984 → 0.40118620179648207 MPa**.
- Harmonic false refutation: **0/30**. Initial Duffing refutation and revised
  survival: **30/30** each. Damped initial and revised refutation: **30/30** each.
- The discovery-only quartic also survives **30/30** noiseless Duffing trials:
  this does not show counterexample search is necessary for model recovery.
- At 8 MPa noise, active empirical brackets cover the noiseless onset in **1/3**
  robustness trials. All policies' boundary and revised-audit verdicts abstain.
- Tight/loose DOP853 settings preserve verdicts; numeric drift of the revised
  Duffing invariant remains far below the quadratic physical failure.

Machine-readable metrics, CSV and all exact robustness/sensitivity settings:
`outputs/benchmark/metrics.json`, `metrics.csv`, `solver_sensitivity.csv`,
`protocol.json`. Generated tables and interpretation: `docs/EVALUATION.md`.

## Reproducibility and checkpoints

- Baseline checkpoint: `e64e06f`.
- Frozen numerical implementation/protocol checkpoint: `63c686c`.
- Final source/evidence checkpoint: run `git rev-parse HEAD`; the final bundle
  records that SHA in `bundle_manifest.json`. No remote repository is configured
  or published by this work.
- All eight scientific acquisition/fitting/policy modules match their recorded
  per-run SHA256s. Post-freeze work extended evidence validators, reporting,
  packaging and the exploratory notebook; it did not tune scientific policies,
  thresholds, candidate families or final-split definitions.
- The isolated clean environment reproduced all three primary oscillator records
  and the first two materials records and raw NPZ checksums **exactly**. The
  regular 30-seed materials command matches benchmark materials output.
- Locked 22-package runtime/test dependency closure tested on Python 3.12.3/Linux.
- The packaged archive includes all source, tests, raw evidence, figures, docs,
  historical results and unposted drafts, with per-file hashes. `.git`, virtual
  environments, runtime caches and the two original duplicate ZIPs are excluded.
- Clean extracted archive verification and a new no-Git CPU demo pass; exact
  output is saved in `docs/logs/package-verification.txt`.

## Known limits and pending independent work

Synthetic simplified physics only; one material per parameter set; predefined
revision families; monotonicity prior; no formal statistical error calibration,
multiple-testing guarantee, real measured alloy data or state-of-the-art comparison.
A surviving MAE audit is weaker than a pointwise error bound. Narrow brackets can
miss the target under noise, and unsampled nonmonotonicity can remain hidden.
Certificate verification establishes internal consistency, not independent
scientific replication or proof. Independent review: `docs/INDEPENDENT_AUDIT.md`.
The supplied legacy PDF generator had hard-coded old metrics; its original source
is preserved under `baseline/`, and the root entry point now refuses to mix those
numbers with new figures. The reviewed write-up is `submission/MOMENT_WRITEUP_FINAL.md`.
