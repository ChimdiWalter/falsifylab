import pytest


@pytest.fixture(scope='session')
def evidence_run(tmp_path_factory):
    from falsifylab.run_demo import execute as oscillator
    from falsifylab.run_materials import execute as material
    root = tmp_path_factory.mktemp('evidence')
    oscillator(root)
    material(root / 'materials', seeds=2)
    return root
