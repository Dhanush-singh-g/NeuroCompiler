"""Export a small, static view of existing evidence; never run benchmarks.

Python's standard library is sufficient. Missing or invalid evidence stays
unavailable rather than being replaced with example data or performance scores.
"""
import argparse
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = 'results/expanded_native_20261012'
SETTINGS = ['O3', 'O2', 'O3_no_vector', 'O3_large_inline']
LABELS = {'jsonparser': 'json-parser', 'jsonh': 'json.h', 'blake2': 'BLAKE2',
          'sha256': 'B-Con SHA256', 'picohttp': 'picohttpparser', 'cjson': 'cJSON',
          'tinyexpr': 'TinyExpr', 'fastlz': 'FastLZ', 'mpack': 'MPack',
          'bzip2': 'BZip2', 'lz4': 'LZ4', 'lua': 'Lua', 'expat': 'Expat',
          'frozen': 'Frozen', 'monocypher': 'Monocypher', 'parson': 'Parson'}
GROUPS = {'zlib': 'Compression', 'lz4': 'Compression', 'bzip2': 'Compression',
          'miniz': 'Compression', 'fastlz': 'Compression', 'libdeflate': 'Compression',
          'blake2': 'Cryptography', 'sha256': 'Cryptography', 'monocypher': 'Cryptography',
          'lua': 'Interpreter', 'tinyexpr': 'Interpreter', 'expat': 'Parsing',
          'yxml': 'Parsing', 'inih': 'Parsing', 'picohttp': 'Parsing'}


def normalized_stat(raw, tolerance):
    """Check recorded summary gates; do not recompute timing labels or fit models."""
    ratio = float(raw['speedup'])
    interval = [float(x) for x in raw['interval']]
    blocks = [float(x) for x in raw['blocks']]
    order = float(raw['order_log_difference'])
    local_order = [float(x) for x in raw['block_order_log_differences']]
    values = [ratio, *interval, *blocks, order, *local_order]
    if len(interval) != 2 or len(blocks) != 3 or len(local_order) != 3:
        raise ValueError('Incomplete control summary')
    if not all(math.isfinite(x) for x in values) or min([ratio, *interval, *blocks]) <= 0:
        raise ValueError('Nonfinite or nonpositive ratio')
    if interval[0] > interval[1]:
        raise ValueError('Reversed interval')
    reasons = []
    if order > math.log1p(tolerance) or any(x > math.log1p(tolerance) for x in local_order):
        reasons.append('Starting-order bias')
    lo, hi = 1 / (1 + tolerance), 1 + tolerance
    if any(not lo <= x <= hi for x in blocks):
        reasons.append('Block outside tolerance')
    if not (interval[0] >= lo and interval[1] <= hi):
        reasons.append('Interval outside tolerance')
    passed = not reasons
    if raw['control_pass'] is not passed:
        raise ValueError('Control decision disagrees with recorded statistics')
    return {'ratio': ratio, 'interval': interval, 'blocks': blocks,
            'passed': passed, 'reasons': reasons}


def correctness_status(manifest, setting):
    raw = manifest.get('correctness', {}).get(setting)
    if not raw or len(raw.get('samples', [])) != 2:
        return 'unavailable'
    expected = manifest.get('expected')
    if not expected:
        return 'unavailable'
    for sample in raw['samples']:
        for side in ('left', 'right'):
            if any(sample.get(side, {}).get(k) != v for k, v in expected.items()):
                return 'failed'
    return 'passed'


def build_data(root):
    root = Path(root)
    sources, warnings = [], []

    def read(relative):
        path = root / relative
        if not path.is_file():
            sources.append({'path': relative, 'status': 'missing', 'sha256': None})
            warnings.append(relative + ': missing')
            return None
        content = path.read_bytes()
        sources.append({'path': relative, 'status': 'loaded',
                        'sha256': hashlib.sha256(content).hexdigest()})
        try:
            value = json.loads(content)
            if not isinstance(value, dict):
                raise ValueError('Expected JSON object')
            return value
        except (ValueError, UnicodeError) as error:
            sources[-1]['status'] = 'invalid'
            warnings.append(relative + ': ' + str(error))
            return None

    frozen = read(STUDY + '/frozen.json')
    preflight = read(STUDY + '/preflight.json')
    pins = read('results/expanded_source_pins.json') or {}
    gate = read(STUDY + '/gate.json')
    screen = read('results/expanded_target_screen.json')
    cpu0 = read('results/expanded_cpu0_screen.json')
    selection = read('results/persistent_native_20261011_selection.json')
    probe = read('results/persistent_probe.json')
    # The current declaration binds preflight and pins. If either changes,
    # display the affected section as unavailable rather than a stale success.
    for value, field, relative in ((preflight, 'preflight_sha256', STUDY + '/preflight.json'),
                                   (pins, 'source_pin_file_sha256', 'results/expanded_source_pins.json')):
        expected_hash = (frozen or {}).get(field)
        observed = next((s['sha256'] for s in sources if s['path'] == relative), None)
        if value is not None and expected_hash and observed != expected_hash:
            warnings.append(relative + ': differs from frozen declaration')
            if field == 'preflight_sha256':
                preflight = None
            else:
                pins = {}
    protocol = (frozen or {}).get('protocol', {})
    tolerance = protocol.get('control_tolerance', .03)
    programs = {}
    manifests = (preflight or {}).get('manifests', {})
    for case, m in manifests.items():
        program = m['program']
        item = programs.setdefault(program, {'id': program, 'name': LABELS.get(program, program),
            'category': GROUPS.get(program, 'JSON / serialization'), 'split': 'training', 'inputs': [],
            'pin': {k: pins.get(program, {}).get(k) for k in ('repository', 'commit', 'sha256', 'url')}})
        item['inputs'].append({'id': case, 'settings': {s: correctness_status(m, s) for s in SETTINGS},
            'eligible': m.get('eligible') is True,
            'feature_count': len(next(iter(m.get('features', {}).values()), [])),
            'input_sha256': m.get('input_sha256')})
    # Development sources are present, but their fixtures have never been executed.
    for case in (frozen or {}).get('development_cases', []):
        program = case.split('_', 1)[0]
        item = programs.setdefault(program, {'id': program, 'name': LABELS.get(program, program),
            'category': GROUPS.get(program, 'JSON / serialization'), 'split': 'development', 'inputs': [],
            'pin': {k: pins.get(program, {}).get(k) for k in ('repository', 'commit', 'sha256', 'url')}})
        item['inputs'].append({'id': case, 'settings': {s: 'unrun' for s in SETTINGS},
                               'eligible': None, 'feature_count': None, 'input_sha256': None})
    training = [p for p in programs.values() if p['split'] == 'training']
    coverage_complete = bool(preflight and preflight.get('complete') is True and not preflight.get('failures') and frozen and
                             set(manifests) == set(frozen.get('training_cases', [])))
    corpus = {'status': 'complete' if coverage_complete else 'unavailable',
              'training_programs': len(training) if coverage_complete else None,
              'training_inputs': len(manifests) if coverage_complete else None,
              'correctness_cells': sum(s == 'passed' for p in training for i in p['inputs']
                                      for s in i['settings'].values()) if coverage_complete else None,
              'development_programs': len(programs) - len(training) if frozen else None}
    targets = []
    cases = (frozen or {}).get('gate_cases', [])

    def add_target(cpu, stats, rows, source):
        try:
            if not cases or set(stats) != set(cases):
                raise ValueError('Incomplete admission cohort')
            normalized = {case: {clock: normalized_stat(stats[case][clock], tolerance)
                                for clock in ('cpu', 'wall')} for case in cases}
            counts = {clock: sum(x[clock]['passed'] for x in normalized.values()) for clock in ('cpu', 'wall')}
            targets.append({'cpu': cpu, 'counts': counts, 'total': len(cases), 'statistics': normalized,
                'admitted': all(n == len(cases) for n in counts.values()), 'source': source,
                'cells': len(rows), 'pairs': sum(len(r.get('samples', [])) for r in rows)})
        except (KeyError, TypeError, ValueError) as error:
            warnings.append(source + ': ' + str(error))

    if gate and gate.get('complete') is True and frozen:
        add_target(frozen['context']['native_cpu'], gate.get('summary', {}).get('statistics', {}),
                   gate.get('records', []), STUDY + '/gate.json')
    for raw, source in ((screen, 'results/expanded_target_screen.json'), (cpu0, 'results/expanded_cpu0_screen.json')):
        if raw and raw.get('complete') is True:
            for cpu, item in raw.get('summary', {}).get('targets', {}).items():
                add_target(int(cpu), item['statistics'], [r for r in raw['records'] if r['target_cpu'] == int(cpu)], source)
    targets.sort(key=lambda x: x['cpu'])
    measurement_complete = len(targets) == 5 and {t['cpu'] for t in targets} == set(range(5))
    # A passing screen would still need independent confirmation; admission alone
    # never certifies a model. This exporter never opens or runs holdout artifacts.
    measurement = {'status': ('failed' if all(not t['admitted'] for t in targets) else 'confirmation_required')
                   if measurement_complete else 'unavailable', 'targets': targets, 'cases': cases,
                   'cells': sum(t['cells'] for t in targets) if measurement_complete else None,
                   'pairs': sum(t['pairs'] for t in targets) if measurement_complete else None,
                   'tolerance': tolerance, 'source': STUDY + '/frozen.json'}
    model = {'status': 'unavailable', 'default': None, 'qualified_targets': None, 'configurations': None}
    if selection:
        model = {'status': 'qualified' if selection.get('cv_certified') is True else 'not_qualified',
                 'default': selection.get('default'), 'qualified_targets': selection.get('distinct_candidate_targets'),
                 'configurations': len(selection.get('experiments', {})), 'study': 'persistent_20261011',
                 'source': 'results/persistent_native_20261011_selection.json'}
    headroom = None
    if probe and probe.get('complete') is True:
        try:
            clocks = probe['summary']['statistics']
            if all(clocks[c].get('qualified') is True and clocks[c].get('confirmed_gain') is True for c in ('cpu', 'wall')):
                headroom = {c: {k: clocks[c]['effect'][k] for k in ('speedup', 'interval', 'blocks')} for c in ('cpu', 'wall')}
                headroom.update(case='blake2_random', setting='O3_no_vector',
                                cpu_time_reduction=100 * (1 - 1 / headroom['cpu']['speedup']),
                                source='results/persistent_probe.json', scope='Training-only headroom; excluded from model fitting')
        except (KeyError, TypeError, ZeroDivisionError) as error:
            warnings.append('results/persistent_probe.json: ' + str(error))
    return {'schema_version': 1, 'exported_at': datetime.now(timezone.utc).isoformat(),
            'study': 'expanded_20261012', 'recorded_at': (frozen or {}).get('declared_utc'),
            'context': {k: (frozen or {}).get('context', {}).get(k) for k in ('cpu_model', 'kernel', 'cpu_quota')},
            'settings': SETTINGS, 'active_choices': protocol.get('active_choices', []), 'corpus': corpus,
            'programs': sorted(programs.values(), key=lambda x: (x['split'] != 'training', x['name'].lower())),
            'measurement': measurement, 'model': model, 'headroom': headroom, 'warnings': warnings,
            'sources': sources, 'reports': ['EXPANDED_SL.md', 'PERSISTENT_SL.md', 'FINAL_ASSESSMENT.md']}


def export(root, output):
    output = Path(output)
    data = build_data(root)
    output.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, allow_nan=False)
    (output / 'data.json').write_text(serialized + '\n')
    # Bundled script supports file:// demos without fetch or a backend.
    (output / 'results.js').write_text('window.NEURO_RESULTS = ' + serialized.replace('<', '\\u003c') + ';\n')
    (output / 'reports').mkdir(exist_ok=True)
    for report in data['reports']:
        source = Path(root) / report
        target = output / 'reports' / report
        if source.is_file():
            shutil.copyfile(source, target)
        else:
            target.unlink(missing_ok=True)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=ROOT / 'dashboard')
    args = parser.parse_args()
    data = export(args.root, args.output)
    print(json.dumps({'output': str(args.output), 'corpus': data['corpus'],
                      'measurement_status': data['measurement']['status'], 'warnings': data['warnings']}, indent=2))


if __name__ == '__main__':
    main()
