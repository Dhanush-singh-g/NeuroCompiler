"""Source-only portable runner, pinned archives and SHA/CRC verification."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmarks.expanded import ROOT, source_pins
from src.benchmarks.compact import sha


def main():
    output = ROOT / 'results/expanded_portable_sources.zip'
    if output.exists(): raise ValueError('Existing portable kit; no overwrite')
    files = {}
    for directory in ['src', 'scripts', 'configs', 'tests']:
        for path in (ROOT / directory).rglob('*'):
            if '__pycache__' not in path.parts and path.suffix in ['.py', '.c', '.h', '.json', '.yaml', '.yml']:
                files[str(path.relative_to(ROOT))] = path
    pins = ROOT / 'results/expanded_source_pins.json'; files[str(pins.relative_to(ROOT))] = pins
    for pin in source_pins().values():
        path = ROOT / pin['archive']
        if sha(path) != pin['sha256']: raise ValueError('Pinned archive changed')
        files[pin['archive']] = path
    hashes = {name: sha(path) for name, path in sorted(files.items())}
    instructions = '''# Portable NeuroCompiler source runner

This kit contains code and 23 checksum-pinned upstream source archives, including
their licenses. It contains no NeuroCompiler-generated native binaries, fitted
models or prior timing labels. It supports Linux; a different CPU requires a
fresh build and a fresh study directory. Cross-machine performance is untested.

Use Python 3.10 and LLVM19 (clang, opt, llvm-link, llvm-dis). The independent LZ4
decoder needs the system liblz4 runtime. On Debian/Ubuntu these LLVM tools are
provided by the llvm-19 and clang-19 packages; liblz4-1 supplies the decoder.
Use a venv and install requirements-portable.txt. Preserve normal TLS/checksum
verification. No CompilerGym or LLVM10 installation is required by this workflow.

Run from the extracted kit directory, with no other benchmarking/build jobs:

```bash
export NEUROCOMPILER_LLVM19=/usr/lib/llvm-19/bin
python scripts/expanded_study.py prepare --output runs/local_001 --cpu 2
python scripts/expanded_study.py declare --output runs/local_001
python scripts/expanded_study.py gate --output runs/local_001
```

Select a CPU allowed by your Linux cpuset. Keep orchestration on another CPU
(e.g. prefix commands with taskset -c 0 when using native CPU2). All archives
are bundled; builds need no upstream download. Preparation builds 21 training
implementations/42 correctness inputs and calibrates equal counts; its clocks
never fit models. The study preselects one formal input per implementation.

Read gate.json: all six inputs must pass both clocks. If it fails, stop; do not
rerun controls until they pass. If it passes, run exactly one confirmation:

```bash
python scripts/expanded_study.py confirmation --output runs/local_001
```

Only if confirmation also passes all six inputs on both clocks:

```bash
python scripts/expanded_study.py train --output runs/local_001
python scripts/expanded_study.py fit --output runs/local_001
python scripts/expanded_study.py development --output runs/local_001
python scripts/evaluate_expanded.py --output runs/local_001
python scripts/expanded_study.py verify --output runs/local_001
```

json.h and libdeflate are untouched development sources. The runner builds and
executes them only after freezing the model. Training recommendations are O3,
O2 or no-vector; large-inline is correctness/features only. Missing outcomes
are unscorable. O3 remains default unless whole-program CV qualifies a model.
Library API clocks exclude startup, IPC and client verification. Never pool
different machines, old studies, gate/correctness clocks or failed controls.

Completed sampling commands accept --resume and verify without resampling.
Preflight --repair is for a diagnosed build/correctness defect before freeze,
and preserves failed build attempts; it cannot repair failed timing controls.
Use a new directory for a new machine, toolchain or declaration. Existing
formal declarations/fitted models refuse overwrite. A source rebuild validates
compatibility, not improvement over O3. Broad learned gain remains unproven.
'''
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(files.items()): archive.write(path, name)
        archive.writestr('PORTABLE_RUNNER.md', instructions)
        archive.writestr('requirements-portable.txt', 'numpy==1.23.5\nscipy==1.15.3\nscikit-learn==1.3.2\njoblib==1.3.2\n')
        archive.writestr('portable_manifest.json', json.dumps({'sha256': hashes, 'scope': 'source-only; fresh native builds required'}, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip(): raise ValueError('Portable kit CRC failure')
        for name, digest in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest: raise ValueError('Portable kit file hash mismatch')
    print(json.dumps({'files': len(files), 'bytes': output.stat().st_size, 'sha256': sha(output)}, indent=2))


if __name__ == '__main__': main()
