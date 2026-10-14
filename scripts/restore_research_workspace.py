"""Verify and restore a release workspace without executing or unpickling it."""
import argparse
import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def digest(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        value.update(chunk)
    return value.hexdigest()


def destination(root, name):
    relative = PurePosixPath(name)
    if (relative.is_absolute() or not relative.parts or relative.parts[0] not in ('data', 'models', 'results')
            or '..' in relative.parts or '\\' in name or relative.as_posix() != name):
        raise ValueError('Unsafe workspace path')
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Unsafe workspace destination')
    return path


def restore(archive_path, manifest_path, root, checksum_path=None):
    root = Path(root).resolve()
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('files'), dict) or not manifest['files']:
        raise ValueError('Invalid manifest')
    expected_hash = manifest['archive_sha256']
    if checksum_path:
        fields = Path(checksum_path).read_text().split()
        if len(fields) != 2 or fields != [expected_hash, manifest['archive']]:
            raise ValueError('Checksum file differs from manifest')
    with Path(archive_path).open('rb') as stream:
        if digest(stream) != expected_hash:
            raise ValueError('Archive SHA256 mismatch')
    seen = set()
    # Validate everything and check all conflicts before writing any file.
    with tarfile.open(archive_path, 'r|gz') as archive:
        for member in archive:
            if not member.isfile() or member.name in seen or member.name not in manifest['files']:
                raise ValueError('Unexpected, duplicate or nonregular archive entry')
            seen.add(member.name)
            path = destination(root, member.name)
            expected = manifest['files'][member.name]
            if member.size != expected['bytes']:
                raise ValueError('File length mismatch: '+member.name)
            with archive.extractfile(member) as stream:
                if digest(stream) != expected['sha256']:
                    raise ValueError('File SHA256 mismatch: '+member.name)
            if path.exists():
                if not path.is_file():
                    raise ValueError('Existing nonfile: '+member.name)
                with path.open('rb') as stream:
                    if digest(stream) != expected['sha256']:
                        raise ValueError('Refuse to overwrite different existing file: '+member.name)
    if seen != set(manifest['files']):
        raise ValueError('Archive is missing manifest entries')
    print(f'Verified {len(seen)} files. Restoring missing files only.', flush=True)
    restored, skipped = 0, 0
    with tarfile.open(archive_path, 'r|gz') as archive:
        for member in archive:
            path = destination(root, member.name)
            if path.exists():
                with path.open('rb') as stream:
                    if digest(stream) != manifest['files'][member.name]['sha256']:
                        raise ValueError('File changed after verification')
                skipped += 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                try:
                    with archive.extractfile(member) as source:
                        for chunk in iter(lambda: source.read(1024*1024), b''):
                            output.write(chunk)
                    output.flush()
                except BaseException:
                    temporary.unlink(missing_ok=True)
                    raise
            try:
                with temporary.open('rb') as stream:
                    if digest(stream) != manifest['files'][member.name]['sha256']:
                        raise ValueError('File changed during extraction')
                os.chmod(temporary, member.mode & 0o777)
                # Hard-link creation fails if a file appeared after validation.
                # It never replaces an existing destination.
                os.link(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
            restored += 1
    return {'verified': len(seen), 'restored': restored, 'identical_skipped': skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sha256-file', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(restore(args.archive, args.manifest, args.root, args.sha256_file), indent=2))


if __name__ == '__main__':
    main()
