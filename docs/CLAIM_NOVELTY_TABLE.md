# Prior work and the honest novelty boundary

Citations checked on 2026-10-21 against publisher pages or Crossref records.
This is a positioning note, not a systematic review.

## Verified citations

| Work | Capability it already establishes |
|---|---|
| Brunton, Proctor & Kutz, *Discovering governing equations from data by sparse identification of nonlinear dynamical systems* (SINDy), PNAS 113:3932 (2016), [doi:10.1073/pnas.1517384113](https://doi.org/10.1073/pnas.1517384113) | Sparse discovery of governing equations from a function library |
| Cranmer, *Interpretable Machine Learning for Science with PySR and SymbolicRegression.jl*, [arXiv:2305.01582](https://arxiv.org/abs/2305.01582) (2023); [pysr.ai](https://pysr.ai) | Open-ended symbolic regression |
| Huang, Jin, Li, Li, Candès & Leskovec, *Automated Hypothesis Validation with Agentic Sequential Falsifications* (POPPER), ICML 2025, [PMLR 267](https://proceedings.mlr.press/v267/huang25n.html) | Agentic sequential falsification with strict Type-I error control |
| Nägele & Marquardt, *Agentic Exploration of Physics Models* (SciExplorer), Phys. Rev. X 16, 031002 (2026), [link](https://journals.aps.org/prx/abstract/10.1103/xnqc-q6nt) | LLM agent explores unknown physical systems and recovers equations of motion and Hamiltonians |
| Solar-Lezama et al., *Combinatorial sketching for finite programs*, ASPLOS 2006, [doi:10.1145/1168857.1168907](https://doi.org/10.1145/1168857.1168907) | Counterexample-guided inductive synthesis: propose, find counterexample, refine |
| Annpureddy et al., S-TaLiRo, TACAS 2011, [doi:10.1007/978-3-642-19835-9_21](https://doi.org/10.1007/978-3-642-19835-9_21); Donzé, Breach, CAV 2010, [doi:10.1007/978-3-642-14295-6_17](https://doi.org/10.1007/978-3-642-14295-6_17) | Optimization-guided falsification of simulated systems against a specification |
| Gotovos, Casati, Hitz & Krause, *Active Learning for Level Set Estimation*, IJCAI 2013, [link](https://www.ijcai.org/Abstract/13/202) | Sample-efficient threshold-crossing estimation under noise, no monotonicity needed |
| Waeber, Frazier & Henderson, *Bisection Search with Noisy Responses*, SIAM J. Control Optim. 51:2261 (2013), [doi:10.1137/120861898](https://doi.org/10.1137/120861898) | Noisy bisection with convergence guarantees |
| Schmidt & Lipson, *Distilling Free-Form Natural Laws from Experimental Data*, Science 324:81 (2009), [doi:10.1126/science.1165893](https://doi.org/10.1126/science.1165893); Udrescu & Tegmark, AI Feynman, Sci. Adv. 6:eaay2631 (2020), [doi:10.1126/sciadv.aay2631](https://doi.org/10.1126/sciadv.aay2631) | Discovery of conserved quantities and physical laws from data |
| Liu & Tegmark, *Machine Learning Conservation Laws from Trajectories*, PRL 126:180604 (2021), [doi:10.1103/PhysRevLett.126.180604](https://doi.org/10.1103/PhysRevLett.126.180604); Greydanus et al., Hamiltonian Neural Networks, NeurIPS 2019, [arXiv:1906.01563](https://arxiv.org/abs/1906.01563) | Learning conservation laws / energy-conserving dynamics from trajectories |
| Flaschel, Kumar & De Lorenzis (EUCLID), CMAME 381:113852 (2021), [doi:10.1016/j.cma.2021.113852](https://doi.org/10.1016/j.cma.2021.113852); npj Comput. Mater. 8:91 (2022), [doi:10.1038/s41524-022-00752-4](https://doi.org/10.1038/s41524-022-00752-4) | Unsupervised discovery of interpretable elastic and plastic constitutive laws |
| Kusne et al., CAMEO, Nat. Commun. 11:5966 (2020), [doi:10.1038/s41467-020-19597-w](https://doi.org/10.1038/s41467-020-19597-w) | Closed-loop active learning on real materials instruments |
| King et al., Nature 427:247 (2004), [doi:10.1038/nature02236](https://doi.org/10.1038/nature02236); King et al., *The Automation of Science*, Science 324:85 (2009), [doi:10.1126/science.1165620](https://doi.org/10.1126/science.1165620) | Robot scientists that generate hypotheses, run experiments and reject hypotheses |
| Nosek et al., *The preregistration revolution*, PNAS 115:2600 (2018), [doi:10.1073/pnas.1708274114](https://doi.org/10.1073/pnas.1708274114) | Committing the analysis before seeing outcome data |

## Already established vs. concretely implemented here

| Already established in prior work | What FalsifyLab concretely implements and measures |
|---|---|
| Counterexample-guided refinement (CEGIS, S-TaLiRo, Breach) | A fixed 15-condition catalog scan, then a refit of a predeclared quartic with the worst counterexample. No formal specification or optimizing search. |
| Noise-aware threshold finding (level-set estimation, noisy bisection) | Plain bisection under a disclosed monotonic prior, compared at an equal 10-probe / 40-reading budget with uniform and random sampling. Every miss under noise is flagged INCONCLUSIVE (0 silent misses in 450 post-hoc trials), and a reproducible nonmonotone case shows where it fails silently. |
| Law and invariant discovery (SINDy, PySR, AI Feynman, Schmidt & Lipson, AI Poincaré, HNN, EUCLID) | Fixed two- and three-term families and a bilinear model containing the ground truth. **It discovers nothing new.** |
| Falsification with error control (POPPER) | A three-way verdict with heuristic abstention. No calibrated error control. |
| Agentic or robotic exploration (SciExplorer, Adam/Eve, CAMEO) | A deterministic local CPU pipeline. No LLM judges a physical claim. |
| Preregistration and provenance practice | A model-freeze guard enforced in code before any holdout acquisition, counted costs for every simulator call, SHA-256 hashes of raw arrays, a JSON-schema evidence record per run, and a verifier that recomputes metrics from raw data. An independent rerun reproduced all raw arrays byte for byte. |
| Negative controls (standard scientific practice) | Harmonic (valid law) and damped (no conservation law) controls run through the same pipeline. The damped control is correctly refused. |

## Honest positioning

FalsifyLab's contribution is an **integration**: one inspectable, re-executable record
that links a candidate law, counted interventions, an observed validity boundary, a
constrained revision, a frozen independent audit, negative controls and abstention.
No single component is new. On the hackathon rubric, the realistic novelty score is
in the 2–3 range ("a fresh combination" / "original tooling"), not a first-of-kind
claim.

Do **not** claim: first automated falsification system; new physical law; formal
proof; outperforming POPPER, PySR, SINDy, SciExplorer or active learning.
