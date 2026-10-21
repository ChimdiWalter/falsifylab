"""Portable report and evidence records from freshly executed source artifacts."""
import json
from falsifylab.make_report import generate
from falsifylab.certificates import validate
from falsifylab.verify import verify


def test_certificate_generation(evidence_run):
    root = evidence_run
    result = generate(root / 'results.json', root / 'materials/results.json',
                      root / 'demo.html', root / 'certificates')
    assert len(result['certificate_paths']) == 4
    m = json.loads((root / 'certificates/materials.json').read_text())
    o = json.loads((root / 'certificates/oscillator.json').read_text())
    validate(m, certificate_path=root / 'certificates/materials.json', artifact_root=root)
    assert m['selection_policy']['query_budget_per_policy'] == 10
    assert len(o['partition_manifest']['partitions']['probe']) == 15
    assert m['record_type'].endswith('NOT_formal_proof')
    assert verify(root) == 4
