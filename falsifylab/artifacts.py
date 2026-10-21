"""Portable, deterministic artifact IO and software provenance."""
from __future__ import annotations
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def provenance() -> dict:
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], text=True))
    except (OSError, subprocess.CalledProcessError):
        sha, dirty = None, None
    sources = {str(p): digest(p) for p in sorted(Path('falsifylab').glob('*.py'))}
    return {'git_sha': sha, 'git_worktree_dirty': dirty,
            'source_sha256': sources, 'python': platform.python_version(),
            'dependencies': {name: version(name) for name in ('numpy', 'scipy', 'matplotlib', 'pytest', 'jsonschema')}}
