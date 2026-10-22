"""Install the checksum-pinned LLVM10 tools without installing CompilerGym."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(directory, manifest):
    for name, expected in manifest['binaries'].items():
        path = directory/'bin'/name
        if not path.is_file() or sha(path) != expected:
            raise ValueError(f'Pinned compiler verification failed: {name}')


def install(archive=None, destination=None):
    manifest = json.loads((ROOT/'presentation/toolchain.json').read_text())
    destination = Path(destination or ROOT/'.presentation/toolchain')
    if destination.exists():
        verify(destination, manifest)
        print('Verified existing LLVM10 tools.')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    if archive is None:
        archive = ROOT/'.presentation/downloads/llvm10.tar.bz2'
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            partial = archive.with_suffix('.partial')
            print('Downloading 95 MB checksum-pinned LLVM10 runtime…', flush=True)
            try:
                with urllib.request.urlopen(manifest['url'], timeout=60) as response, partial.open('xb') as output:
                    total = 0
                    while chunk := response.read(1024*1024):
                        total += len(chunk)
                        if total > 200*1024*1024:
                            raise ValueError('Compiler archive exceeded the expected size limit.')
                        output.write(chunk)
                if sha(partial) != manifest['archive_sha256']:
                    raise ValueError('Downloaded LLVM archive checksum mismatch.')
                partial.replace(archive)
            finally:
                partial.unlink(missing_ok=True)
    archive = Path(archive)
    if sha(archive) != manifest['archive_sha256']:
        raise ValueError('LLVM archive checksum mismatch. Nothing was extracted.')
    print('Archive checksum verified. Extracting only compiler tools and headers…', flush=True)
    temporary = Path(tempfile.mkdtemp(prefix='llvm-install-', dir=destination.parent))
    try:
        with tarfile.open(archive, 'r:bz2') as stream:
            for member in stream:
                name = PurePosixPath(member.name.removeprefix('./'))
                selected = str(name) in {'LICENSE', 'bin/clang', 'bin/opt', 'bin/llvm-dis'} or str(name).startswith('lib/clang/10.0.0/include/')
                if not selected:
                    continue
                if name.is_absolute() or '..' in name.parts or '\\' in str(name) or not member.isfile():
                    if member.isdir() and not name.is_absolute() and '..' not in name.parts:
                        continue
                    raise ValueError('Unexpected compiler archive member.')
                if member.size > 130*1024*1024:
                    raise ValueError('Compiler archive member too large.')
                target = temporary.joinpath(*name.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if str(name).startswith('bin/') else 0o644)
        verify(temporary, manifest)
        (temporary/'verified.json').write_text(json.dumps(manifest, indent=2)+'\n')
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    print(f'Installed verified LLVM10 tools: {destination}')
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Optional local copy of the exact upstream archive.')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        parser.error('Use x86_64 Linux, or WSL2 Ubuntu22.04 on Windows.')
    try:
        install(args.archive)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
