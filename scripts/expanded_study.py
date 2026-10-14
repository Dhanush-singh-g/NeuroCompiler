"""Portable source rebuild, bounded machine gate, then a frozen native SL study."""
import argparse
import copy
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmarks import expanded as e
from src.benchmarks.compact import save, sha
from src.benchmarks.persistent import validate
from src.benchmarks.region import clock_effect, summarize

PARAMETERS = [(a, l, f, 'ridge', 3) for a in [1., 10.] for l in [False, True] for f in [.01, .03]]
PARAMETERS += [(10., l, f, 'forest', d) for d in [3, 6] for l in [False, True] for f in [.01, .03]]
SOURCE_NAMES = ['scripts/expanded_study.py', 'src/benchmarks/expanded.py', 'src/benchmarks/expanded_drivers.py',
                'src/supervised/expanded.py', 'src/supervised/region.py', 'src/supervised/frozen.py',
                'src/benchmarks/persistent.py', 'src/benchmarks/persistent_library_worker.c',
                'src/benchmarks/invocation_worker.c', 'src/benchmarks/region.py', 'src/benchmarks/compact.py',
                'src/benchmarks/polybench.py', 'src/benchmarks/real.py', 'src/benchmarks/kernels.py',
                'src/benchmarks/broad.py', 'src/benchmarks/invocation.py', 'src/features/timed_region.py', 'src/features/transform.py']


def sources(): return {name: sha(e.ROOT / name) for name in SOURCE_NAMES}


def preflight(base, cpu, llvm, repair):
    tools = e.Toolchain(llvm); ctx = e.context(tools, cpu); decl = base / 'declaration.json'
    if (base / 'frozen.json').exists(): raise ValueError('Frozen study; preflight cannot change it')
    if not decl.exists():
        base.mkdir(parents=True, exist_ok=False); save(decl, {'context': ctx, 'phase': 'preflight; no fit labels', 'source_pins': e.source_pins()})
        e.compile_worker(base, tools)
    elif json.loads(decl.read_text())['context'] != ctx:
        raise ValueError('Different machine/toolchain/affinity; use a new context directory')
    path = base / 'preflight.json'
    raw = json.loads(path.read_text()) if path.exists() else {'manifests': {}, 'failures': {}, 'complete': False}
    programs = list(dict.fromkeys(c.split('_')[0] for c in e.TRAIN_CASES))
    for program in programs:
        cases = [c for c in e.TRAIN_CASES if c.split('_')[0] == program]
        if all(c in raw['manifests'] for c in cases): continue
        if program in raw['failures']:
            if not repair: continue
            directory = base / 'programs' / program
            backup = base / 'failed_builds' / (program + '_' + str(len(list((base / 'failed_builds').glob(program + '_*')))))
            backup.parent.mkdir(exist_ok=True); shutil.move(str(directory), str(backup)); del raw['failures'][program]
            for case in cases: raw['manifests'].pop(case, None)
        try:
            m = e.compile_program(base, program, tools)
            for case in cases:
                raw['manifests'][case] = e.prepare_case(base, m, case)
                save(path, raw); print('Correct', case, 'all four pipelines; independent oracle; eligible', raw['manifests'][case]['eligible'], flush=True)
        except Exception as exc:
            raw['failures'][program] = {'type': type(exc).__name__, 'message': str(exc),
                'stderr': (getattr(exc, 'stderr', b'') or b'').decode(errors='replace')}
            print('Preflight failure', program, raw['failures'][program], flush=True)
        save(path, raw)
    raw['complete'] = len(raw['manifests']) == len(e.TRAIN_CASES) and not raw['failures']; save(path, raw)
    print('Preflight', len(raw['manifests']), 'of', len(e.TRAIN_CASES), 'inputs;', len(raw['failures']), 'failed implementations', flush=True)


def declare(base):
    path = base / 'frozen.json'
    if path.exists(): raise ValueError('Existing formal declaration')
    raw = json.loads((base / 'preflight.json').read_text()); context = json.loads((base / 'declaration.json').read_text())['context']
    if not raw['complete'] or set(raw['manifests']) != set(e.TRAIN_CASES): raise ValueError('Training preflight incomplete')
    hashes = sources()
    for name in hashes:
        dest = base / 'declared_sources' / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(e.ROOT / name, dest)
    save(path, {'declared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'context': context,
        'protocol': e.PROTOCOL, 'source_sha256': hashes, 'source_pins': e.source_pins(), 'source_pin_file_sha256': sha(e.SOURCE_PINS),
        'preflight_sha256': sha(base / 'preflight.json'), 'worker_sha256': sha(base / 'persistent_library_worker.out'),
        'training_cases': e.TRAIN_CASES, 'formal_cases': e.PRIMARY_CASES, 'development_cases': e.DEVELOPMENT_CASES,
        'gate_cases': e.GATE_CASES, 'parameters': PARAMETERS,
        'previously_opened': 'Monocypher/yyjson are now training; no earlier clock is reused',
        'fresh_development': 'json.h and libdeflate sources only; no native build/execution before model freeze',
        'budget': 'one six-case machine gate, one independent confirmation if gate passes; full formal study only if both pass; no replacements/retries',
        'selection': 'unchanged 16 parameters, whole-program CV utility>0, worst program>=0.97, >=1 confirmed gain; default O3',
        'formal_menu': e.ACTIVE, 'build_menu': list(e.MENU), 'inline_status': 'large-inline correctness/features only; never predict an unmeasured menu setting'})
    check(base); print('Frozen 21 original training implementations, 42 correctness inputs, 21 formal inputs, 2 fresh development implementations', flush=True)


def check(base):
    d = json.loads((base / 'frozen.json').read_text())
    if (d['protocol'] != e.PROTOCOL or d['source_sha256'] != sources() or d['source_pins'] != e.source_pins()
        or d['source_pin_file_sha256'] != sha(e.SOURCE_PINS) or d['preflight_sha256'] != sha(base / 'preflight.json')
        or d['worker_sha256'] != sha(base / 'persistent_library_worker.out')
        or d['parameters'] != [list(p) for p in PARAMETERS] or d['formal_cases'] != e.PRIMARY_CASES
        or d['training_cases'] != e.TRAIN_CASES or d['development_cases'] != e.DEVELOPMENT_CASES or d['gate_cases'] != e.GATE_CASES):
        raise ValueError('Frozen source/protocol/provenance changed')
    for name, digest in d['source_sha256'].items():
        if sha(base / 'declared_sources' / name) != digest: raise ValueError('Archived source changed')
    for pin in d['source_pins'].values():
        if sha(e.ROOT / pin['archive']) != pin['sha256']: raise ValueError('Upstream archive changed')
    current = e.context(e.Toolchain(), d['context']['native_cpu'])
    for key in ['architecture', 'cpu_model', 'cpu_flags', 'tools']:
        if current[key] != d['context'][key]: raise ValueError('Changed native target; rebuild in a fresh context')
    for m in json.loads((base / 'preflight.json').read_text())['manifests'].values():
        verify_manifest(base, m)
    return d


def verify_manifest(base, m):
    if sha(base / m['input']) != m['input_sha256']: raise ValueError('Input changed')
    for artifact in m['artifacts'].values():
        for field in ['bc', 'so']:
            if sha(base / artifact[field]) != artifact[field + '_sha256']: raise ValueError('Native artifact changed')
    if sha(base / m['initial']) != m['initial_sha256']: raise ValueError('Initial bitcode changed')
    for path, digest in m['sources'].items():
        if sha(base / path) != digest: raise ValueError('Native source changed')
    for c, row in m['correctness'].items():
        if row['left'] != 'reference_O0' or row['right'] != c: raise ValueError('Correctness comparison changed')
        validate(row, m, 2, 1, row['first'], 'micro')
    if set(m['correctness']) != set(e.MENU): raise ValueError('Missing correctness setting')
    if m['program'] != m['id'].split('_')[0]: raise ValueError('Program group changed')
    for c in e.MENU:
        if m['aliases'][c] != next(k for k in e.MENU if m['artifacts'][c]['so_sha256'] == m['artifacts'][k]['so_sha256']):
            raise ValueError('Executable alias changed')


def schedule(cases, seed):
    rng = np.random.default_rng(seed)
    return [{'case': cases[i], 'block': b} for b in range(e.PROTOCOL['blocks']) for i in rng.permutation(len(cases))]


def gate_summary(raw):
    statistics = {case: {clock: clock_effect([r for r in raw['records'] if r['case'] == case], clock)
                        for clock in ['cpu', 'wall']} for case in e.GATE_CASES}
    coverage = {clock: sum(s[clock]['control_pass'] for s in statistics.values()) for clock in ['cpu', 'wall']}
    return {'statistics': statistics, 'coverage': coverage, 'passed': all(n == len(e.GATE_CASES) for n in coverage.values()),
            'fit_targets': 0, 'scope': 'machine admission only, never compiler/model labels'}


def verify_rows(base, raw, expected_schedule, seed):
    d = check(base)
    if raw['declaration_sha256'] != sha(base / 'frozen.json') or len(raw['records']) > len(expected_schedule): raise ValueError('Result binding/coverage changed')
    if raw['complete'] and len(raw['records']) != len(expected_schedule): raise ValueError('Incomplete formal schedule')
    for row, item in zip(raw['records'], expected_schedule):
        if any(row[k] != v for k, v in item.items()): raise ValueError('Schedule changed')
        m = raw['manifests'][row['case']]; validate(row, m, e.PROTOCOL['pairs'], m['repetitions'], row['first'], 'micro')
        if row['method'] != 'micro' or row['case'] != m['id']: raise ValueError('Method/case changed')
        if not np.isfinite(row['process_elapsed_seconds']) or row['process_elapsed_seconds'] <= 0 or any(v < 0 for v in row['scheduler_delta'].values()):
            raise ValueError('Scheduler/process clocks invalid')
        cell_seed = seed + int(hashlib.sha256(f'{m["id"]}:micro:{row["block"]}:{row["left"]}:{row["right"]}'.encode()).hexdigest()[:8], 16)
        if row['first'] != bool(np.random.default_rng(cell_seed).integers(2)): raise ValueError('Starting side changed')
    return d


def gate(base, stage, resume):
    check(base); source = json.loads((base / 'preflight.json').read_text()); seed = e.PROTOCOL['order_seed'] + int(stage == 'confirmation')
    path = base / (stage + '.json')
    if stage == 'confirmation':
        g = json.loads((base / 'gate.json').read_text())
        verify_gate(base, g, 'gate')
        if not g['summary']['passed']: raise ValueError('Machine gate failed; no confirmation or SL sampling')
    plan = [{**item, 'left': 'O3', 'right': 'O3', 'role': 'qualification'} for item in schedule(e.GATE_CASES, seed)]
    raw = json.loads(path.read_text()) if path.exists() else {'declaration_sha256': sha(base / 'frozen.json'),
        'manifests': {c: source['manifests'][c] for c in e.GATE_CASES}, 'records': [], 'complete': False}
    if path.exists():
        if not resume: raise ValueError('Existing machine gate; use --resume')
        verify_gate(base, raw, stage)
        if raw['complete']: print('Verified complete', stage, '; no new clocks'); return
    for item in plan[len(raw['records']):]:
        m = raw['manifests'][item['case']]
        if not m['eligible']: raise ValueError('Declared gate input below minimum duration; cannot substitute')
        row = e.run(base, m, item['block'], seed=seed); raw['records'].append(row); save(path, raw)
        print(stage, item['block']+1, item['case'], flush=True)
    raw['summary'] = gate_summary(raw); raw['complete'] = True; verify_gate(base, raw, stage); save(path, raw)
    print(json.dumps({k: v for k, v in raw['summary'].items() if k != 'statistics'}, indent=2), flush=True)


def verify_gate(base, raw, stage):
    seed = e.PROTOCOL['order_seed'] + int(stage == 'confirmation')
    plan = [{**item, 'left': 'O3', 'right': 'O3', 'role': 'qualification'} for item in schedule(e.GATE_CASES, seed)]
    verify_rows(base, raw, plan, seed)
    expected = json.loads((base / 'preflight.json').read_text())['manifests']
    if raw['manifests'] != {c: expected[c] for c in e.GATE_CASES}: raise ValueError('Gate manifest changed')
    if raw['complete'] and raw['summary'] != gate_summary(raw): raise ValueError('Reported admission changed')


def admitted(base):
    for stage in ['gate', 'confirmation']:
        raw = json.loads((base / (stage + '.json')).read_text()); verify_gate(base, raw, stage)
        if not raw['complete'] or not raw['summary']['passed']: raise ValueError('Native timing target not admitted; no training labels')


def candidate_plan(raw, seed):
    result = []; cases = list(raw['manifests']); rng = np.random.default_rng(seed + 5)
    for block in range(e.PROTOCOL['blocks']):
        for i in rng.permutation(len(cases)):
            case = cases[i]; m = raw['manifests'][case]
            q = [r for r in raw['records'] if r['case'] == case and r['role'] == 'qualification']
            if not m['eligible'] or not clock_effect(q, 'cpu')['control_pass']: continue
            choices = e.ACTIVE if raw['split'] == 'train' else ['O3', raw['decisions'][case]['choice']]
            for c in dict.fromkeys(m['aliases'][c] for c in choices):
                if c == 'O3': continue
                roles = [('candidate_control', c, c), ('effect', 'O3', c)]
                if block % 2: roles.reverse()
                for role, left, right in roles: result.append({'case': case, 'block': block, 'choice': c, 'role': role, 'left': left, 'right': right})
    return result


def verify_study(base, raw):
    if raw.get('gate_sha256') != sha(base / 'gate.json') or raw.get('confirmation_sha256') != sha(base / 'confirmation.json'):
        raise ValueError('Admission evidence changed')
    if raw['split'] not in ['train', 'development']: raise ValueError('Unknown split')
    if raw['split'] == 'train':
        manifests = json.loads((base / 'preflight.json').read_text())['manifests']
        if raw['manifests'] != {c: manifests[c] for c in e.PRIMARY_CASES} or raw['active_choices'] != {c: e.ACTIVE for c in e.PRIMARY_CASES}:
            raise ValueError('Frozen training inputs/features/menu changed')
    else:
        import joblib
        from src.supervised.frozen import predictions_equal
        selected = json.loads((base / 'selection.json').read_text())
        if sha(base / 'selection.json') != raw['selection_sha256'] or sha(base / 'model.joblib') != selected['model_sha256'] or sha(base / 'train.json') != selected['training_sha256']:
            raise ValueError('Frozen selection changed')
        bundle = joblib.load(base / 'model.joblib')
        if set(raw['manifests']) != set(e.DEVELOPMENT_CASES): raise ValueError('Fresh development coverage changed')
        for case, m in raw['manifests'].items():
            verify_manifest(base, m)
            if (base / m['input']).read_bytes() != e.input_bytes(case) or m['expected'] != e.expected(case): raise ValueError('Independent development oracle changed')
            program = json.loads((base / 'programs' / m['program'] / 'manifest.json').read_text())
            if m['artifacts'] != program['artifacts'] or m['features'] != {c: v + e.region.input_features((base / m['input']).read_bytes()) for c, v in program['features'].items()}:
                raise ValueError('Fresh native features/artifacts changed')
            decision = bundle['experimental'].choose(m) if bundle['experimental'] else {'choice': 'O3', 'scores': {}}
            if not predictions_equal(decision, raw['decisions'][case]): raise ValueError('Frozen development recommendation changed')
        if raw['active_choices'] != {c: ['O3', v['choice']] for c, v in raw['decisions'].items()}:
            raise ValueError('Development measurement menu changed')
    seed = e.PROTOCOL['order_seed'] + 10 + int(raw['split'] == 'development')
    plan = [{**item, 'role': 'qualification', 'choice': 'O3', 'left': 'O3', 'right': 'O3'}
            for item in schedule(list(raw['manifests']), seed) if raw['manifests'][item['case']]['eligible']]
    if len(raw['records']) >= len(plan): plan += candidate_plan(raw, seed)
    verify_rows(base, raw, plan, seed)
    labels, diagnostics = summarize(raw)
    if raw['complete'] and (raw.get('labels') != labels or raw.get('diagnostics') != diagnostics): raise ValueError('Study outcomes changed')
    return labels, diagnostics


def collect(base, split, resume):
    d = check(base); admitted(base); path = base / (split + '.json'); seed = e.PROTOCOL['order_seed'] + 10 + int(split == 'development')
    if path.exists():
        if not resume: raise ValueError('Existing study; use --resume')
        raw = json.loads(path.read_text()); verify_study(base, raw)
        if raw['complete']: print('Verified complete', split, '; no new clocks'); return
    else:
        if split == 'train':
            manifests = json.loads((base / 'preflight.json').read_text())['manifests']; manifests = {c: manifests[c] for c in e.PRIMARY_CASES}
            decisions = None
        else:
            import joblib
            selection = json.loads((base / 'selection.json').read_text()); model = base / 'model.joblib'
            if sha(model) != selection['model_sha256'] or sha(base / 'train.json') != selection['training_sha256']: raise ValueError('Frozen model changed')
            bundle = joblib.load(model); manifests = {}; tools = e.Toolchain()
            for p in e.NEW_DEVELOPMENT:
                prepared = e.compile_program(base, p, tools)
                for v in e.VARIANTS[p]: manifests[p+'_'+v] = e.prepare_case(base, prepared, p+'_'+v)
            decisions = {c: bundle['experimental'].choose(m) if bundle['experimental'] else {'choice': 'O3', 'scores': {}} for c, m in manifests.items()}
        raw = {'split': split, 'declaration_sha256': sha(base / 'frozen.json'), 'manifests': manifests,
               'records': [], 'complete': False, 'active_choices': {c: e.ACTIVE for c in manifests},
               'gate_sha256': sha(base / 'gate.json'), 'confirmation_sha256': sha(base / 'confirmation.json')}
        if decisions is not None:
            raw.update(decisions=decisions, active_choices={c: ['O3', v['choice']] for c, v in decisions.items()}, selection_sha256=sha(base / 'selection.json'))
        save(path, raw)
    plan = [{**item, 'role': 'qualification', 'choice': 'O3', 'left': 'O3', 'right': 'O3'} for item in schedule(list(raw['manifests']), seed)
            if raw['manifests'][item['case']]['eligible']]
    def cell(item):
        row = e.run(base, raw['manifests'][item['case']], item['block'], item['left'], item['right'], seed=seed)
        row.update(role=item['role'], choice=item['choice']); raw['records'].append(row); save(path, raw)
        print(split, item['block']+1, item['case'], item['role'], item['choice'], flush=True)
    for item in plan[len(raw['records']):]: cell(item)
    plan += candidate_plan(raw, seed)
    for item in plan[len(raw['records']):]: cell(item)
    raw['labels'], raw['diagnostics'] = summarize(raw); raw['complete'] = True; verify_study(base, raw); save(path, raw)
    print('Completed', split, len(raw['labels']), 'baseline-qualified inputs', flush=True)


def fit(base):
    import joblib
    from src.supervised.expanded import Selector, cv
    from src.supervised.region import training_rows
    d = check(base); admitted(base); output = base / 'selection.json'; model = base / 'model.joblib'
    if output.exists() or model.exists(): raise ValueError('Frozen selection exists')
    raw = json.loads((base / 'train.json').read_text()); labels, _ = verify_study(base, raw)
    if not raw['complete']: raise ValueError('Incomplete training')
    experiments = {str(i): {'parameters': list(p), **cv(labels, raw['manifests'], *p)} for i, p in enumerate(PARAMETERS)}
    accepted = [k for k, v in experiments.items() if v['eligible'] and v['score']['utility'] > 0 and v['score']['worst_original_program'] >= .97 and v['score']['confirmed_workloads'] >= 1]
    best = max(accepted, key=lambda k: experiments[k]['score']['utility']) if accepted else None
    selector = Selector(*experiments[best]['parameters']).fit(labels) if best else None
    joblib.dump({'default': 'O3', 'experimental': selector, 'training_sha256': sha(base / 'train.json'), 'declaration_sha256': sha(base / 'frozen.json'), 'protocol': e.PROTOCOL}, model)
    save(output, {'training_sha256': sha(base / 'train.json'), 'model_sha256': sha(model), 'experiments': experiments,
                 'experimental': best, 'default': 'O3', 'distinct_targets': len(training_rows(labels, False))})
    print('Frozen model', best, 'default O3', flush=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['prepare', 'declare', 'gate', 'confirmation', 'train', 'fit', 'development', 'verify'])
    p.add_argument('--output', required=True, type=Path); p.add_argument('--cpu', type=int, default=2); p.add_argument('--llvm-bin')
    p.add_argument('--resume', action='store_true'); p.add_argument('--repair', action='store_true'); args = p.parse_args()
    base = args.output.resolve()
    if args.llvm_bin: os.environ['NEUROCOMPILER_LLVM19'] = str(Path(args.llvm_bin).resolve())
    if args.action == 'prepare': preflight(base, args.cpu, args.llvm_bin, args.repair)
    elif args.action == 'declare': declare(base)
    elif args.action in ['gate', 'confirmation']: gate(base, args.action, args.resume)
    elif args.action in ['train', 'development']: collect(base, args.action, args.resume)
    elif args.action == 'fit': fit(base)
    else:
        check(base)
        for stage in ['gate', 'confirmation']:
            path = base / (stage + '.json')
            if path.exists(): verify_gate(base, json.loads(path.read_text()), stage)
        for split in ['train', 'development']:
            path = base / (split + '.json')
            if path.exists(): verify_study(base, json.loads(path.read_text()))
        print('Verified existing evidence; no sampling', flush=True)


if __name__ == '__main__': main()
