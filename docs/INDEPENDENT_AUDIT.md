# Independent scientific audit of FalsifyLab

**Audited checkpoint:** `fdc32ec` (engineering build). Scientific acquisition, fitting and policy code
is byte-identical to the protocol-freeze commit `63c686c`; the committed benchmark was
generated at a clean `63c686c` tree.
**Date:** 2026-10-21. **Environment:** Python 3.12.3, Linux, `~/.venvs/lesegenv`.

This audit was run independently of the engineering reports. Every number below was
recomputed by the commands listed, not copied from `docs/ENGINEERING_REPORT.md`.

## Verdict

| Area | Verdict | Basis |
|---|---|---|
| A. Mathematical correctness | **PASS** | Symbolic derivation; closed-form onset; fit algebra re-derived |
| B. ODE and numerical solver | **PASS** | Independent implicit Radau integrator reproduces audit drifts to <1e-6 |
| C. Conservation-law equations | **PASS** | `dQ/dt = -2 gamma v^2` symbolic and numeric (energy balance to 2e-7 relative) |
| D. Units and physical quantities | **PASS** (minor note) | MPa, dimensionless strain, m, s, m/s, coefficient units consistent; noise allowance mixes units by design |
| E. Train/test separation, frozen partitions | **PASS** | Ledger order, freeze fingerprints, disjoint strains, models re-derived from pre-freeze raw data |
| F. Acquisition costs | **PASS** | 10 probes / 40 readings per policy in all 30 seeds; partition costs sum |
| G. Independent validation as claimed | **PASS, qualified** | Fresh measurements and RNG streams, but inside the probed domain (interpolation), and oscillator audits share one deterministic model |
| H. Counterexample-search behaviour | **PASS as described; INCONCLUSIVE as a general method** | Bisection works under its monotonic prior; a reproducible hidden-nonmonotonicity case defeats it silently |
| I. Model revision | **PASS** | Quartic recovers `omega^2 = 4`, `alpha/2 = 0.5` to 1e-10; bilinear refits exact |
| J. Raw data vs reported statistics | **PASS** | 184 of 187 benchmark files byte-identical on rerun (all 174 raw NPZ); the other 3 differ only in provenance fields |
| K. Noise and solver sensitivity | **PASS, sample too small** | Verdicts stable across tolerances; frozen noise subset is n=3; 30-seed post-hoc sweep added |
| L. Statistical limitations | **PASS on disclosure** | No calibrated error control exists and none is claimed; any such claim would fail |
| M. Novelty | **Integration contribution only** | See section 7; no first-of-kind or superiority claim is supportable |

**Overall scientific verdict: PASS for submission, with nine MAJOR wording corrections
(sections 4 and 8) that change how the results must be described, not what was measured.
Four of them (section 8) were found by a second, independent adversarial review after this
audit was first written.**
No BLOCKER was found: no fabricated data, no leakage of simulator truth into search or
fitting, no tuning on the final split, no silent protocol change.

## 1. Reproduction

| Command | Result | Log |
|---|---|---|
| `python -m pytest -q` | 34 passed (24.8 s) | `docs/logs/audit/pytest-fdc32ec.txt` |
| `python -m falsifylab.benchmark --seeds 30 --out audit_runs/benchmark_fdc32ec` | 81 s wall; 184 of 187 files byte-identical to committed `outputs/benchmark`, including every raw `.npz` (`docs/logs/audit/benchmark-rerun-comparison.txt`); `metrics.json` identical except provenance | `audit_runs/benchmark_fdc32ec.log` (scratch, not committed) |
| `python -m falsifylab.verify outputs` | VERIFIED 4 certificates | `docs/logs/audit/verify-fdc32ec.txt` |
| `python -m falsifylab --seeds 2 --out <tmp>` then `verify` | pass | `docs/logs/audit/smoke-seeds2.txt` |
| `PYTHONPATH=. python audit/independent_checks.py` | 22/22 checks pass | `docs/logs/audit/independent-checks-committed-benchmark.txt`, `audit/independent_checks.json` |
| `PYTHONPATH=. python audit/posthoc_oscillator_excitation.py` | see section 3.4 | `docs/logs/audit/posthoc-oscillator-excitation.txt`, `audit/posthoc_oscillator_excitation.json` |
| `git diff 63c686c fdc32ec -- falsifylab/{physics,hypothesis,decisions,experiments,materials,run_materials,run_demo,benchmark}.py` | empty | — |

Recorded source hashes in the committed results match current files except
`certificates.py` and `verify.py`, which were hardened after the freeze (disclosed).

## 2. Mathematics

**Energy balance.** For `x'' = -omega^2 x - alpha x^3 - gamma x'` and
`Q = v^2 + omega^2 x^2 + (alpha/2) x^4`:
`dQ/dt = 2v x'' + 2 omega^2 x v + 2 alpha x^3 v = 2v(-omega^2 x - alpha x^3 - gamma v) + 2 omega^2 x v + 2 alpha x^3 v = -2 gamma v^2`.
Verified with SymPy. Numerically (Radau, rtol 1e-12) for the damped control on the first
audit trajectory: `Q(T) - Q(0) = -0.6289232` vs `-2 gamma ∫v^2 dt = -0.6289234`.

**Invariant fit.** Fixing the `v^2` coefficient to 1 and centering within each trajectory
removes each trajectory's unknown energy constant: `v^2 - mean(v^2) = -a (x^2 - mean) - b (x^4 - mean)`.
Least squares on this is correct. Units: `a` in s^-2, `b` in m^-2 s^-2, `Q` in m^2/s^2.

**Materials onset (evaluator target).** With fitted slope `Ê` and the bilinear truth
(E, H, ε_y), the deviation past yield is `Ê ε - E ε_y - H (ε - ε_y)`. Setting it to 10 MPa:
`ε* = (10 + (E - H) ε_y) / (Ê - H)`. This matches the stored evaluator onset in all
30 seeds (max difference 4e-19). For the default material `ε* ≈ 0.002048`, i.e. about
4.8e-5 strain past the simulator's yield strain 0.002. **The reported boundary is a
10 MPa deviation onset of the fitted Hooke law, not the physical yield point.** The
code, figure labels and documents state this correctly.

**Bracket widths are design constants.** Active search spends 2 probes on the domain
ends [0.001, 0.014] and 8 on bisection, so every resolved active bracket has width
`0.013 / 2^8 = 5.078125e-5` (IQR exactly 0 across 30 seeds). Uniform spacing gives
`0.013 / 9 = 1.444e-3`. The "~28× narrower" ratio is `2^8 / 9 = 28.4`. It is
arithmetic, guaranteed whenever the monotonic prior holds and no probe is
misclassified. The empirical content is **coverage and abstention**, not width.

**Noise floor.** The audit compares predictions with means of 3 readings at SD 0.8 MPa.
A perfect model therefore has expected MAE `0.8/√3 · √(2/π) = 0.369 MPa`. The true
simulator scores a median of 0.371 MPa on the saved audit data. The revised models
score 0.401 (active), 0.403 (uniform) and 0.397 (random).

## 3. Experimental findings

### 3.1 Separation, costs and leakage
- Holdout events come after the model-freeze event in every record, and nothing
  non-holdout follows them. Holdout strains are disjoint from probe strains.
- Frozen models were **re-derived from the saved raw pre-freeze arrays** for all
  90 oscillator records and 30 materials records × 3 policies (exact agreement).
  `falsifylab.verify` does not do this; it checks metrics against frozen models only.
- Search and fitting receive an observation callable, the fitted slope and the
  public instrument SD. They never receive simulator coefficients. As a leakage
  probe, a different hypothetical material (E = 70 GPa, ε_y = 0.0045, H = 3 GPa)
  was run on 30 seeds. The active bracket relocated correctly (median midpoint offset
  < 1e-4 strain) and covered the new onset in 27/30. All 30 were flagged INCONCLUSIVE,
  so there were 0 silent misses.

### 3.2 Materials: what the 1,064.8 → 0.401 MPa result means
The improvement is real and reproducible, but it is **not attributable to active
search**. All three policies reach the same audit MAE, which is the measurement noise
floor (§2), because the predeclared bilinear family is the generating family. The
initial MAE is large because the audit spans strain up to 0.0138, about 7× the
yield strain: 71 of 83 audit strains lie past the onset. The audit interpolates inside
the probed domain [0.001, 0.014]. It is not an extrapolation test.

### 3.3 Materials under noise (post-hoc, 30 seeds per level, not part of frozen protocol)
`audit/independent_checks.py`, seeds 2026–2055:

| Noise SD (MPa) | Active covered | Active boundary INCONCLUSIVE | Uniform covered | Random covered | Silent misses (all policies) | Revised audit (all policies) |
|---:|---:|---:|---:|---:|---:|---|
| 0.8 | 30/30 | 0/30 | 30/30 | 30/30 | 0 | 30/30 not refuted |
| 2 | 30/30 | 26/30 | 30/30 | 30/30 | 0 | 30/30 not refuted |
| 4 | 28/30 | 30/30 | 30/30 | 30/30 | 0 | 30/30 not refuted |
| 8 | 17/29 | 30/30 | 29/29 | 29/29 | 0 | 30/30 INCONCLUSIVE |
| 16 | 2/23 | 30/30 | 24/24 | 19/22 | 0 | 30/30 INCONCLUSIVE |

("covered" counts evaluable brackets.) The narrow active bracket stays accurate up to
roughly 2–4 MPa noise and then degrades. Wide passive brackets keep covering because
they are wide. Every uncovered bracket was flagged INCONCLUSIVE, but see section 8: all
38 misses occurred where the engine abstained on *every* run, so this shows conservative
abstention, not discrimination between right and wrong brackets. The frozen 3-seed robustness subset reported active coverage
1/3 at 8 MPa. With 30 seeds it is 17/29 (59%), so the 3-seed figure is too small a
sample to quote as a rate.

### 3.4 Oscillator: is counterexample search needed?
Primary runs are **noise-free**. Discovery, search and revision are identical in all
30 seeds (one distinct frozen model per system); seeds only jitter the three audit
amplitudes by ±0.025 m. "30/30" therefore means one deterministic pipeline audited
on 30 slightly different final sets, not 30 independent trials. Noise-free, the
discovery-only quartic also recovers the invariant, as the engineering report disclosed.

Under instrument noise the conclusion changes. Post-hoc, 30 seeds, nominal horizon
(`audit/posthoc_oscillator_excitation.py`), quartic fitted on discovery plus one extra
501-sample trajectory chosen four ways:

| Extra trajectory | Noise 0.001: refuted / not refuted / inconclusive | median quartic coeff (true 0.5) | Noise 0.01: refuted / not / inconcl. | median quartic coeff |
|---|---|---:|---|---:|
| none (discovery only) | 25 / 0 / 5 | 0.462 (IQR 0.334–0.604) | 30 / 0 / 0 | −3.69 |
| counterexample search | 0 / 4 / 26 | 0.4997 | 0 / 0 / 30 | 0.494 |
| random catalog condition | 8 / 2 / 20 | 0.498 (IQR 0.487–0.503) | 14 / 0 / 16 | 0.362 |
| largest amplitude (1.7 m, 12 s) | 0 / 5 / 25 | 0.4999 | 0 / 0 / 30 | 0.491 |

The frozen robustness subset agrees (search-informed 0/12 refuted; discovery-only
10/12 refuted). **Conclusion:** under noise the search-selected excitation is what makes
the quartic identifiable, and it beats a random experiment. It does not beat the
obvious "use the largest available amplitude" design, which search always chose here.
The claim can be "search finds an informative, falsifying experiment". It cannot be
"search finds experiments a physicist would not". Under noise the verdict usually
abstains rather than survives.

### 3.5 Reproducible failure case: hidden nonmonotonicity
A bilinear material with a localized 25 MPa pre-yield softening dip at strain
0.0012–0.0016 (`DippedMaterial` in the audit script) puts the true first 10 MPa
exceedance near 0.00128. In 10/10 seeds, active bisection reported a resolved bracket
near 0.00205 **without** flagging nonmonotonicity: a silent miss. Uniform never
sampled the dip either; its bracket covered it only because the bracket is wide.
Random sampling hit it in 2 seeds and flagged nonmonotonicity once. This is the
documented monotonic-prior limitation, now with a concrete reproduction.

### 3.6 Solver
Tight (2e-11/1e-13) and loose (1e-7/1e-9) DOP853 settings give identical verdicts.
The Duffing quadratic drift (0.2214) exceeds revised-model numerical drift
(5e-11 to 3e-7) by more than five orders of magnitude. Radau reproduces DOP853
audit drifts to <1e-6.

## 4. Issues (severity, location, fix)

| ID | Severity | Issue | Required correction |
|---|---|---|---|
| M1 | MAJOR (claim) | "Median audit MAE improved 1,064.793 → 0.401 MPa" reads as a search result. All policies reach 0.40, the noise floor (0.37), because the revision family is the generating family. | Always pair the number with: "uniform and random policies reach the same error; the gain comes from the predeclared bilinear family; 0.37 MPa is the measurement floor." |
| M2 | MAJOR (claim) | The active bracket width is a design constant (`0.013/2^8`), reported as a median with IQR 0. | State it as the design resolution. Report coverage, abstention and silent-miss counts as the empirical result. |
| M3 | MAJOR (claim) | Oscillator "30/30" rates come from one deterministic noise-free pipeline. | Describe as "one noise-free discovery/search/revision, audited on 30 jittered final sets". |
| M4 | MAJOR (claim) | "Search is not necessary" (noise-free) is incomplete; under noise, discovery-only fails and search-selected excitation succeeds, though no better than a largest-amplitude design. | Report both regimes (§3.4) with the largest-amplitude caveat. |
| M5 | MAJOR (stats) | 8 MPa active coverage "1/3" comes from n=3. | Quote the 30-seed post-hoc sweep (17/29), labelled post-hoc, with 0 silent misses. |
| m1 | MINOR | `verify.py` does not re-derive frozen models from pre-freeze raw data. | Covered by `audit/independent_checks.py`; recommend porting the refit check into `verify.py`. |
| m2 | MINOR | Materials `boundary_status` reuses the hypothesis label `NOT_REFUTED_UNDER_TESTED_CONDITIONS` for a resolved bracket. | Display as "bracket resolved" in UI; rename in a future schema version. |
| m3 | MINOR | Nominal 100% coverage partly reflects where the default onset sits on the dyadic probe grid; a different material ends 30/30 INCONCLUSIVE at the same noise. | Mention when quoting coverage. |
| m4 | MINOR | Stale pre-v3 numbers (1,068.981 MPa, random 0.002139, 20.245%, "nine tests") in earlier unpublished planning notes and an untracked legacy root `demo.html`. | Excluded from the published repository; never quote them. |
| m5 | MINOR | The oscillator noise allowance applies one numeric SD to x (m) and v (m/s). | Disclosed heuristic; keep the disclosure. |
| m6 | MINOR | The notebook's exploratory oscillator audit reuses a v3 final condition (1.463 m, 0.239 m/s, 9.73 s). | Already disclosed in the notebook text; keep. |
| m7 | MINOR | In the damped control, catalog drifts at a given horizon tie to ~1e-10 (energy decay of a linear oscillator is amplitude-independent), so the "largest drift" revision trajectory is a numerical tie-break; DOP853 and RK4 pick different amplitudes. Verdicts are unaffected. | Note it; prefer a deterministic tie-break (e.g. largest amplitude) in a future version. |
| m8 | MINOR | `outputs/results.json` and `outputs/materials/results.json` (the certificate sources) record `git_worktree_dirty: true` at `63c686c`. All 14 recorded source SHA-256s equal the committed `63c686c` files, so the dirtiness was in non-source files; the 30-seed benchmark was generated from a clean tree, and its materials records are identical to `outputs/materials`. | Regenerate certificate sources from a clean tree when convenient; disclose until then. |
| F1 | FUTURE | Hidden nonmonotonicity defeats bisection silently (§3.5). | Hybrid design: a sparse uniform screen before bisection, plus "unsampled gap" reporting. |
| F2 | FUTURE | No comparison with GP level-set estimation, SINDy or PySR. | Add as baselines on the same ledger. |
| F3 | FUTURE | Thresholds and allowances are uncalibrated. | Calibrate by simulation; add sequential error control (as in POPPER). |

No issue requires a change to the scientific engine, the frozen protocol or committed
evidence before submission. The corrections are to wording, figures and the frontend.
These are applied in the published materials.

## 5. Specific questions from the brief

- **10 MPa onset vs yield:** described correctly everywhere in code and docs; derived in §2.
- **Monotonic benefit:** yes. All of the width advantage comes from bisection under a
  monotonic prior (§2). It fails silently when the prior is false (§3.5).
- **Equal budgets:** yes. 10 probes / 40 readings per policy per seed; common setup (40)
  and audit (249) counted separately.
- **Stronger noise invalidates brackets:** active brackets lose coverage from about
  4 MPa; all such cases are flagged INCONCLUSIVE (§3.3).
- **Quartic without search:** yes noise-free; no under 0.001–0.01 noise (§3.4).
- **Dependence on predefined families:** total. Both revisions choose from a single
  hand-specified family that contains the truth.
- **Certificates:** establish internal consistency (schema, partitions, freeze order,
  costs, raw-data hashes, recomputed metrics). They do not establish scientific truth
  or independent replication, and are not proofs. A self-consistent fabricated run
  would also verify; rerunning the deterministic benchmark (byte-identical here)
  is the stronger check.

## 6. Scientifically defensible claims

1. On a synthetic bilinear material, a counted 10-probe adaptive search brackets the
   10 MPa deviation onset of a fitted Hooke law to 5.1e-5 strain. That is 28× finer than
   equal-budget uniform sampling by design, and it covered the noiseless onset in
   30/30 nominal-noise trials.
2. When noise grows, the engine abstains rather than reporting false precision. Post-hoc,
   none of the 38 missed brackets (of 426, at 0.8–16 MPa) was reported as settled. The
   abstention is blunt: it also abstains on many correct brackets, and it is given the
   true noise SD.
3. A predeclared bilinear revision, frozen before an independent 249-reading audit,
   reduces audit MAE from 1,064.8 MPa to 0.40 MPa, the measurement floor. Equal-budget
   uniform and random policies achieve the same.
4. A quadratic invariant fitted on low-amplitude Duffing data is refuted by a fixed
   15-condition stress catalog. The quartic revision recovers the physical invariant
   (`ω² = 4`, `α/2 = 0.5`) and survives all noise-free audits. The same procedure
   correctly refuses to certify a conservation law for the damped control.
5. Under instrument noise, the counterexample-selected revision is never refuted where
   discovery-only fitting and random experiments often are. It is, however, confirmed in
   only 4/60 runs, and one largest-amplitude run with no search does equally well.
6. Every run is a deterministic, hash-linked record. An independent rerun reproduced
   all raw arrays byte-for-byte.

**Do not claim:** new physics or materials discovery; physical yield estimation;
statistical confidence or error control; first or only automated falsification
system; superiority over SINDy, PySR, POPPER, SciExplorer or active learning;
real-material validity; "proof" or "certification" in a formal sense.

## 7. Novelty relative to prior work

See `docs/CLAIM_NOVELTY_TABLE.md` (14 sources verified against publisher pages or Crossref). Summary: sparse and
symbolic equation discovery (SINDy, PySR, AI Feynman), invariant learning, agentic
falsification with error control (POPPER), LLM-driven physics exploration
(SciExplorer), counterexample-guided synthesis and CPS falsification, and active
level-set estimation already exist. FalsifyLab does not advance any one of them. Its
concrete, demonstrated contribution is a compact integration: counted interventions,
a validity boundary, a constrained revision, a model-freeze guard, an independent
audit, negative controls and abstention, all exported as one hash-linked,
re-executable evidence record. That is an engineering and reproducibility
contribution, and it should be presented that way.

## 8. Findings from the final adversarial review

A second reviewer with no shared context re-checked the final materials. Its findings were
reproduced here before acceptance (`audit/posthoc_controls.py` →
`audit/posthoc_controls.json`, log `docs/logs/audit/posthoc-controls.txt`).

| ID | Severity | Finding (verified) | Correction applied |
|---|---|---|---|
| R1 | MAJOR | The valid harmonic control is falsely refuted under 0.01 instrument noise in 4/30 runs (horizon ×0.5 and ×1) and 2/30 (×2), and is never confirmed. At 0.001 it is confirmed in 89/90. Earlier text said it was "inconclusive rather than falsely refuted". | All texts and the workbench now state the false-refutation rate. |
| R2 | MAJOR | "0 silent misses" came from blanket abstention: all 38 misses (of 426 evaluable brackets) fell in noise/policy cells where 30/30 runs abstained. At 2 MPa bisection abstained on 26/30 correct brackets. The rule is given the true noise SD. "450 noisier runs" included 90 at nominal noise. | Reworded everywhere as conservative, not discriminating, abstention; the counts are given. |
| R3 | MAJOR | On the hidden-dip material the frozen revision passes the mean-error audit for every policy (30/30 runs, MAE 0.66–0.81 MPa) while erring by up to 25.5 MPa locally against the hidden truth. A mean-error audit averages local failures away. | Limitations now name the audit, not only bisection; the live lab shows the worst local error when an audit passes. A max-error criterion is future work. |
| R4 | MAJOR | The excitation comparison is not budget-matched (search: 15 catalog runs + 1; largest amplitude: 1 run). The search-selected revision is confirmed in only 4/60 runs, and the old figure showed only the refuted share. | Figure 3 now shows stacked refuted/inconclusive/not-refuted outcomes; texts give the confirmation rate and the budget difference. |
| r5 | MINOR | The rerun count is 184 of 187 files, not 184 of 186: the checksum list differs too. | Corrected; comparison log committed. |
| r6 | MINOR | All audits are in-domain interpolation (strain 0.016–1.378% inside the probed 0.1–1.4%; oscillator audits inside the 1.7 m / 12 s catalog envelope). | Stated in the limitations. |
| r7 | MINOR | The freeze is self-attested; the development history is not published. | Stated in the judge Q&A. Check P verifies that the published scientific modules match the SHA-256 recorded in every evidence record. |
| r8 | MINOR | Workbench issues: stale test count shown, a wrong message when the onset lies below the probed range, a clipped column, colour-only line encoding, low-contrast small text, and a toolbar covering data on mobile. | Fixed and re-tested. |

Independent scores from that review (1–5): impact 2, innovativeness 2, novelty 2, relevance 3.
