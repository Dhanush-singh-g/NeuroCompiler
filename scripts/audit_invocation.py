"""Read-only provenance/secondary checks and one default-export correctness check.

This audit is separate from the frozen training experiment. It never collects
new performance labels or changes model selection.
"""
import copy
import json
import math
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import effect, save, sha
from src.benchmarks.invocation import BASE, DRIVERS, EXPAT_CONFIG, NAME, ROOT, verify


def check_secondary(report, declaration, manifest):
    if not report['complete'] or any(report[k] != v for k, v in declaration.items()):
        raise ValueError('Secondary declaration mismatch')
    protocol = declaration['protocol']
    expected = manifest['expected']
    roles = [('qualification', 'O3', 'O3'), ('candidate_control', 'O2', 'O2'), ('effect', 'O3', 'O2')]
    records = report['records']
    if len(records) != protocol['blocks'] * len(roles):
        raise ValueError('Incomplete secondary coverage')
    rng = np.random.default_rng(protocol['seed'])
    for record, (block, role, left, right) in zip(records, [(b, *r) for b in range(protocol['blocks']) for r in roles]):
        first = bool(rng.integers(2))
        if any(record[k] != v for k, v in {'block': block, 'role': role, 'left': left, 'right': right, 'first': first}.items()):
            raise ValueError('Secondary cell/order mismatch')
        if len(record['samples']) != protocol['pairs']:
            raise ValueError('Incomplete secondary pair count')
        for p, row in enumerate(record['samples']):
            if row['pair'] != p or row['left_first'] != ((p % 2 == 0) == first):
                raise ValueError('Secondary pair order mismatch')
            for side in ['left', 'right']:
                sample = row[side]
                if {k: sample[k] for k in expected} != expected:
                    raise ValueError('Secondary oracle mismatch')
                if any(not math.isfinite(sample[k]) or sample[k] <= 0 for k in ['cpu_seconds', 'wall_seconds']):
                    raise ValueError('Invalid secondary clocks')
    statistics = {}
    for clock in ['cpu', 'wall']:
        detail = {}
        for role, _, _ in roles:
            rows = [r for r in records if r['role'] == role]
            detail[role] = effect([{'left_seconds': [s['left'][clock + '_seconds'] for s in r['samples']],
                                   'right_seconds': [s['right'][clock + '_seconds'] for s in r['samples']]} for r in rows], protocol)
        measured = detail['effect']
        valid = detail['qualification']['control_pass'] and detail['candidate_control']['control_pass']
        detail['qualified'] = bool(valid)
        detail['confirmed_gain'] = bool(valid and measured['interval'][0] > 1 + protocol['gain_floor']
                                        and all(v > 1 + protocol['gain_floor'] for v in measured['blocks']))
        statistics[clock] = detail
    if statistics != report['statistics']:
        raise ValueError('Secondary derived statistics changed')
    return len(records) * protocol['pairs'] * 2


def main():
    output = ROOT / 'results/invocation_additional_audit.json'
    if output.exists():
        raise ValueError('Existing audit; refusing overwrite')
    declared = json.loads((ROOT / 'results/invocation_declaration.json').read_text())
    for name, digest in declared['source_sha256'].items():
        if sha(ROOT / name) != digest or sha(BASE / 'declared_sources' / name) != digest:
            raise ValueError('Frozen study source changed ' + name)
    raw = {s: json.loads((ROOT / f'results/{NAME}_{s}.json').read_text()) for s in ['train', 'development']}
    for r in raw.values():
        verify(r)
    source_count = 0
    programs = {}
    for r in raw.values():
        for m in r['manifests'].values():
            programs.setdefault(m['program'], m)
    for program, m in programs.items():
        pin = m['source_pin']
        subdir = {'lua': 'src/', 'expat': 'expat/lib/', 'lz4': 'lib/'}.get(program, '')
        with tarfile.open(pin['archive']) as archive:
            for source, digest in m['sources'].items():
                path = Path(source)
                if sha(path) != digest:
                    raise ValueError('Source manifest mismatch')
                if path.name == 'driver.c':
                    expected = DRIVERS[program].encode()
                elif program == 'expat' and path.name == 'expat_config.h':
                    expected = EXPAT_CONFIG.encode()
                else:
                    expected = archive.extractfile(pin['root'] + '/' + subdir + path.name).read()
                if path.read_bytes() != expected:
                    raise ValueError('Upstream/generated source provenance mismatch ' + source)
                source_count += 1
    secondary = json.loads((ROOT / 'results/invocation_isolated_confirmation.json').read_text())
    declaration = json.loads((ROOT / 'results/invocation_isolated_declaration.json').read_text())
    if declaration['training_sha256'] != sha(ROOT / f'results/{NAME}_train.json'):
        raise ValueError('Secondary training binding changed')
    for name, digest in declaration['source_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Secondary source changed')
    if sha(BASE / 'isolated_library_worker.out') != declaration['worker_sha256']:
        raise ValueError('Secondary worker changed')
    count = check_secondary(secondary, declaration, raw['train']['manifests']['expat_nested'])
    rejected = {}
    for name, mutate in {
        'missing_pair': lambda r: r['records'][0]['samples'].pop(),
        'pair_order': lambda r: r['records'][0]['samples'][0].update({'left_first': False}),
        'oracle': lambda r: r['records'][0]['samples'][0]['left'].update({'checksum': 'bad'}),
        'gain': lambda r: r['statistics']['cpu'].update({'confirmed_gain': True}),
    }.items():
        bad = copy.deepcopy(secondary)
        mutate(bad)
        try:
            check_secondary(bad, declaration, raw['train']['manifests']['expat_nested'])
        except ValueError:
            rejected[name] = True
        else:
            raise ValueError('Secondary corruption accepted ' + name)
    exported = ROOT / 'results/invocation_export'
    manifest = json.loads((exported / 'manifest.json').read_text())
    original = raw['development']['manifests']['xxhash_random']
    files = {'program.bc': original['artifacts']['O3']['bc'], 'candidate.so': original['artifacts']['O3']['so'],
             'invocation_worker.out': original['worker'], 'input.dat': original['input']}
    for name, source in files.items():
        if sha(exported / name) != sha(source) or sha(exported / name) != manifest['files_sha256'][name]:
            raise ValueError('Export mismatch')
    if manifest['expected'] != original['expected'] or manifest['decision']['choice'] != 'O3' or manifest['experimental']:
        raise ValueError('Default decision mismatch')
    result = subprocess.run(['taskset', '-c', '2', str(exported / 'invocation_worker.out'),
                             str(exported / 'candidate.so'), str(exported / 'candidate.so'),
                             '1', '1', '0', str(exported / 'input.dat')], capture_output=True, check=True, timeout=60)
    row = json.loads(result.stdout)
    for sample in row['samples']:
        for side in ['left', 'right']:
            if {k: sample[side][k] for k in original['expected']} != original['expected']:
                raise ValueError('Export independent oracle mismatch')
    denied = ROOT / 'results/invocation_experimental_rejected'
    if denied.exists():
        raise ValueError('Rejection output path already exists')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/optimize_invocation.py'), '--case', 'xxhash_random',
                             '--experimental', '--output', str(denied)], capture_output=True, timeout=60)
    if result.returncode != 1 or b'No CV-qualified experimental model' not in result.stderr or denied.exists():
        raise ValueError('Unqualified experimental export accepted')
    report = {'frozen_primary_sources_unchanged': len(declared['source_sha256']),
              'source_files_checked_against_pins_or_declared_generated_text': source_count,
              'upstream_programs': len(programs), 'secondary_worker_outputs_checked': count,
              'secondary_statistics_recomputed': True, 'secondary_tamper_rejected': rejected,
              'secondary_qualified': {c: secondary['statistics'][c]['qualified'] for c in ['cpu', 'wall']},
              'secondary_confirmed_gain': {c: secondary['statistics'][c]['confirmed_gain'] for c in ['cpu', 'wall']},
              'secondary_control_scope': 'same DSO in two separate processes; primary separate-copy placement descriptor does not apply',
              'default_export_independent_oracle': True, 'unqualified_experimental_export_rejected': True,
              'source_sha256': {s: sha(ROOT / f'results/{NAME}_{s}.json') for s in raw},
              'secondary_sha256': sha(ROOT / 'results/invocation_isolated_confirmation.json'),
              'new_performance_labels': 0, 'reserved_test_executions': 0}
    save(output, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
