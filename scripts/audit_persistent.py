"""Reconstruct timing strata, replay CV, verify native outputs and preservation."""
import ast
import copy
import hashlib
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import measure_persistent as pilot, confirm_persistent as confirmation, study_persistent as study
from src.benchmarks.compact import save, sha
from src.supervised.region import NativeSelector, program_cv
from src.supervised.frozen import predictions_equal


def independent_order(rows, stats, clock):
    pooled = {True: [], False: []}; differences = []; medians = []
    for row in sorted(rows, key=lambda r: r['block']):
        local = {True: [], False: []}; logs = []
        for sample in row['samples']:
            value = math.log(sample['left'][clock + '_seconds'] / sample['right'][clock + '_seconds'])
            local[sample['left_first']].append(value); pooled[sample['left_first']].append(value); logs.append(value)
        differences.append(abs(float(np.median(local[True]) - np.median(local[False]))))
        medians.append(float(np.exp(np.median(logs))))
    bias = abs(float(np.median(pooled[True]) - np.median(pooled[False])))
    passed = bias <= math.log1p(.03) and all(v <= math.log1p(.03) for v in differences)
    if stats['order_pass'] != passed or stats['order_log_difference'] != bias or stats['block_order_log_differences'] != differences:
        raise ValueError('Independent starting-order reconstruction failed')
    if not np.allclose(stats['blocks'], medians, rtol=1e-14, atol=0):
        raise ValueError('Independent block medians differ')


def replay(selected, labels, manifests):
    actuals = {}
    for name, experiment in selected['experiments'].items():
        actual = {'parameters': experiment['parameters'], **program_cv(labels, manifests, *experiment['parameters'])}
        a, b = copy.deepcopy(actual), copy.deepcopy(experiment)
        for group in ['records', 'unscorable']:
            if len(a.get(group, [])) != len(b.get(group, [])):
                raise ValueError('CV prediction coverage changed')
            for x, y in zip(a.get(group, []), b.get(group, [])):
                if not predictions_equal(x['scores'], y['scores']):
                    raise ValueError('CV prediction replay changed')
                x['scores'] = y['scores'] = {}
        if a != b:
            raise ValueError('CV replay changed')
        for fold in actual['folds']:
            if fold['held_program'] in fold['train_programs'] or set(fold['train_cases']) & set(fold['test_cases']):
                raise ValueError('Original-program leakage')
        actuals[name] = actual
    if {tuple(v['parameters']) for v in actuals.values()} != set(study.PARAMETERS):
        raise ValueError('Incomplete model menu')
    accepted = [k for k, v in actuals.items() if v['eligible'] and v['score']['utility'] > 0
                and v['score']['worst_original_program'] >= .97 and v['score']['confirmed_workloads'] >= 1]
    best = max(accepted, key=lambda k: actuals[k]['score']['utility']) if accepted else None
    if selected['experimental'] != best or selected['cv_certified'] != bool(best):
        raise ValueError('Model gate changed')
    return actuals, best


def main():
    output = study.ROOT / 'results/persistent_verification.json'
    if output.exists():
        raise ValueError('Existing audit; no overwrite')
    pilot_raw = json.loads(pilot.OUTPUT.read_text()); pilot.verify(pilot_raw)
    controls = {}
    for stage in confirmation.SEEDS:
        _, source = confirmation.paths(stage); controls[stage] = json.loads(source.read_text())
        confirmation.verify(stage, controls[stage])
    raw = {split: json.loads(study.path(split).read_text()) for split in ['train', 'development']}
    for r in raw.values():
        if not r['complete']:
            raise ValueError('Incomplete study')
        study.verify(r)
    d = study.check(); selected = json.loads(study.path('selection').read_text())
    model = study.ROOT / f'models/sl_{study.NAME}_bundle.joblib'
    if selected['training_sha256'] != sha(study.path('train')) or selected['model_sha256'] != sha(model):
        raise ValueError('Model binding changed')
    actuals, best = replay(selected, raw['train']['labels'], raw['train']['manifests'])
    bundle = joblib.load(model)
    if bundle['default'] != 'O3' or bundle['training_sha256'] != selected['training_sha256'] or bundle['declaration_sha256'] != sha(study.DECLARATION):
        raise ValueError('Model bundle changed')
    clarification = study.ROOT / 'results/persistent_sl_protocol_clarification.json'
    clarified = json.loads(clarification.read_text())
    if (clarified['declaration_sha256'] != sha(study.DECLARATION) or clarified['training_sha256'] != sha(study.path('train'))
        or clarified['source_sha256'] != sha(study.ROOT / 'scripts/train_persistent.py')
        or clarified['source_sha256'] != sha(study.BASE / 'prefit/declared_sources/scripts/train_persistent.py')
        or bundle['protocol_clarification_sha256'] != sha(clarification)
        or selected['protocol_clarification_sha256'] != sha(clarification)
        or bundle['protocol'] != clarified['protocol'] or selected['protocol'] != clarified['protocol']):
        raise ValueError('Full-study protocol description changed')
    for key in ['blocks', 'pairs', 'cpu', 'control_tolerance', 'gain_floor', 'bootstrap_replicates', 'seed']:
        if clarified['protocol'][key] != d['protocol'][key]: raise ValueError('Numeric protocol changed')
    if best:
        selector = NativeSelector(*actuals[best]['parameters']).fit(raw['train']['labels'])
        for r in raw.values():
            for m in r['manifests'].values():
                if not predictions_equal(selector.choose(m), bundle['experimental'].choose(m)):
                    raise ValueError('Serialized selector differs')
    elif bundle['experimental'] is not None:
        raise ValueError('Unqualified selector stored')
    order_groups = 0
    for method, stats in pilot_raw['summary']['statistics'].items():
        for case, clocks in stats.items():
            rows = [r for r in pilot_raw['records'] if r['method'] == method and r['case'] == case]
            for clock, s in clocks.items():
                independent_order(rows, s, clock); order_groups += 1
    for case, clocks in controls['confirmation']['summary']['statistics'].items():
        rows = [r for r in controls['confirmation']['records'] if r['case'] == case]
        for clock, s in clocks.items():
            independent_order(rows, s, clock); order_groups += 1
    if controls['probe']['method'] is not None:
        for clock, stats in controls['probe']['summary']['statistics'].items():
            for role, _, _ in confirmation.ROLES:
                independent_order([r for r in controls['probe']['records'] if r['role'] == role], stats[role], clock); order_groups += 1
    for r in raw.values():
        for case, diagnostics in r['diagnostics'].items():
            groups = [('O3', 'qualification', diagnostics['baseline_controls'])]
            for choice, detail in diagnostics['measurements'].items():
                groups += [(choice, 'candidate_control', {c: detail[c]['control'] for c in ['cpu', 'wall']}),
                           (choice, 'effect', {c: detail[c]['effect'] for c in ['cpu', 'wall']})]
            for choice, role, clocks in groups:
                rows = [x for x in r['records'] if x['case'] == case and x['choice'] == choice and x['role'] == role]
                for clock, s in clocks.items():
                    independent_order(rows, s, clock); order_groups += 1
    train = raw['train']; rejected = {}
    mutations = {
        'missing_pair': lambda r: r['records'][0]['samples'].pop(),
        'starting_side': lambda r: r['records'][0]['samples'][0].update(left_first=not r['records'][0]['samples'][0]['left_first']),
        'missing_invocation_trace': lambda r: r['records'][0]['samples'][0]['clock_trace'].pop(),
        'aggregate_clock': lambda r: r['records'][0]['samples'][0]['left'].update(cpu_seconds=99.),
        'same_process': lambda r: r['records'][0].update(right_pid=r['records'][0]['left_pid']),
        'native_checksum': lambda r: r['correctness'][0]['samples'][0]['right'].update(checksum='bad'),
        'static_feature': lambda r: next(iter(r['manifests'].values()))['features']['O2'].__setitem__(0, 999.),
        'reported_gain': lambda r: next(iter(r['diagnostics'].values()))['baseline_controls']['cpu'].update(speedup=9.),
        'reported_order': lambda r: next(iter(r['diagnostics'].values()))['baseline_controls']['cpu'].update(
            order_pass=not next(iter(r['diagnostics'].values()))['baseline_controls']['cpu']['order_pass']),
        'missing_correctness': lambda r: r['correctness'].pop(),
    }
    for name, mutate in mutations.items():
        bad = copy.deepcopy(train); mutate(bad)
        with patch.object(study, 'check', return_value=d):
            try: study.verify(bad)
            except (ValueError, TypeError): rejected[name] = True
            else: raise ValueError('Corrupt evidence accepted: ' + name)
    native = 0
    for r in raw.values():
        for case, m in r['manifests'].items():
            for choice in study.region.MENU:
                # A different, frozen fresh-process collector independently
                # checks the artifacts used by the persistent study.
                study.region.run_cell(m, 'reference_O0', choice, 0, 'audit', pairs=1, repetitions=1); native += 1
    exported = study.ROOT / 'results/persistent_export'; e = json.loads((exported / 'manifest.json').read_text())
    m = raw['development']['manifests']['yyjson_flat']
    if e['decision']['choice'] != 'O3' or e['experimental'] or e['model_sha256'] != sha(model) or e['expected'] != m['expected']:
        raise ValueError('Default export changed')
    for name, original in {'program.bc': m['artifacts']['O3']['bc'], 'candidate.so': m['artifacts']['O3']['so'],
                           'isolated_library_worker.out': m['worker'], 'input.dat': m['input']}.items():
        if sha(exported / name) != sha(original) or sha(exported / name) != e['files_sha256'][name]:
            raise ValueError('Export artifact changed')
    result = subprocess.run(['taskset', '-c', '2', str(exported / 'isolated_library_worker.out'), str(exported / 'candidate.so'),
                             str(exported / 'input.dat'), '1'], check=True, capture_output=True, timeout=60)
    sample = json.loads(result.stdout)['sample']
    if {k: sample[k] for k in m['expected']} != m['expected']:
        raise ValueError('Independent export oracle failed')
    denied = study.ROOT / 'results/persistent_experimental_rejected'
    if best is None:
        if denied.exists(): raise ValueError('Denial path already exists')
        result = subprocess.run([sys.executable, str(study.ROOT / 'scripts/optimize_persistent.py'), '--case', 'yyjson_flat',
                                 '--experimental', '--output', str(denied)], capture_output=True, timeout=180)
        if result.returncode != 1 or b'No CV-qualified experimental model' not in result.stderr or denied.exists():
            raise ValueError('Unqualified export accepted')
    preserved = 0
    prior_zip = study.ROOT / 'results/region_iteration.zip'
    snapshot = json.loads((study.ROOT / 'results/region_snapshot.log').read_text())
    if sha(prior_zip) != snapshot['sha256']:
        raise ValueError('Prior immutable snapshot changed')
    with zipfile.ZipFile(prior_zip) as archive:
        if archive.testzip(): raise ValueError('Prior archive CRC failure')
        hashes = json.loads(archive.read('snapshot_manifest.json'))['sha256']
        for name, digest in hashes.items():
            if not name.startswith(('results/', 'data/', 'models/')):
                continue
            if sha(study.ROOT / name) != digest:
                raise ValueError('Prior generated evidence changed: ' + name)
            preserved += 1
    parsed = 0
    for directory in ['src', 'scripts', 'tests']:
        for source in (study.ROOT / directory).rglob('*.py'):
            ast.parse(source.read_text()); parsed += 1
    study.evaluate()
    save(output, {'native_O0_candidate_comparisons': native, 'CV_variants_replayed': len(actuals),
                  'fully_scorable_CV_variants': sum(v['eligible'] for v in actuals.values()),
                  'actual_side_clock_groups_independently_checked': order_groups, 'tamper_rejected': rejected,
                  'prior_generated_files_unchanged': preserved, 'python_sources_parsed': parsed,
                  'default_export_independent_oracle': True, 'uncertified_export_rejected': best is None,
                  'source_sha256': {split: sha(study.path(split)) for split in raw}, 'reserved_test_executions': 0})
    print(json.dumps(json.loads(output.read_text()), indent=2))


if __name__ == '__main__': main()
