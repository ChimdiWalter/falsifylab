# FalsifyLab — Where Scientific Laws Meet Counterexamples

A law can fit every observation you have and still fail outside the conditions where it was measured. FalsifyLab spends a counted experiment budget trying to break a candidate law, revises it only within a declared family, freezes the revision, and lets independent measurements decide. Every reading is exported as a hash-linked evidence record.

**Code:** https://github.com/ChimdiWalter/falsifylab · **Live workbench:** [GitHub Pages URL] · **Video:** [video URL]

## What we built

FalsifyLab is an open-source Python engine with a browser workbench and a marimo notebook. It runs on a CPU, and no language model judges a physical claim. The loop:

1. Fit a candidate law.
2. Spend counted experiments looking for counterexamples, and bracket where the law fails.
3. Revise within a predeclared family.
4. Freeze, with a code guard that blocks audit data until then.
5. Audit on new data.

Verdicts are *refuted*, *not refuted under tested conditions*, or *inconclusive*.

## Method

**Synthetic bilinear solid.** A Hooke slope is fitted from 40 low-strain readings. Bisection, a uniform grid and random sampling each get 10 probes × 4 readings to find where the law's error first exceeds 10 MPa. This is an operational onset, not yield. A frozen bilinear revision is then audited on 249 new readings.

**Oscillator.** A quadratic energy fitted on short, low-amplitude runs faces a 15-condition stress catalog. A quartic revision is audited on three new trajectories. Harmonic (valid law) and damped (no conservation law) controls run through the same pipeline.

## Results (synthetic)

**Material, 30 noise seeds.**
- Bisection brackets the onset to $5.1\times10^{-5}$ strain. This is its design resolution, 28× finer than an equal-budget grid, and the bracket covered the true onset in **30/30** runs at nominal noise.
- Revision cuts audit error from **1,064.8 to 0.40 MPa**, the measurement floor (0.37). Uniform and random sampling match it, so the gain comes from the declared family, not the search.
- Post-hoc, at 0.8–16 MPa noise, 38 of 426 brackets missed the onset. All of them fell where the engine abstained on every run, so none was reported as settled. Abstention is blunt: at 2 MPa bisection also abstained on 26/30 correct brackets.

**Oscillator.** These results come from one noise-free pipeline audited on 30 jittered final sets.
- The quadratic is refuted: 22% audit drift vs 0.6% in training.
- The quartic recovers $\omega^2=4.000$ and $\alpha/2=0.500$.
- The damped control is refused a conservation law.

**Oscillator under noise (post-hoc, 30 seeds).**
- The discovery-only quartic is refuted in 25/30 and 30/30 audits.
- The search-selected revision is never refuted, but it is confirmed in only 4/60 runs and inconclusive in the rest. One largest-amplitude run, without the 15-run search, does as well.
- At noise 0.01 the valid harmonic law is falsely refuted in 4/30 runs.

A rerun reproduced every raw array byte for byte, and all 38 tests pass.

*[Figure: submission/figures/fig1_materials_counterexample.png]*

## Judging criteria

- **Impact:** an audit pattern for fitted or learned constitutive models that reports where they stop working, and when the data cannot decide.
- **Innovativeness:** falsification, boundary finding, revision and audit share one counted, frozen ledger rather than a fit score.
- **Novelty:** each component has prior art (SINDy, PySR, POPPER, counterexample-guided synthesis, level-set estimation). The contribution is their integration into one re-executable record with negative controls and abstention.
- **Physical sciences:** materials constitutive behaviour and conservation laws, checked with two ODE solvers and the derived energy balance dQ/dt = −2γv².

## Limitations

The systems are synthetic, and the revision families contain the truth. Thresholds are uncalibrated, and the abstention rule is given the true noise level. Audits interpolate within the probed range. Bisection assumes monotonicity: with a hidden softening dip, both the bracket and the mean-error audit miss a 25 MPa local failure (reproducible). There is no real-alloy data and no comparison with mature discovery methods.
