"""Preserve generated data, models and results as a checksum-backed release asset."""
import argparse
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'neurocompiler-research-workspace-20261014.tar.gz'


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def package(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError('Write release assets outside the checkout to avoid recursive packaging')
    output.mkdir(parents=True, exist_ok=True)
    archive, manifest_path, checksum_path = (output/ARCHIVE, output/'research-workspace-manifest.json', output/'research-workspace.sha256')
    if any(p.exists() for p in (archive, manifest_path, checksum_path, output/(ARCHIVE+'.partial'))):
        raise ValueError('Refuse to overwrite an existing release package')
    files = []
    for tree in ('data', 'models', 'results'):
        for path in (root/tree).rglob('*'):
            if '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
                continue
            if path.is_symlink():
                if not path.is_file() or not path.resolve().is_relative_to(root):
                    raise ValueError('External or nonfile symlink in generated workspace: '+str(path.relative_to(root)))
            if path.is_file():
                files.append(path)
    files.sort()
    records = {}
    stamps = {}
    for path in files:
        stat = path.stat()
        name = path.relative_to(root).as_posix()
        records[name] = {'bytes': stat.st_size, 'sha256': digest(path)}
        if path.is_symlink():
            records[name]['materialized_symlink_target'] = str(path.readlink())
        stamps[name] = (stat.st_size, stat.st_mtime_ns)
    print(f'Hashed {len(files)} files, {sum(v["bytes"] for v in records.values()):,} bytes.', flush=True)
    partial = output/(ARCHIVE+'.partial')
    with tarfile.open(partial, 'w:gz', compresslevel=1, dereference=True) as archive_stream:
        for index, path in enumerate(files):
            name = path.relative_to(root).as_posix()
            stat = path.stat()
            if stamps[name] != (stat.st_size, stat.st_mtime_ns):
                raise ValueError('File changed during packaging: '+name)
            archive_stream.add(path, arcname=name, recursive=False)
            if index and index % 1000 == 0:
                print(f'Archived {index}/{len(files)} files.', flush=True)
    partial.rename(archive)
    manifest = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                'archive': archive.name, 'archive_sha256': digest(archive),
                'archive_bytes': archive.stat().st_size, 'files': records,
                'excluded': ['Python __pycache__ directories and .pyc/.pyo files',
                             'Git metadata, virtual environments and machine-private setup outside data/models/results'],
                'symlink_policy': 'Internal file symlinks materialized with original target recorded; external/nonfile links rejected'}
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    checksum_path.write_text(f'{manifest["archive_sha256"]}  {archive.name}\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'}, indent=2), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package(args.root, args.output)


if __name__ == '__main__':
    main()
