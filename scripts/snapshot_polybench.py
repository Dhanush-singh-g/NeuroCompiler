"""Create an immutable portable source/evidence snapshot with SHA-256 manifest."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.polybench import ROOT
from src.benchmarks.compact import sha


def main():
    output=ROOT/'results/polybench_iteration.zip'
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
    for directory in ['data/processed/polybench-c-3.2','data/processed/polybench19']:
        for path in (ROOT/directory).rglob('*'):include(path)
    include(ROOT/'data/processed/polybench-c-3.2.tar.gz')
    for path in (ROOT/'results').glob('polybench*'):
        if path.is_file() and path!=output:include(path)
    include(ROOT/'results/scheduler_diagnostic.json')
    include(ROOT/'results/robust_iteration.zip')
    include(ROOT/'models/sl_polybench19_bundle.joblib')
    for prefix in ['autophase','compiler_gym','measurement','polybench.html']:
        for path in (ROOT/'results/research_sources').glob(prefix+'*'):include(path)
    for name,path in {
        'environment/llvm19_setup.sh':Path('/workspace/.neurocompiler/llvm19/setup.sh'),
        'environment/llvm19_setup_validation.log':Path('/workspace/.neurocompiler/llvm19/setup-validation.log'),
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
