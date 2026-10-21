# Predeclared final protocol v3 — 2026-10-21

The supplied v1 holdout and v2 implementation smoke tests are development data.
The v3 final split below is frozen in source before the full 30-seed run. It was
chosen to remain within the original test domain, independently of model errors.
No model hyperparameter, selection policy, threshold or candidate family will be
tuned on these final observations. Bug fixes must be disclosed and rerun.

- Primary noise seeds: integers 2026–2055. These are repeated observations of one
  material and three textbook dynamical systems, not 30 independent materials.
- Oscillator discovery: three low-amplitude trajectories. Exhaustive catalog:
  five amplitudes × three horizons, 401 state pairs each. One extra 501-pair
  trajectory may support a quartic revision. Common audit: three new trajectories.
- Final oscillator base tuples `(amplitude m, velocity m/s, horizon s, samples)`:
  `(1.463,.239,9.73,641)`, `(1.613,-.173,11.57,733)`,
  `(1.243,.359,8.13,569)`. Amplitudes have predeclared uniform ±.025 m jitter
  from `SeedSequence([seed,17391])`. Observation noise uses a different namespace.
- Materials discovery: 8 strains .0002–.0008 × 5 replicates = 40 readings.
  Each policy gets 10 strain probes × 4 readings = 40. Random selection and
  measurement noise have independent generators; initial elastic fit is shared.
- Final material audit: 83 strains from .000161 to .013781, 3 readings each =249.
  Revised models for all three policies are frozen before this shared audit.
- Thresholds: dimensionless peak-to-peak invariant drift .02; stress deviation
  10 MPa. Both are demonstration/engineering tolerances, not significance tests.
- Robustness subset: first 3 seeds; oscillator instrument SD .001/.01 in nominal
  m and m/s, observation-horizon factors .5/2. Materials noise SD 0/.8/8/80 MPa.
- Solver sensitivity: DOP853 `rtol=2e-11,atol=1e-13` and `rtol=1e-7,atol=1e-9`.
  All other settings and final initial conditions match.
- Negative control: gamma=.008 dissipates scaled energy; quartic fitting must
  not be called a successful conservation-law repair if it fails the final audit.
- Ablations: no revision retains initial fit; materials no search retains Hooke
  fit. Oscillator no search fits the same quartic family on discovery alone.
  The latter may succeed: this is a disclosed weakness of the discovery story.
- Report medians, quartiles, control refutation rates, abstention, empirical
  boundary width and coverage of the noiseless crossing for the fitted initial
  slope. No best-seed selection; failures and missing brackets remain visible.
- For ambiguous branches or contradictory observations, the empirical bracket
  cannot be interpreted as an uncertainty interval. A separate conservative
  observed bracket and `INCONCLUSIVE` status record that limitation.

Models cannot acquire holdout data until frozen. The ledger refuses subsequent
fitting/search acquisition. Raw arrays, experiment settings, costs, source hashes
and all final predictions are saved; `falsifylab.verify` recomputes the metrics.

Engineering checks of controls after evaluation do not constitute model tuning.
No claim of formal statistical calibration, real-material accuracy or superiority
over SINDy, PySR, POPPER, SciExplorer or active-learning methods is made.
