# Related work and scope of the contribution

Primary sources checked on 2026-10-21. This is a limited positioning note,
not a systematic novelty review or a head-to-head performance comparison.

| Work | Established capability | What this prototype does and does not add |
|---|---|---|
| [Brunton, Proctor & Kutz, PNAS 2016 / SINDy](https://doi.org/10.1073/pnas.1517384113), [author preprint](https://arxiv.org/abs/1509.03580) | Sparse identification of dynamical equations from a feature library and observations | Uses predeclared families and focuses on challenge/revision/audit traces; does not introduce sparse dynamical discovery |
| [PySR official documentation](https://pysr.ai/v2.7.1/) | Configurable symbolic regression using an evolutionary search engine | Does not implement or surpass general symbolic search; the polynomial and bilinear families here are fixed |
| [Huang et al., POPPER, ICML 2025](https://proceedings.mlr.press/v267/huang25n.html) | Agentic sequential falsification with formal Type-I error control | Records physically grounded counterexamples, validity and reproducibility, but supplies no comparable formal error control |
| [Nägele & Marquardt, Agentic Exploration of Physics Models, PRX 16, 031002, 8 July 2026](https://journals.aps.org/prx/abstract/10.1103/xnqc-q6nt) | SciExplorer uses LLM tool use to investigate initially unknown physical systems and recover equations/Hamiltonians | Provides a small deterministic local audit workflow; does not match the paper's broad autonomous exploration claims |

The proposed engineering contribution is the integration of counted interventions,
finite validity reporting, constrained revision, independent evaluation and portable
machine-readable evidence. This integration is not established as novel or superior
by the current synthetic evaluation. It may be useful as a compact, auditable
teaching or research-prototyping instrument.

The noiseless oscillator ablation is especially important: a discovery-only quartic
fit already succeeds. Materials bisection has a structural monotonicity advantage;
its narrow bracket can under-cover the target when noise increases. Neither result
justifies a general active-learning or discovery-performance claim.

No SINDy/PySR/POPPER/SciExplorer package or online model was used to produce the
numerical results. References give scientific context, not sponsor eligibility.
