"""Immutable library-pair source/evidence archive with verified SHA manifest."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import sha
from src.benchmarks.broad import ROOT,pins


def main():
    output=ROOT/'results/broad_iteration.zip'
    if output.exists():raise ValueError('Existing snapshot; refusing overwrite')
    files={}
    def include(path,name=None):
        if path.is_file():files[name or str(path.relative_to(ROOT))]=path
    for pattern in ['*.md','requirements*.txt','pyproject.toml','setup.py','.gitignore']:
        for path in ROOT.glob(pattern):include(path)
    for directory in ['src','scripts','tests','configs']:
        for path in (ROOT/directory).rglob('*'):
            if '__pycache__' not in path.parts and path.suffix in ['.py','.c','.h','.yaml','.yml','.json']:include(path)
    for path in (ROOT/'data/processed/broad19').rglob('*'):include(path)
    for pin in pins().values():include(Path(pin['archive']))
    for path in (ROOT/'results').glob('broad*'):
        if path==output or path.name=='broad_snapshot.log':continue
        if path.is_dir():
            for child in path.rglob('*'):include(child)
        else:include(path)
    include(ROOT/'results/invocation_iteration.zip');include(ROOT/'results/invocation_snapshot.log')
    for path in (ROOT/'models').glob('sl_broad*'):include(path)
    hashes={name:sha(path) for name,path in sorted(files.items())}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,path in sorted(files.items()):archive.write(path,name)
        archive.writestr('snapshot_manifest.json',json.dumps({'sha256':hashes},indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():raise ValueError('Snapshot CRC failure')
        for name,expected in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=expected:raise ValueError('Snapshot hash mismatch')
    print(json.dumps({'files':len(files),'bytes':output.stat().st_size,'sha256':sha(output)},indent=2))


if __name__=='__main__':main()
