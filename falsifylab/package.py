"""Build a local, checksum-manifested source/evidence bundle; never publish."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED
from .artifacts import digest
from .verify import verify


def build(out: Path):
    root=Path.cwd()
    verify(root/'outputs')
    files=[]
    for name in ('falsifylab','tests','notebooks','docs','prompts','submission','outputs','baseline'):
        files += [p for p in (root/name).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and '__marimo__' not in p.parts and p.suffix not in ('.pyc','.zip')]
    files += [root/name for name in ('README.md','requirements.txt','requirements-lock.txt',
                                    'requirements-notebook.txt','make_onepager.py','.gitignore') if (root/name).is_file()]
    files=sorted(set(files))
    try:
        sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        sha=None
    manifest={'project':'FalsifyLab','artifact_git_sha':sha,
              'scope':'local source, tests, measured synthetic evidence and unposted submission drafts',
              'files':{str(p.relative_to(root)):digest(p) for p in files}}
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,'w') as archive:
        for p in files:
            info=ZipInfo('FalsifyLab/'+str(p.relative_to(root)))
            info.compress_type=ZIP_STORED if p.suffix in ('.npz','.png') else ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info,p.read_bytes())
        info=ZipInfo('FalsifyLab/bundle_manifest.json')
        info.compress_type=ZIP_DEFLATED
        archive.writestr(info,json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    checksum=digest(out)
    out.with_suffix('.sha256').write_text(checksum+'  '+out.name+'\n')
    print(f'PACKAGED {len(files)} files: {out} ({out.stat().st_size:,} bytes)')
    print(f'SHA256 {checksum}')
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('dist/FalsifyLab_bundle.zip'))
    build(parser.parse_args().out)

if __name__=='__main__':
    main()
