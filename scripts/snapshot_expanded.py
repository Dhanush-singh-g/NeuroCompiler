"""Immutable source/evidence snapshot nesting the unchanged predecessor."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import sha
from src.benchmarks.expanded import ROOT, source_pins


def main():
    output = ROOT/'results/expanded_iteration.zip'
    if output.exists(): raise ValueError('Existing snapshot; no overwrite')
    files = {}
    def include(path):
        if path.is_file(): files[str(path.relative_to(ROOT))] = path
    for pattern in ['*.md', 'requirements*.txt', 'pyproject.toml', 'setup.py', '.gitignore']:
        for path in ROOT.glob(pattern): include(path)
    for folder in ['src', 'scripts', 'tests', 'configs']:
        for path in (ROOT/folder).rglob('*'):
            if '__pycache__' not in path.parts and path.suffix in ['.py', '.c', '.h', '.json', '.yaml', '.yml']: include(path)
    for pin in source_pins().values(): include(ROOT/pin['archive'])
    for path in (ROOT/'results').glob('expanded*'):
        if path == output or path.name == 'expanded_snapshot.log': continue
        if path.is_dir():
            for child in path.rglob('*'): include(child)
        else: include(path)
    include(ROOT/'results/persistent_iteration.zip'); include(ROOT/'results/persistent_snapshot.log')
    hashes = {name: sha(path) for name, path in sorted(files.items())}
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(files.items()): archive.write(path, name)
        archive.writestr('snapshot_manifest.json', json.dumps({'sha256': hashes}, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip(): raise ValueError('Snapshot CRC failed')
        for name, digest in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest: raise ValueError('Snapshot SHA mismatch')
    print(json.dumps({'files': len(files), 'bytes': output.stat().st_size, 'sha256': sha(output)}, indent=2))


if __name__ == '__main__': main()
