"""Last unused logical CPU, one screen and optional independent confirmation.

Use CPU1 for orchestration, CPU0 for native children. The generic collector
and this launcher are both hash-bound before timing. All prior studies remain
unchanged; there is no failed-core replacement or compiler-effect sampling.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import screen_expanded_targets as collector
from src.benchmarks.compact import save, sha

collector.CPUS = [0]
collector.SEED = 20261021
collector.DECL = collector.e.ROOT/'results/expanded_cpu0_declaration.json'
collector.OUT = collector.e.ROOT/'results/expanded_cpu0_screen.json'
collector.CONFIRM = collector.e.ROOT/'results/expanded_cpu0_confirmation.json'
original_check = collector.check


def check():
    d, base = original_check()
    if d['launcher_sha256'] != sha(Path(__file__)) or d['launcher_sha256'] != sha(base/'declared_sources/scripts/screen_expanded_cpu0.py'):
        raise ValueError('Frozen CPU0 launcher changed')
    return d, base


collector.check = check


def main():
    p = argparse.ArgumentParser(); p.add_argument('--declare', action='store_true'); p.add_argument('--base', type=Path)
    p.add_argument('--confirmation', action='store_true'); p.add_argument('--resume', action='store_true'); a = p.parse_args()
    if a.declare:
        if a.base is None: raise ValueError('--base required')
        base = a.base.resolve(); collector.declare(base)
        d = json.loads(collector.DECL.read_text()); d.update(launcher_sha256=sha(Path(__file__)), orchestration_cpu=1,
            gate='all six CPU AND wall controls on unused CPU0; one fixed 18-cell screen; no retries',
            confirmation_budget='one independent 18-cell CPU0 confirmation if eligible; no further target search')
        save(collector.DECL, d); shutil.copy2(Path(__file__), base/'declared_sources/scripts/screen_expanded_cpu0.py')
        check()
    else: collector.collect(a.confirmation, a.resume)


if __name__ == '__main__': main()
