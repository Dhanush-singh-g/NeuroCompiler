"""Audit expanded-source correctness, admission failure and closed holdouts."""
import argparse
import ast
import copy
import hashlib
import json
import math
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import expanded_study as study
from src.benchmarks import expanded as e
from src.benchmarks.compact import save, sha


def actual_order(rows, stats, clock):
    groups = {True: [], False: []}; differences = []
    for row in sorted(rows, key=lambda r: r['block']):
        local = {True: [], False: []}
        for sample in row['samples']:
            v = math.log(sample['left'][clock+'_seconds']/sample['right'][clock+'_seconds'])
            local[sample['left_first']].append(v); groups[sample['left_first']].append(v)
        differences.append(abs(float(np.median(local[True])-np.median(local[False]))))
    pooled = abs(float(np.median(groups[True])-np.median(groups[False])))
    passed = pooled <= math.log1p(.03) and all(v <= math.log1p(.03) for v in differences)
    if stats['order_pass'] != passed or stats['order_log_difference'] != pooled or stats['block_order_log_differences'] != differences:
        raise ValueError('Independent order reconstruction failed')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); args = p.parse_args()
    base = args.output.resolve(); output = e.ROOT / 'results/expanded_verification.json'
    if output.exists(): raise ValueError('Existing independent audit')
    d = study.check(base); preflight = json.loads((base/'preflight.json').read_text()); raw = json.loads((base/'gate.json').read_text())
    study.verify_gate(base, raw, 'gate')
    if not preflight['complete'] or not raw['complete']: raise ValueError('Incomplete correctness/admission study')
    oracle_checks = 0; native_cells = 0; interop = 0; source_files = 0
    for case, m in preflight['manifests'].items():
        if e.input_bytes(case) != (base/m['input']).read_bytes() or e.expected(case) != m['expected']:
            raise ValueError('Independent regenerated input/oracle differs')
        oracle_checks += 1; native_cells += len(m['correctness']); interop += len(m['interoperability'])
    for program in {m['program'] for m in preflight['manifests'].values()}:
        pin = d['source_pins'][program]; directory = base/'programs'/program; m = json.loads((directory/'manifest.json').read_text())
        driver = e.new.DRIVERS.get(program) or e.region.DRIVERS[program]
        if (directory/'driver.c').read_text() != driver: raise ValueError('Driver differs from frozen source')
        with tarfile.open(e.ROOT/pin['archive']) as archive:
            for member, relative in e.safe_members(archive, pin['root']):
                path = directory/'upstream'/relative
                # Expat deliberately generates its documented configuration.
                if program == 'expat' and relative.as_posix() == 'expat/lib/expat_config.h': continue
                if path.read_bytes() != archive.extractfile(member).read(): raise ValueError('Upstream source materialization changed')
                source_files += 1
    order_groups = 0
    for case, clocks in raw['summary']['statistics'].items():
        rows = [r for r in raw['records'] if r['case'] == case]
        for clock, stats in clocks.items(): actual_order(rows, stats, clock); order_groups += 1
    rejected = {}
    mutations = {
        'missing_pair': lambda r: r['records'][0]['samples'].pop(),
        'missing_trace': lambda r: r['records'][0]['samples'][0]['clock_trace'].pop(),
        'native_checksum': lambda r: r['records'][0]['samples'][0]['left'].update(checksum='bad'),
        'same_process': lambda r: r['records'][0].update(right_pid=r['records'][0]['left_pid']),
        'wrong_side': lambda r: r['records'][0]['samples'][0].update(left_first=not r['records'][0]['samples'][0]['left_first']),
        'aggregate_clock': lambda r: r['records'][0]['samples'][0]['left'].update(cpu_seconds=99.),
        'static_feature': lambda r: next(iter(r['manifests'].values()))['features']['O2'].__setitem__(0, 99.),
        'claimed_admission': lambda r: r['summary'].update(passed=not r['summary']['passed']),
        'extra_record': lambda r: r['records'].append(copy.deepcopy(r['records'][0])),
    }
    for name, mutate in mutations.items():
        bad = copy.deepcopy(raw); mutate(bad)
        with patch.object(study, 'check', return_value=d):
            try: study.verify_gate(base, bad, 'gate')
            except (ValueError, TypeError): rejected[name] = True
            else: raise ValueError('Corrupt evidence accepted: '+name)
    blocked = {}
    if not raw['summary']['passed']:
        for action in ['confirmation', 'train', 'fit', 'development']:
            result = subprocess.run([sys.executable, str(e.ROOT/'scripts/expanded_study.py'), action, '--output', str(base)], capture_output=True, timeout=90)
            if result.returncode == 0: raise ValueError('Failed gate allowed '+action)
            if b'gate failed' not in result.stderr and b'target not admitted' not in result.stderr:
                raise ValueError('Unexpected blocked-action failure: '+result.stderr.decode())
            blocked[action] = True
        if any((base/name).exists() for name in ['confirmation.json', 'train.json', 'selection.json', 'model.joblib', 'development.json']):
            raise ValueError('Blocked study created downstream evidence')
        for program in e.NEW_DEVELOPMENT:
            if (base/'programs'/program).exists(): raise ValueError('Fresh holdout executed after failed admission')
    preserved = 0; old_zip = e.ROOT/'results/persistent_iteration.zip'
    old_log = json.loads((e.ROOT/'results/persistent_snapshot.log').read_text())
    if sha(old_zip) != old_log['sha256']: raise ValueError('Prior immutable ZIP changed')
    with zipfile.ZipFile(old_zip) as archive:
        if archive.testzip(): raise ValueError('Prior archive CRC failure')
        hashes = json.loads(archive.read('snapshot_manifest.json'))['sha256']
        for name, digest in hashes.items():
            if not name.startswith(('results/', 'data/', 'models/')): continue
            if sha(e.ROOT/name) != digest: raise ValueError('Prior generated evidence changed: '+name)
            preserved += 1
    before = sha(base/'gate.json')
    subprocess.run([sys.executable, str(e.ROOT/'scripts/expanded_study.py'), 'gate', '--output', str(base), '--resume'], check=True)
    subprocess.run([sys.executable, str(e.ROOT/'scripts/expanded_study.py'), 'verify', '--output', str(base)], check=True)
    if sha(base/'gate.json') != before: raise ValueError('Completed verification resampled/changed gate')
    parsed = 0
    for directory in ['src', 'scripts', 'tests']:
        for source in (e.ROOT/directory).rglob('*.py'): ast.parse(source.read_text()); parsed += 1
    subprocess.run(['git', 'diff', '--check'], cwd=e.ROOT, check=True)
    save(output, {'training_implementations': 21, 'training_inputs': oracle_checks, 'correct_native_cells': native_cells,
        'O0_candidate_pairs': native_cells*2, 'independent_compressed_stream_checks': interop, 'upstream_files_checked': source_files,
        'actual_order_clock_groups_checked': order_groups, 'tamper_rejected': rejected, 'blocked_after_failed_gate': blocked,
        'fresh_development_builds': 0 if blocked else None, 'gate_sha256_unchanged': before, 'prior_generated_files_unchanged': preserved,
        'python_sources_parsed': parsed, 'git_diff_check': True, 'fit_targets_from_gate': 0, 'reserved_test_executions': 0,
        'portability': json.loads((e.ROOT/'results/expanded_portability_check.json').read_text())})
    print(json.dumps(json.loads(output.read_text()), indent=2))


if __name__ == '__main__': main()
