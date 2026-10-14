"""Fetch pinned upstream archives with TLS and SHA-256 verification."""
import tarfile
from urllib.request import urlopen

from src.benchmarks.real import ROOT,SOURCES
from src.benchmarks.compact import sha


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    for name,spec in SOURCES.items():
        archive=ROOT/spec['archive']
        if not archive.exists():
            temporary=archive.with_suffix(archive.suffix+'.tmp')
            try:
                with urlopen(spec['url'],timeout=45) as response,temporary.open('wb') as out:
                    total=0
                    while chunk:=response.read(1024*1024):
                        total+=len(chunk)
                        if total>32*1024*1024:raise ValueError('Archive exceeds fixed size budget')
                        out.write(chunk)
                if sha(temporary)!=spec['sha256']:raise ValueError('Upstream archive checksum mismatch')
                temporary.replace(archive)
            finally:temporary.unlink(missing_ok=True)
        if sha(archive)!=spec['sha256']:raise ValueError('Existing archive checksum mismatch')
        if not (ROOT/spec['root']).exists():
            with tarfile.open(archive) as t:t.extractall(ROOT,filter='data')
        print('Verified',name,spec['sha256'],flush=True)


if __name__=='__main__':main()
