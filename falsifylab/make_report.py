"""Build a static, offline evidence viewer from the actual stored runs."""
from __future__ import annotations
import argparse
from html import escape
import json
import os
from pathlib import Path
from .artifacts import digest
from .certificates import build, artifact, write_certificate

sha256 = digest


def generate(osc_file: Path, mat_file: Path, out_html: Path, certificates_dir: Path,
             benchmark_file: Path | None = None):
    oscillator = json.loads(osc_file.read_text())
    materials = json.loads(mat_file.read_text())
    certificates_dir.mkdir(parents=True, exist_ok=True)
    root = Path(os.path.commonpath([osc_file.resolve().parent, mat_file.resolve().parent,
                                   certificates_dir.resolve(), out_html.resolve().parent]))
    benchmark = json.loads(benchmark_file.read_text()) if benchmark_file and benchmark_file.exists() else None
    sensitivity = ({'status': 'MEASURED', 'records': benchmark['solver_sensitivity']}
                   if benchmark is not None else None)
    certificates = []
    for record in oscillator['cases']:
        slug = 'oscillator' if record['system'] == 'duffing_nonlinearity' else record['system']
        path = certificates_dir / f'{slug}.json'
        doc = build(record, osc_file, osc_file.parent / record['raw_artifact'], path,
                    oscillator['software'], sensitivity=sensitivity)
        if benchmark is not None:
            doc['artifacts'].append(artifact(benchmark_file, path, 'benchmark_sensitivity'))
        if slug == 'oscillator':
            doc['artifacts'].append(artifact(osc_file.parent / 'duffing_counterexample.png', path, 'figure'))
        write_certificate(doc, path, artifact_root=root)
        certificates.append(path)
    path = certificates_dir / 'materials.json'
    material_example = materials['records'][0]
    doc = build(material_example, mat_file, mat_file.parent / material_example['raw_artifact'], path,
                materials['software'], materials=True)
    doc['artifacts'].append(artifact(mat_file.parent / 'stress_strain_boundary.png', path, 'figure'))
    write_certificate(doc, path, artifact_root=root)
    certificates.append(path)
    c = next(r for r in oscillator['cases'] if r['system'] == 'duffing_nonlinearity')
    def link(path):
        return escape(os.path.relpath(path, out_html.parent).replace(os.sep, '/'), quote=True)
    def fmt(value, spec='.6g'):
        return 'inconclusive' if value is None else format(value, spec)
    rows = ''.join(f"<tr><td>{name}</td><td>{fmt(s['median_bracket_width_strain'])}</td>"
                   f"<td>{fmt(s['bracket_width_summary']['q25'])}–{fmt(s['bracket_width_summary']['q75'])}</td>"
                   f"<td>{fmt(s['reference_onset_coverage_fraction'], '.1%')}</td>"
                   f"<td>{fmt(s['inconclusive_boundary_fraction'], '.1%')}</td></tr>"
                   for name, s in materials['methods'].items())
    control_rows = ''.join(f"<tr><td>{escape(r['system'])}</td><td>{fmt(r['heldout_initial_relative_drift'], '.3%')}</td>"
                          f"<td>{escape(r['initial_hypothesis_stress_verdict'])}</td>"
                          f"<td>{escape(r.get('revised_verdict', 'NOT_ATTEMPTED'))}</td></tr>"
                          for r in oscillator['cases'])
    certlinks = ''.join(f'<li><a href="{link(p)}">{escape(p.stem)} JSON</a> · <a href="{link(p.with_suffix(".md"))}">readable trace</a></li>' for p in certificates)
    benchmark_html = ''
    if benchmark is not None:
        benchmark_html = f'''<section><p class="eyebrow">Controls and robustness</p><h2>Evidence includes the weak points.</h2>
<img src="{link(benchmark_file.parent / 'comparison.png')}" alt="Equal-budget comparison and independent model audit">
<p>Primary benchmark: {benchmark['seed_count']} seeds. Noise/horizon checks and two solver tolerances are recorded separately.
The discovery-only quartic ablation can already succeed in the noiseless oscillator: search is useful for exposing the quadratic failure, but is not necessary for fitting this correctly specified richer family.</p>
<p><a href="{link(benchmark_file)}">All metrics and failures</a> · <a href="{link(benchmark_file.parent / 'solver_sensitivity.csv')}">Solver sensitivity table</a></p></section>'''
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FalsifyLab | Where a law fails</title><style>
:root{{font-family:system-ui,sans-serif;background:#f3f1e9;color:#1b3436}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1100px;margin:auto;padding:35px 25px 70px}}header{{padding:40px 0}}h1{{font-size:clamp(54px,8vw,92px);letter-spacing:-.06em;margin:8px 0}}h2{{font-size:clamp(26px,4vw,36px);letter-spacing:-.035em}}p{{line-height:1.65;max-width:850px}}.lead{{font-size:22px}}.eyebrow{{color:#306c62;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:750}}section{{background:white;border:1px solid #d9dfd6;border-radius:16px;padding:28px;margin:18px 0 28px}}.cards{{display:flex;gap:15px;flex-wrap:wrap;margin:25px 0}}.card{{background:#e9f2eb;padding:18px;border-radius:12px;flex:1;min-width:210px}}.card strong{{font-size:30px;display:block;margin:8px 0}}.note{{border-left:4px solid #d7953e;padding-left:16px;color:#4e5146}}img{{width:100%;height:auto;border-radius:7px}}a{{color:#236258}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:12px 8px;text-align:left;border-bottom:1px solid #dfe6de}}.scroll{{overflow:auto}}code{{background:#ecf0e9;padding:3px 6px;border-radius:4px}}footer{{font-size:13px;color:#52645d}}li{{line-height:1.8}}
</style></head><body><main><header><p class="eyebrow">FalsifyLab / executable scientific evidence</p><h1>Where does<br>a law stop working?</h1>
<p class="lead">Fit a plausible relationship. Spend a declared experiment budget trying to break it. Attempt a limited repair, then audit it on independent observations.</p>
<p>Synthetic mechanics and materials · CPU only · No API keys · No new physical-law discovery claimed</p></header>
<section><p class="eyebrow">01 / materials characterization</p><h2>A linear fit meets its limits.</h2>
<p>A low-strain Hookean model is challenged by a synthetic continuous bilinear response. Ten probes with four readings each locate a threshold-defined deviation onset. The model is revised within a predeclared bilinear family.</p>
<div class="cards"><div class="card">Active median bracket<strong>{fmt(materials['methods']['active']['median_bracket_width_strain'])}</strong>dimensionless strain</div>
<div class="card">Independent stress MAE<strong>{fmt(materials['median_holdout_linear_mae_mpa'], '.2f')} → {fmt(materials['median_holdout_revised_mae_mpa'], '.3f')}</strong>MPa · initial → bilinear repair</div></div>
<img src="{link(mat_file.parent / 'stress_strain_boundary.png')}" alt="Logged synthetic stress-strain measurements and constrained model repair">
<p>{materials['seed_count']} repeated noise seeds on <b>one</b> simulated material. Shared training: 40 readings. Each policy: 40 probe readings. Shared final audit: 249 readings.</p>
<div class="scroll"><table><thead><tr><th>Policy</th><th>Median width (strain)</th><th>25th–75th percentile</th><th>Noiseless onset covered</th><th>Boundary inconclusive</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">The 10 MPa operational boundary differs from physical yield. An empirical bracket is not a confidence interval; adaptive bisection exploits a monotonicity prior. Narrow brackets can miss the noiseless target under noise.</p></section>
<section><p class="eyebrow">02 / nonlinear dynamics</p><h2>An apparent invariant, a counterexample, a restricted repair.</h2>
<p><code>{escape(c['initial_hypothesis'])}</code> has {c['initial_training_relative_drift']:.3%} discovery drift. A fixed 15-condition stress grid exposes failures; a quartic revision is frozen before three new heldout trajectories are acquired.</p>
<img src="{link(osc_file.parent / 'duffing_counterexample.png')}" alt="Initial and revised invariant on the first independent Duffing audit trajectory">
<div class="scroll"><table><thead><tr><th>System</th><th>First holdout drift</th><th>Initial audit</th><th>Revised audit</th></tr></thead><tbody>{control_rows}</tbody></table></div>
<p class="note">The 2% drift threshold is a demonstration heuristic. Surviving finite tests does not prove conservation. The damped control remains refuted after attempted repair.</p></section>
{benchmark_html}
<section><p class="eyebrow">03 / the research record</p><h2>Inspect the evidence.</h2><p>Each schema-validated trace includes the candidate, raw-data checksums, partition manifest, frozen coefficients, every experiment, costs, counterexamples, independent audit and limitations.</p><ul>{certlinks}</ul>
<p><code>python -m falsifylab</code> regenerates this report. <code>python -m falsifylab.verify outputs</code> checks saved measurements, frozen predictions and provenance.</p></section>
<footer>Established context: SINDy, PySR, POPPER and SciExplorer. The proposed contribution is a compact integration of counterexample search, validity reporting, constrained revision and reproducible evidence. No statistical error control or general discovery superiority is established.</footer></main></body></html>'''
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html)
    return {'html': str(out_html), 'certificate_paths': [str(p) for p in certificates]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--osc', type=Path, default=Path('outputs/results.json'))
    parser.add_argument('--materials', type=Path, default=Path('outputs/materials/results.json'))
    parser.add_argument('--out', type=Path, default=Path('outputs/demo.html'))
    parser.add_argument('--certificates', type=Path, default=Path('outputs/certificates'))
    parser.add_argument('--benchmark', type=Path, default=Path('outputs/benchmark/metrics.json'))
    args = parser.parse_args()
    print(json.dumps(generate(args.osc, args.materials, args.out, args.certificates, args.benchmark), indent=2))

if __name__ == '__main__':
    main()
