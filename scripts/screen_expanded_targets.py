"""One bounded screen of unused logical CPUs, then one independent confirmation.

CPU2's failed study is immutable. This diagnostic selects a measurement target,
not compiler settings; no screen/confirmation clock becomes a training label.
"""
import argparse
import datetime
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import expanded_study as study
from src.benchmarks import expanded as e
from src.benchmarks.compact import save, sha
from src.benchmarks.persistent import run, validate
from src.benchmarks.region import clock_effect

CPUS = [1, 3, 4]
SEED = 20261020
DECL = e.ROOT / 'results/expanded_target_declaration.json'
OUT = e.ROOT / 'results/expanded_target_screen.json'
CONFIRM = e.ROOT / 'results/expanded_target_confirmation.json'


def plan():
    rng = np.random.default_rng(SEED); result = []
    for block in range(3):
        for cpu in rng.permutation(CPUS):
            for i in rng.permutation(len(e.GATE_CASES)):
                result.append({'target_cpu': int(cpu), 'case': e.GATE_CASES[i], 'block': block})
    return result


def declare(base):
    if DECL.exists() or OUT.exists(): raise ValueError('Existing target screen; no retries')
    d = study.check(base); gate = json.loads((base/'gate.json').read_text()); study.verify_gate(base, gate, 'gate')
    if gate['summary']['passed']: raise ValueError('Current target already admitted; no screen needed')
    processor_flags = {}
    for section in Path('/proc/cpuinfo').read_text().strip().split('\n\n'):
        values = dict(line.split(':', 1) for line in section.splitlines() if ':' in line)
        values = {k.strip(): v.strip() for k, v in values.items()}
        if 'processor' in values: processor_flags[int(values['processor'])] = values.get('flags', '')
    if any(processor_flags.get(cpu) != d['context']['cpu_flags'] for cpu in CPUS):
        raise ValueError('Different instruction-set flags; fresh target-specific builds required')
    if d['context']['native_cpu'] in CPUS: raise ValueError('Do not retry the failed CPU')
    save(DECL, {'declared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base': str(base),
        'base_declaration_sha256': sha(base/'frozen.json'), 'failed_gate_sha256': sha(base/'gate.json'),
        'source_sha256': sha(Path(__file__)), 'cpus': CPUS, 'schedule': plan(), 'seed': SEED,
        'reuse': 'same freshly source-built binaries and even prior-calibrated counts on identical-ISA logical CPUs of this machine; no old clocks fit',
        'gate': 'all six CPU AND wall null controls; one fixed 54-cell screen; no CPU2 timing; no retries',
        'selection': 'eligible CPU with largest minimum control margin across both clocks/all cases; lowest CPU ID on ties',
        'confirmation_budget': 'one independent 18-cell check on selected CPU; all six controls each clock required; no alternate CPU if it fails',
        'fit_targets': 0})
    shutil.copy2(Path(__file__), base/'declared_sources/scripts/screen_expanded_targets.py')


def check():
    d = json.loads(DECL.read_text()); base = Path(d['base']); study.check(base)
    if (d['source_sha256'] != sha(Path(__file__)) or d['source_sha256'] != sha(base/'declared_sources/scripts/screen_expanded_targets.py')
        or d['base_declaration_sha256'] != sha(base/'frozen.json') or d['failed_gate_sha256'] != sha(base/'gate.json')
        or d['schedule'] != plan() or d['cpus'] != CPUS or d['seed'] != SEED): raise ValueError('Frozen target protocol/source changed')
    return d, base


def statistics(raw, cpus):
    results = {}
    for cpu in cpus:
        stats = {case: {clock: clock_effect([r for r in raw['records'] if r['target_cpu'] == cpu and r['case'] == case], clock)
                        for clock in ['cpu', 'wall']} for case in e.GATE_CASES}
        coverage = {clock: sum(v[clock]['control_pass'] for v in stats.values()) for clock in ['cpu', 'wall']}
        margins = []
        for clocks in stats.values():
            for s in clocks.values():
                margins += [math.log1p(.03)-abs(math.log(v)) for v in s['blocks']+s['interval']]
                margins += [math.log1p(.03)-v for v in [s['order_log_difference'], *s['block_order_log_differences']]]
        results[str(cpu)] = {'statistics': stats, 'coverage': coverage, 'passed': all(v == 6 for v in coverage.values()), 'minimum_margin': min(margins)}
    eligible = [cpu for cpu in cpus if results[str(cpu)]['passed']]
    selected = max(eligible, key=lambda c: (results[str(c)]['minimum_margin'], -c)) if eligible else None
    return {'targets': results, 'selected_cpu': selected, 'fit_targets': 0, 'scope': 'measurement-target qualification only'}


def verify(raw, confirmation=False):
    d, base = check(); preflight = json.loads((base/'preflight.json').read_text())['manifests']
    if raw['declaration_sha256'] != sha(DECL): raise ValueError('Result binding changed')
    if confirmation:
        screen = json.loads(OUT.read_text()); verify(screen)
        if raw['screen_sha256'] != sha(OUT): raise ValueError('Screen changed before confirmation')
        cpu = screen['summary']['selected_cpu']
        schedule = [{**v, 'target_cpu': cpu} for v in study.schedule(e.GATE_CASES, SEED+100)] if cpu is not None else []
        cpus = [cpu] if cpu is not None else []
    else: schedule = d['schedule']; cpus = CPUS
    if len(raw['records']) > len(schedule) or (raw['complete'] and len(raw['records']) != len(schedule)): raise ValueError('Target schedule coverage changed')
    for row, item in zip(raw['records'], schedule):
        if any(row[k] != v for k, v in item.items()): raise ValueError('Target schedule changed')
        m = preflight[row['case']]; validate(row, m, 24, m['repetitions'], row['first'], 'micro')
        if row['left'] != 'O3' or row['right'] != 'O3' or row['role'] != 'qualification': raise ValueError('Not a null control')
    if raw['complete'] and raw['summary'] != statistics(raw, cpus): raise ValueError('Target qualification changed')
    return schedule, base


def collect(confirmation, resume):
    d, base = check(); output = CONFIRM if confirmation else OUT
    preflight = json.loads((base/'preflight.json').read_text())['manifests']
    if output.exists():
        if not resume: raise ValueError('Existing target check; use --resume')
        raw = json.loads(output.read_text()); verify(raw, confirmation)
        if raw['complete']: print('Verified complete target check; no new timing'); return
    else:
        raw = {'declaration_sha256': sha(DECL), 'records': [], 'complete': False}
        if confirmation: raw['screen_sha256'] = sha(OUT)
        save(output, raw)
    schedule, base = verify(raw, confirmation)
    for item in schedule[len(raw['records']):]:
        m = e.resolved(base, preflight[item['case']]); cpu = item['target_cpu']
        row = run(m, 'micro', base/'persistent_library_worker.out', item['block'], SEED+cpu*1000+int(confirmation)*100,
                  pairs=24, cpu=cpu)
        row['target_cpu'] = cpu; raw['records'].append(row); save(output, raw)
        print('target', cpu, item['block']+1, item['case'], flush=True)
    cpus = [json.loads(OUT.read_text())['summary']['selected_cpu']] if confirmation and schedule else [] if confirmation else CPUS
    raw['summary'] = statistics(raw, cpus); raw['complete'] = True; verify(raw, confirmation); save(output, raw)
    print(json.dumps({'coverage': {c: v['coverage'] for c, v in raw['summary']['targets'].items()}, 'selected_cpu': raw['summary']['selected_cpu']}, indent=2))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--declare', action='store_true'); p.add_argument('--base', type=Path)
    p.add_argument('--confirmation', action='store_true'); p.add_argument('--resume', action='store_true'); a = p.parse_args()
    if a.declare:
        if a.base is None: raise ValueError('--base required')
        declare(a.base.resolve())
    else: collect(a.confirmation, a.resume)


if __name__ == '__main__': main()
