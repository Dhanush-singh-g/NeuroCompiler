"""Reassemble the research-branch archive, checking every part and the whole file."""
import argparse
import hashlib
import json
from pathlib import Path


def join(directory, output=None):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'research-workspace-parts.json').read_text())
    if manifest.get('schema_version') != 1 or not manifest.get('parts'):
        raise ValueError('Invalid parts manifest')
    archive_name = manifest['archive']
    if Path(archive_name).name != archive_name or archive_name in ('.', '..'):
        raise ValueError('Unsafe archive name')
    output = Path(output) if output else directory/archive_name
    temporary = output.with_name(output.name+'.partial')
    if output.exists() or temporary.exists():
        raise ValueError('Refuse to overwrite an existing archive or temporary file')
    output.parent.mkdir(parents=True, exist_ok=True)
    whole, total = hashlib.sha256(), 0
    try:
        with temporary.open('xb') as target:
            seen = set()
            for index, part in enumerate(manifest['parts'], 1):
                name = part['name']
                if Path(name).name != name or name in seen or name in ('.', '..'):
                    raise ValueError('Unsafe or duplicate part name')
                seen.add(name)
                path = directory/name
                if path.is_symlink() or not path.is_file() or path.stat().st_size != part['bytes']:
                    raise ValueError('Missing or invalid part: '+name)
                digest, count = hashlib.sha256(), 0
                with path.open('rb') as source:
                    for chunk in iter(lambda: source.read(1024*1024), b''):
                        target.write(chunk)
                        whole.update(chunk)
                        digest.update(chunk)
                        count += len(chunk)
                        total += len(chunk)
                if count != part['bytes'] or digest.hexdigest() != part['sha256']:
                    raise ValueError('Part checksum mismatch: '+name)
                print(f'Joined {index}/{len(manifest["parts"])} parts.', flush=True)
        if total != manifest['archive_bytes'] or whole.hexdigest() != manifest['archive_sha256']:
            raise ValueError('Whole archive checksum mismatch')
        temporary.rename(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print('Verified archive: '+str(join(args.directory, args.output)))


if __name__ == '__main__':
    main()
