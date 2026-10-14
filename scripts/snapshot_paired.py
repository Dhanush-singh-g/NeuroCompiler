"""Preserve current native-pair evidence beside the immutable prior snapshot."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import sha
from src.benchmarks.polybench import ROOT


def main():
    output=ROOT/'results/paired_iteration.zip'
    if output.exists():raise ValueError('Existing snapshot; refusing overwrite')
    files={}
    def include(path,name=None):
        if path.is_file():files[name or str(path.relative_to(ROOT))]=path
    for pattern in ['*.md','requirements*.txt','pyproject.toml','setup.py','.gitignore']:
        for path in ROOT.glob(pattern):include(path)
    for directory in ['src','scripts','tests','configs']:
        for path in (ROOT/directory).rglob('*'):
            if '__pycache__' not in path.parts and path.suffix in ['.py','.c','.h','.yaml','.yml','.json']:
                include(path)
    for path in (ROOT/'data/processed/paired19').rglob('*'):include(path)
    for path in (ROOT/'results').glob('paired*'):
        if path==output:continue
        if path.is_dir():
            for child in path.rglob('*'):include(child)
        elif path.name!='paired_snapshot.log':include(path)
    for path in (ROOT/'models').glob('sl_paired*'):include(path)
    # The previous snapshot contains the pinned corpus, research and old studies.
    include(ROOT/'results/polybench_iteration.zip')
    include(ROOT/'results/polybench_snapshot.log')
    for name,path in {
        'environment/llvm19_setup.sh':Path('/workspace/.neurocompiler/llvm19/setup.sh'),
        'environment/activate.sh':Path('/workspace/.neurocompiler/activate.sh'),
        'environment/python_requirements.txt':Path('/workspace/.neurocompiler/requirements.txt'),
    }.items():include(path,name)
    hashes={name:sha(path) for name,path in sorted(files.items())}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,path in sorted(files.items()):archive.write(path,name)
        archive.writestr('snapshot_manifest.json',json.dumps({'sha256':hashes},indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():raise ValueError('Snapshot CRC failure')
        for name,expected in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=expected:
                raise ValueError('Snapshot file hash mismatch')
    print(json.dumps({'files':len(files),'bytes':output.stat().st_size,'sha256':sha(output)},indent=2))


if __name__=='__main__':main()
