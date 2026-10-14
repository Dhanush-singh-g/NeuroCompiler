"""Preserve code, pinned archives, and complete immutable experiment evidence."""
import hashlib
import json
import zipfile
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1];output=root/'results/robust_iteration.zip'
    if output.exists():raise ValueError('Preserve existing snapshot')
    files=set(root.glob('*.md'))|{root/'.gitignore'}
    for folder in ['src','scripts','tests','configs']:files.update((root/folder).rglob('*.py'))
    files.update((root/'models').glob('*.joblib'))
    files.update(p for p in (root/'data/baselines').glob('*') if p.is_file())
    files.update(p for p in (root/'data/processed').glob('*') if p.is_file())
    essentials={'initial.bc','source.c','program.bc','a.out','_finfo_dataset','manifest.json','input.dat'}
    for folder in ['compact_train','compact_validation','kernel_train','real_train']:
        files.update(p for p in (root/'data/processed'/folder).rglob('*') if p.is_file() and p.name in essentials)
    files.update((root/'data/processed/real_sources').glob('*.tar.gz'))
    for pattern in ['*/initial.bc','*/build.json','*/driver.c','*/expat_config.h']:
        files.update((root/'data/processed/real_build').glob(pattern))
    for pattern in ['*.json','*.bc','*.ll','*.out','compact_*.log','transform_*.log','kernel_*.log','robust_*.log','real_*.log']:
        files.update((root/'results').glob(pattern))
    manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,str(p.relative_to(root)))
        z.writestr('SHA256_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('Snapshot CRC failure')
        if set(z.namelist())!=set(manifest)|{'SHA256_MANIFEST.json'}:raise ValueError('Snapshot coverage mismatch')
        for name,h in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError(f'Snapshot checksum mismatch: {name}')
    print('Verified',len(manifest),'files;',output.stat().st_size,'bytes;',output)


if __name__=='__main__':main()
