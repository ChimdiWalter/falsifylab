# FalsifyLab

**Where scientific laws meet counterexamples.** A law can fit every observation you have
and still fail outside the conditions where it was measured. FalsifyLab spends a counted
experiment budget trying to break a candidate physical law, revises it only within a
declared family, freezes the revision, and lets independent measurements decide. Every
reading is kept as hash-linked evidence.

It runs on two synthetic laboratories: a bilinear stress–strain material and a set of
oscillators (harmonic, Duffing, damped). It is a scientific-computing prototype. It does
not discover new physics, and its evidence records show reproducibility, not proof.

![Synthetic material: ten probes find where Hooke's law fails; a frozen revision is audited](submission/figures/fig1_materials_counterexample.png)

**Key results (synthetic, see [`docs/INDEPENDENT_AUDIT.md`](docs/INDEPENDENT_AUDIT.md)):**

- **Bracket.** Ten adaptive probes bracket where Hooke's law first errs by 10 MPa, to
  5.1 × 10⁻⁵ strain. That is the design resolution of bisection; the bracket covered the
  true onset in 30/30 seeds at nominal noise.
- **Revision.** A frozen bilinear revision cuts independent audit error from 1,064.8 to
  0.40 MPa, the measurement floor. Simpler sampling policies reach the same value.
- **Oscillator.** A quadratic energy is refuted on a Duffing oscillator, and the quartic
  revision recovers the true invariant. The damped control is refused a conservation law.
- **Failures, all reproducible:**
  - Under heavy noise the engine abstains, bluntly.
  - At the highest noise, the valid harmonic law is falsely refuted in 4/30 runs.
  - A hidden softening dip fools both bisection and the mean-error audit.

## Quick start

You need **Python 3.12** (3.11 or newer should work; tested on 3.12.3). A CPU is enough:
no GPU, API key or account is needed. Node.js 18 or newer is optional, for one browser
test.

```bash
git clone https://github.com/ChimdiWalter/falsifylab.git
cd falsifylab
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-lock.txt # exact tested versions (or: requirements.txt)

python -m pytest -q                  # 38 tests, about 30 s
python -m falsifylab.verify outputs  # recompute every saved metric from the raw data
```

The last command should print
`VERIFIED 4 certificates, all saved holdout metrics, raw-data checksums and frozen models`.

**Open the interactive workbench** (charts, live experiments and the evidence viewer):

```bash
python -m http.server 8000           # from the repository root
```

Then open <http://localhost:8000/site/index.html>. If port 8000 is busy, use any other
number, for example `python -m http.server 8765` and `http://localhost:8765/site/index.html`.
Opening the HTML file directly also works, but the in-browser hash check needs a server.

**Open the marimo notebook**, which reruns the real Python engine interactively:

```bash
pip install -r requirements-notebook.txt
python -m marimo run notebooks/explore.py
```

**Run experiments yourself**, writing to a new folder so the committed evidence is left
untouched:

```bash
python -m falsifylab --seeds 2 --out runs/demo        # quick demo, about 10 s
python -m falsifylab.verify runs/demo
python -m falsifylab.benchmark --seeds 30 --out runs/benchmark   # full benchmark, 2 min or more
```

`runs/demo/demo.html` is an offline report. The full benchmark reproduces the committed
`outputs/benchmark` files; only provenance fields such as timestamps differ.

## Repository map

| Path | What it is |
|---|---|
| `falsifylab/` | The engine: simulators, fits, decisions, counted experiment ledger, evidence records, verifier |
| `outputs/` | Committed evidence: raw arrays (`.npz`), results, four evidence records, benchmark metrics |
| `site/` | Static browser workbench and its tests (`site/tests/`) |
| `notebooks/` | Reactive marimo notebook and its helpers |
| `audit/` | Independent checks and post-hoc experiments with their JSON results |
| `docs/` | Protocol, frozen evaluation, independent audit, judge Q&A, logs and screenshots |
| `submission/` | One-page write-up and figures generated from the evidence |
| `tests/` | Test suite |
| `baseline/` | The original prototype and its results, preserved for comparison |

## Reproduce the full evaluation in place

These commands regenerate the committed evidence inside `outputs/`, changing only
timestamps and provenance:

```bash
python -m falsifylab.benchmark --seeds 30 --out outputs/benchmark
python -m falsifylab.make_report
python -m falsifylab.verify outputs
PYTHONPATH=. python audit/independent_checks.py
python site/build.py          # rebuild the workbench data bundle
node site/tests/engine_parity.mjs   # optional: browser engine vs Python (Node 18+)
```

Individual workflows remain available: `python -m falsifylab.run_demo`,
`python -m falsifylab.run_materials --seeds 30 --out outputs/materials`.
Final aggregate numbers, quartiles, budgets, controls, ablations, solver sensitivity and
observed failures are in [`docs/EVALUATION.md`](docs/EVALUATION.md). Machine-readable
records are in [`metrics.json`](outputs/benchmark/metrics.json) and
[`metrics.csv`](outputs/benchmark/metrics.csv). All seeds and robustness settings are
predeclared in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Scientific workbench (browser)

[`site/index.html`](site/index.html) is a static workbench. Serve the repository root
(`python -m http.server`) and open `/site/index.html`, or enable GitHub Pages on the
repository root; the root `index.html` redirects there. Panels are labelled:

- **Live**: computed in your browser by `site/assets/engine.js`, a JavaScript port of the
  engine. `node site/tests/engine_parity.mjs` replays recorded Python runs through it;
  1,500/1,500 checks match. Live runs are exploratory.
- **Recorded**: replays of committed evidence, bundled by `python site/build.py` with the
  SHA-256 of every input file.
- **Post-hoc**: the independent audit's extra experiments, which are not part of the frozen protocol.

Browser QA (`site/tests/browser_qa.py`, Playwright) covers controls, desktop and mobile
layouts, console errors, links and in-browser hash verification. Screenshots are in
`docs/screenshots/`.

## Independent review

[`docs/INDEPENDENT_AUDIT.md`](docs/INDEPENDENT_AUDIT.md) reproduces the
benchmark: 184 of 187 files byte-identical, including every raw array. It re-derives the
mathematics and frozen models and adds post-hoc experiments. Read the headline numbers
with its corrections:

- **Bracket width.** The 5.1e-5 strain active bracket is bisection's design resolution
  (0.013/2^8).
- **Audit error.** All three policies reach the same ~0.40 MPa audit error, the
  measurement floor (0.37 MPa). That gain comes from the declared bilinear family, not
  from the search.
- **Noise.** Under heavier noise the active bracket loses coverage (17/29 at 8 MPa over
  30 seeds). All 38 post-hoc misses fell where the engine abstained on every run. That
  abstention is blunt: it also abstains on many correct brackets, and it is given the true
  noise SD.
- **False refutation.** At 0.01 instrument noise the valid harmonic law is refuted in 4/30 runs.
- **Local failures.** With a hidden softening dip, both bisection and the mean-error audit miss a
  25 MPa local failure. Audits interpolate inside the probed range.
- **Oscillator seeds.** Primary runs are one deterministic noise-free pipeline audited on
  30 jittered final sets.
- **Search under noise.** The discovery-only quartic fails; the search-selected revision is
  never refuted but is mostly inconclusive (confirmed in 4/60 runs), and one largest-amplitude
  run without search does as well.
- **History.** The development history is not published. Commit identifiers in the documents
  refer to it; each evidence record's source SHA-256 hashes match the published files.

Judge-facing answers: [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md). Prior work:
[`docs/CLAIM_NOVELTY_TABLE.md`](docs/CLAIM_NOVELTY_TABLE.md).

## What the experiments mean

**Materials.** A synthetic continuous bilinear response stands in for idealized
uniaxial loading. Discovery fits a zero-intercept Hookean slope at low strains.
The boundary is where absolute prediction error exceeds **10 MPa**. This
operational deviation onset differs from physical yield. Adaptive bisection,
uniform and random sampling share discovery data and receive **10 probes / 40
stress readings each**. Setup (40 readings) and final audit (249 readings) are
counted separately. A preselected bilinear family is fitted from observations;
simulator coefficients are available only to the laboratory and evaluator.
Random locations and measurement noise have independent RNG streams.

Boundary width, noiseless-target coverage and abstention are all reported.
Revised audit status compares aggregate MAE with 10 MPa; it is weaker than a
pointwise bound at every strain. The active empirical bracket can be narrow and wrong at higher noise. The
uncertainty-aware observed interval is also **not a confidence interval**.
Bisection assumes one pass-to-fail transition; unsampled nonmonotonicity may be
missed. Repeated seeds represent one material, not independent physical specimens.

**Mechanics.** The environment solves `x''=-omega²x-alpha*x³-gamma*x'` using DOP853.
Nominal units: x in m, time in s, velocity in m/s. The fitter only sees observed
state pairs, fitting `Q=v²+a*x²` then optionally `Q=v²+a*x²+b*x⁴`. Each trajectory
is centered separately. For gamma=0 the physical scaled energy is
`v²+omega²*x²+(alpha/2)*x⁴`; its derivative with damping is `-2*gamma*v²`.
The energy-balance test checks this independently using integrated dissipated power.

A fixed 15-condition amplitude/horizon catalog challenges the quadratic law;
a selected additional trajectory supports revision. Models freeze before three
new final trajectories are acquired. Ledger costs include all discovery, search,
revision, audit calls, state readings, simulated time and ODE RHS evaluations.
The amplitude boundary is a finite observed grid, not a continuous validity guarantee.

The oscillator **2% peak-to-peak/mean-absolute-level drift threshold** is a
`DEMONSTRATION_THRESHOLD`, not a p-value. Instrument-noise allowances provide
conservative heuristic abstention, without formal coverage or error control.
Valid harmonic and damped failure controls, two solver tolerances, noise/horizon
checks and a discovery-only quartic ablation are included. The latter also fits
the noiseless Duffing invariant: these experiments do not establish that search
is needed for recovery in a correctly specified richer family.

## Inspect and independently recompute the evidence

- [`outputs/certificates/oscillator.json`](outputs/certificates/oscillator.json)
  and [`readable trace`](outputs/certificates/oscillator.md).
- [`outputs/certificates/materials.json`](outputs/certificates/materials.json)
  and [`readable trace`](outputs/certificates/materials.md).
- [`falsifylab/schema.json`](falsifylab/schema.json) defines evidence schema 1.0.0.
- Each certificate has run ID, UTC timestamp, seed, Git/source hashes, dependencies,
  units, domain, uncertainty, disjoint partitions, frozen models, complete queue,
  resource costs, counterexamples, revision, final audit, artifact hashes and limits.
- Raw arrays are portable `.npz` files; load with `numpy.load(..., allow_pickle=False)`.
  `falsifylab.verify` recomputes probe/audit metrics from these arrays, verifies
  source-linked certificate metrics, frozen models, partitions, counts and hashes.

Statuses are `REFUTED`, `NOT_REFUTED_UNDER_TESTED_CONDITIONS` and `INCONCLUSIVE`.
A missing counterexample or surviving audit never proves a law. Invalid data,
degenerate trajectories, incompatible units, unidentifiable fits and contradictory
brackets are rejected or explicitly inconclusive. Every attempted logged simulation,
including failures, is counted. There are no automatic retries or cloud calls.

## Architecture

| Module | Responsibility |
|---|---|
| `physics.py`, `materials.py` | Numerical laboratories, observation-only constrained fits |
| `hypothesis.py`, `decisions.py` | Fixed polynomial family, guarded metrics and abstention |
| `experiments.py` | Counted queue, partitions, raw readings, model-freeze guard |
| `run_demo.py`, `run_materials.py` | Actual scientific workflows and figures |
| `benchmark.py` | Equal-budget trials, controls, robustness, ablations, CSV/JSON |
| `certificates.py`, `verify.py` | Schema, provenance, checksums and raw-data recomputation |
| `make_report.py`, `submission.py` | Offline viewer and drafts generated from results |

## History, limitations and related work

The original ten tests and both supplied benchmarks reproduced exactly. Original
outputs are preserved in [`baseline/`](baseline/). V1 and development V2 holdouts
are development data; V3 uses a newly frozen final split and independent streams.
Changed final numbers reflect those declared changes, not a silent rewrite of
historical results.

There is no real-material validation, unrestricted equation discovery, trained AI
agent, calibrated hypothesis test, state-of-the-art comparison, or demonstrated
first-invention claim. The proposed contribution is an inspectable integration of
existing ideas. Primary-source attribution and distinctions appear in
[`docs/RELATED_WORK.md`](docs/RELATED_WORK.md), covering SINDy, PySR, POPPER and
SciExplorer. Independent review: [`docs/INDEPENDENT_AUDIT.md`](docs/INDEPENDENT_AUDIT.md).

## Reports and submission materials

- Engineering report: [`docs/ENGINEERING_REPORT.md`](docs/ENGINEERING_REPORT.md)
- Independent audit: [`docs/INDEPENDENT_AUDIT.md`](docs/INDEPENDENT_AUDIT.md)
- Frozen evaluation: [`docs/EVALUATION.md`](docs/EVALUATION.md)
- Answers to judging questions: [`docs/JUDGE_QA.md`](docs/JUDGE_QA.md)
- Submission write-up and figures: [`submission/`](submission/README.md)

`python -m falsifylab.submission` regenerates an automatic draft (`submission/MOMENT_WRITEUP_GENERATED.md`, not tracked);
`python submission/make_figures.py` regenerates the figures from the evidence files.
No publication or competition submission is performed by this software.

Released under the [MIT License](LICENSE).

## The marimo notebook

```bash
pip install -r requirements-notebook.txt
python -m marimo run notebooks/explore.py
```

The notebook is reactive. Each control reruns the actual engine
(`falsifylab.run_materials.run`, `falsifylab.run_demo.run_case`) with unchanged thresholds,
budgets and families:

- Materials: choose the hidden material (including a nonmonotone softening-dip case),
  the instrument noise and the seed.
- Oscillator: choose the system, noise and horizon factor.
- Your own Duffing stress amplitude: a low-amplitude probe can find no counterexample and
  decline revision.

Runs are exploratory, not new untouched holdouts. The oscillator audit reuses the v3 final
conditions. Helpers live in `notebooks/exploration.py`, tested by
`tests/test_notebook_exploration.py`. `site/tests/marimo_ui_qa.py` drives `marimo run` in
a browser and checks that controls rerun the engine (log in
`docs/logs/audit/marimo-ui-qa.txt`). The default demo and tests do not require marimo.

Create a portable local bundle with `python -m falsifylab.package`. It verifies
evidence first, writes `dist/FalsifyLab_bundle.zip`, and includes a per-file
checksum manifest and Git checkpoint. No hosting or publication occurs.

## Troubleshooting

- **`Address already in use`** when starting the web server: another program uses that
  port. Pick another number (`python -m http.server 8765`) and use it in the address.
- **Remote machine, for example over VS Code Remote-SSH:** forward the port in the VS Code
  *Ports* tab (*Add Port*), then open the same `localhost` address on your own computer.
- **`ModuleNotFoundError: falsifylab`:** run commands from the repository root, with the
  virtual environment active.
- **Python version errors when installing:** use Python 3.12. The lock file pins
  NumPy 2.4 and SciPy 1.16, which need Python 3.11 or newer.
