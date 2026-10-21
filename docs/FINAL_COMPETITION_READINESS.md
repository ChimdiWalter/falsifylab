# Final competition readiness

Date: 2026-10-21. Deadline: 2026-10-22, 19:00 CDT. This report records a final adversarial
review of the code, the evidence, the workbench and the submission text. The review did not
assume that the earlier audit or frontend was correct; its findings are listed in
`docs/INDEPENDENT_AUDIT.md` §8, and every one was reproduced before being accepted.

## Verdicts

| Area | Verdict | Basis |
|---|---|---|
| Scientific | **PASS**, after corrections | No fabricated data, leakage, or tuning on the final split. Nine MAJOR wording corrections applied (audit §4 and §8). |
| Reproducibility | **PASS** | 38 tests pass. The verifier recomputes all four evidence records. A 30-seed rerun reproduced 184 of 187 files byte for byte, including all 174 raw arrays. 22/22 independent checks pass. |
| Evidence integrity | **PASS, with disclosed caveats** | Frozen models re-derive exactly from pre-freeze raw data. Check P confirms that the published scientific modules match the SHA-256 recorded in every evidence record. The freeze is self-attested (development history not published), and two certificate-source runs carry a dirty-worktree flag. |
| Frontend | **PASS** | Browser QA 48/48 on desktop and mobile: zero console errors and zero failed requests, all links resolve, and the in-browser SHA-256 check matches. The live engine agrees with the Python engine on 1,500/1,500 parity checks. The marimo notebook passes its live UI test 5/5. |
| Protocol | **Unchanged** | The eight scientific modules are byte-identical to the protocol-freeze revision. |

**Release decision: READY FOR HUMAN REVIEW AND SUBMISSION.**

## What the submission may and may not claim

**May claim** (each backed by evidence in this repository):
- an auditable loop of counted experiments, counterexample, validity bracket, declared revision, freeze and independent audit;
- a 5.1 × 10⁻⁵ strain bracket, which is the design resolution, with 30/30 coverage at nominal noise;
- a 1,064.8 → 0.40 MPa audit error, reached equally by every sampling policy, which is the measurement floor;
- under noise, misses are never reported as settled, but abstention is blunt;
- the damped control is refused a conservation law;
- the noisy valid control is falsely refuted in 4/30 runs;
- the search-selected oscillator revision is never refuted but rarely confirmed, and a one-run largest-amplitude design ties it;
- byte-identical reruns.

**Must not claim:** new physics; physical yield estimation; statistical error control; first-of-kind falsification; superiority over SINDy, PySR, POPPER, SciExplorer or active learning; real-material validity; formal proof; that search caused the audit-error gain; or "zero silent misses" as a detection property.

## Judging estimates (1–5, evidence-based)

| Criterion | Estimate | Reasoning | Strength | Weakness | Highest-value improvement |
|---|---|---|---|---|---|
| Potential for impact | 2 (2–3) | A clear audit pattern for fitted constitutive models, demonstrated only on textbook simulators. | Reproducible, inspectable, with honest abstention and negative controls. | No real data. | Run one public tensile dataset through the observation interface. |
| Innovativeness | 2 | Bisection and a fixed catalog scan; the simple baselines and a one-run largest-amplitude design match the search. | Integrates freeze guard, ledger and three-way verdicts in one record. | Search adds little beyond obvious designs. | A screen-then-bisect policy that beats the baselines at equal budget. |
| Novelty | 2 | An integration of established components. | Counterexample-to-evidence record with built-in negative controls. | No capability that prior tools lack individually. | Head-to-head with Gaussian-process level-set estimation and SINDy on the same ledger. |
| Physical-science relevance | 3 | Real constitutive and conservation-law physics, two integrators, a derived energy balance. | Correct units and numerics, independently checked. | Revision families contain the truth. | A case with a wrong family (for example Voce hardening) to test refusal. |

These estimates are deliberately conservative; the entry's strength is credibility, not scale.

## Remaining risks

1. **Video.** Keep the final cut at 4:00 or under, at normal speed.
2. **Live workbench.** It needs GitHub Pages enabled (Settings → Pages → main, root). Until then, judges must run `python -m http.server` locally.
3. **Synthetic-only scope.** It is likely to cap the impact and relevance scores. The write-up states it plainly.
4. **Write-up length.** About one page plus figures; keep both figures optional if Moment renders long.
5. **Marimo track.** The notebook is genuinely used and tested; eligibility beyond "used their platform" is not specified in the public rules.

## Exact commands

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt
python -m pytest -q
python -m falsifylab.verify outputs
python -m falsifylab.benchmark --seeds 30 --out /tmp/bm        # about 1.5 min on a CPU
PYTHONPATH=. python audit/independent_checks.py
PYTHONPATH=. python audit/posthoc_controls.py
PYTHONPATH=. python audit/posthoc_oscillator_excitation.py
python site/build.py && node site/tests/engine_parity.mjs
python -m http.server   # open http://localhost:8000/site/index.html
pip install -r requirements-notebook.txt && python -m marimo run notebooks/explore.py
```

## Ready-to-post materials

- `submission/MOMENT_WRITEUP_FINAL.md` and `submission/figures/fig1_materials_counterexample.png` (cover).
- `submission/figures/fig2_noise_abstention.png`, `fig3_oscillator_revision.png`.
- `docs/JUDGE_QA.md`.

## Remaining human steps

1. Record the video, upload it to YouTube as Public, and paste the URL into Moment.
2. Optionally enable GitHub Pages and add the workbench URL to the write-up and the video description.
3. Paste the write-up, add the cover image, tick **Marimo** only (not Valency or Adaption), confirm the rules yourself, and submit before 19:00 CDT on 22 October 2026.
