"""Fresh SL labels after independent method confirmation; old studies immutable.

Same fixed region features/menu/models. Previously executed development inputs
are explicitly repeated development, never a fresh final test. Pilot/probe and
all earlier clocks are excluded from fitting.
"""
import argparse
import copy
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import confirm_persistent as confirmation
from scripts import measure_persistent as pilot
from src.benchmarks import region
from src.benchmarks.compact import save, sha
from src.benchmarks.persistent import run, validate, clock_effect
from src.supervised.region import NativeSelector, program_cv, program_score, training_rows
from src.supervised.frozen import predictions_equal

ROOT = region.ROOT
NAME = 'persistent_native_20261011'
DECLARATION = ROOT / 'results/persistent_sl_declaration.json'
BASE = ROOT / 'data/processed/persistent19/sl_20261011'
SEED = 20261107
PARAMETERS = [(a, l, f, 'ridge', 3) for a in [1., 10.] for l in [False, True] for f in [.01, .03]]
PARAMETERS += [(10., l, f, 'forest', d) for d in [3, 6] for l in [False, True] for f in [.01, .03]]


def path(kind):
    return ROOT / f'results/{NAME}_{kind}.json'


def prior(split):
    source = ROOT / f'results/{region.NAME}_{split}.json'
    raw = json.loads(source.read_text()); region.verify(raw)
    if not raw['complete']:
        raise ValueError('Prior build/source verification incomplete')
    manifests = copy.deepcopy(raw['manifests'])
    for m in manifests.values():
        m['repetitions'] += m['repetitions'] % 2
        # Retain provenance separately; no old timing record is a fit input.
        m.pop('correctness', None); m.pop('calibration', None)
    return manifests


def declare():
    if DECLARATION.exists() or path('train').exists():
        raise ValueError('Existing SL study')
    _, output = confirmation.paths('confirmation')
    raw = json.loads(output.read_text()); confirmation.verify('confirmation', raw)
    if not raw['complete'] or not raw['summary']['passed']:
        raise ValueError('Independent method confirmation failed; no SL collection')
    sources = ['scripts/study_persistent.py', 'src/supervised/region.py', 'src/supervised/frozen.py']
    hashes = {name: sha(ROOT / name) for name in sources}
    for name in sources:
        dest = BASE / 'declared_sources' / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    d = {'declared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'confirmation_sha256': sha(output), 'method': raw['method'], 'seed': SEED,
         'protocol': pilot.PILOT_PROTOCOL, 'parameters': PARAMETERS, 'menu': list(region.MENU),
         'source_sha256': hashes, 'worker': pilot.check_declaration_local()['worker'],
         'prior_dataset_sha256': {split: sha(ROOT / f'results/{region.NAME}_{split}.json') for split in ['train', 'development']},
         'manifests': {split: prior(split) for split in ['train', 'development']},
         'training_cases': region.CASES, 'development_cases': region.DEVELOPMENT,
         'split_policy': '13 original training implementations / 26 inputs; Monocypher/yyjson are explicitly repeated development; no fresh final-test claim',
         'label_policy': 'only new qualified train effects; exclude every pilot, confirmation, probe, correctness and earlier runtime sample',
         'collection_policy': 'new same-file controls and effect traces; three blocks of 24 pairs; no rejected-control replacement',
         'model_gate': 'unchanged original-program CV; positive utility, worst program >=0.97x and at least one confirmed gain; O3 default',
         'correctness': 'fresh native O0 versus each candidate and independent oracle, before formal split collection; timings excluded',
         'context': {'cpu': 2, 'orchestration_cpu': 0, 'architecture': 'x86_64', 'compiler': 'LLVM19.1.7',
                     'native_artifacts': 'existing verified Intel Xeon 8573C builds; not portable across CPU feature sets'}}
    save(DECLARATION, d); check(); print('Declared new 26-input SL study and four repeated-development inputs')


def check():
    d = json.loads(DECLARATION.read_text())
    _, output = confirmation.paths('confirmation'); raw = json.loads(output.read_text())
    confirmation.verify('confirmation', raw)
    if (sha(output) != d['confirmation_sha256'] or not raw['summary']['passed'] or d['method'] != raw['method']
        or d['seed'] != SEED or d['protocol'] != pilot.PILOT_PROTOCOL or d['parameters'] != [list(p) for p in PARAMETERS]
        or d['menu'] != list(region.MENU) or d['training_cases'] != region.CASES or d['development_cases'] != region.DEVELOPMENT):
        raise ValueError('SL declaration/protocol changed')
    if d['worker'] != pilot.check_declaration_local()['worker']:
        raise ValueError('Worker changed')
    for name, digest in d['source_sha256'].items():
        if sha(ROOT / name) != digest or sha(BASE / 'declared_sources' / name) != digest:
            raise ValueError('Frozen SL source changed')
    for split in ['train', 'development']:
        if sha(ROOT / f'results/{region.NAME}_{split}.json') != d['prior_dataset_sha256'][split] or d['manifests'][split] != prior(split):
            raise ValueError('Verified static feature/artifact provenance changed')
    return d


def base_schedule(d, split):
    rng = np.random.default_rng(SEED + int(split == 'development')); cases = list(d['manifests'][split]); result = []
    for block in range(region.PROTOCOL['blocks']):
        for i in rng.permutation(len(cases)):
            result.append({'case': cases[i], 'block': block, 'role': 'qualification', 'left': 'O3', 'right': 'O3', 'choice': 'O3'})
    return result


def candidate_schedule(d, raw):
    result = []; rng = np.random.default_rng(SEED + 2 + int(raw['split'] == 'development'))
    for block in range(region.PROTOCOL['blocks']):
        for i in rng.permutation(len(raw['manifests'])):
            case = list(raw['manifests'])[i]; m = raw['manifests'][case]
            q = [r for r in raw['records'] if r['case'] == case and r['role'] == 'qualification']
            if not clock_effect(q, 'cpu')['control_pass']:
                continue
            choices = list(region.MENU) if raw['split'] == 'train' else ['O3', raw['decisions'][case]['choice']]
            aliases = list(dict.fromkeys(m['aliases'][c] for c in choices))
            for choice in aliases:
                if choice == 'O3':
                    continue
                roles = [('candidate_control', choice, choice), ('effect', 'O3', choice)]
                if block % 2:
                    roles.reverse()
                for role, left, right in roles:
                    result.append({'case': case, 'block': block, 'role': role, 'left': left, 'right': right, 'choice': choice})
    return result


def validate_order(row, m, d, pairs, reps):
    validate(row, m, pairs, reps, row['first'], d['method'])
    if row['method'] != d['method']:
        raise ValueError('Measurement method changed')
    if d['method'] == 'fresh':
        seed = region.PROTOCOL['seed'] + int(hashlib.sha256(f'{m["id"]}:{row["left"]}:{row["right"]}:qualification:{row["block"]}'.encode()).hexdigest()[:8], 16)
    else:
        seed = SEED + int(hashlib.sha256(f'{m["id"]}:{d["method"]}:{row["block"]}:{row["left"]}:{row["right"]}'.encode()).hexdigest()[:8], 16)
    if row['first'] != bool(np.random.default_rng(seed).integers(2)):
        raise ValueError('Starting order changed')


def decisions(raw):
    selected = json.loads(path('selection').read_text()); model = ROOT / f'models/sl_{NAME}_bundle.joblib'
    if sha(path('selection')) != raw['selection_sha256'] or sha(model) != selected['model_sha256']:
        raise ValueError('Frozen selection/model changed')
    bundle = joblib.load(model)
    if sha(path('train')) != bundle['training_sha256']:
        raise ValueError('Training changed after model freeze')
    predicted = {case: bundle['experimental'].choose(m) if bundle['experimental'] else {'choice': 'O3', 'scores': {}}
                 for case, m in raw['manifests'].items()}
    if 'decisions' in raw and any(not predictions_equal(raw['decisions'][case], decision) for case, decision in predicted.items()):
        raise ValueError('Frozen predictions changed')
    return predicted


def verify(raw):
    d = check(); split = raw['split']
    if split not in ['train', 'development'] or raw['declaration_sha256'] != sha(DECLARATION) or raw['manifests'] != d['manifests'][split]:
        raise ValueError('SL data binding changed')
    correct_plan = [(case, c) for case in raw['manifests'] for c in region.MENU]
    if len(raw['correctness']) > len(correct_plan):
        raise ValueError('Extra correctness cells')
    for row, (case, c) in zip(raw['correctness'], correct_plan):
        if (row['case'] != case or row['left'] != 'reference_O0' or row['right'] != c
            or row['role'] != 'correctness' or row['block'] != 0 or row['choice'] != c):
            raise ValueError('Correctness order changed')
        validate_order(row, raw['manifests'][case], d, 2, 1)
    if raw['records'] and len(raw['correctness']) != len(correct_plan):
        raise ValueError('Formal timings before correctness')
    if split == 'development':
        predicted = decisions(raw)
        if raw.get('decisions') != predicted:
            raise ValueError('Missing frozen development decisions')
    schedule = base_schedule(d, split)
    if len(raw['records']) >= len(schedule):
        schedule += candidate_schedule(d, raw)
    if len(raw['records']) > len(schedule) or (raw['complete'] and len(raw['records']) != len(schedule)):
        raise ValueError('Formal schedule coverage changed')
    for row, item in zip(raw['records'], schedule):
        if any(row[k] != v for k, v in item.items()):
            raise ValueError('SL schedule changed')
        validate_order(row, raw['manifests'][row['case']], d, region.PROTOCOL['pairs'], raw['manifests'][row['case']]['repetitions'])
    labels, diagnostics = region.summarize(raw)
    if raw['complete'] and (raw.get('labels') != labels or raw.get('diagnostics') != diagnostics):
        raise ValueError('SL outcomes changed')
    return labels, diagnostics


def collect(split, resume):
    d = check(); output = path(split)
    if output.exists():
        if not resume:
            raise ValueError('Existing data; use --resume')
        raw = json.loads(output.read_text()); verify(raw)
        if raw['complete']:
            print('Verified complete', split, '; no new timings'); return
    else:
        raw = {'split': split, 'declaration_sha256': sha(DECLARATION), 'manifests': d['manifests'][split],
               'correctness': [], 'records': [], 'complete': False}
        if split == 'development':
            raw['selection_sha256'] = sha(path('selection')); raw['decisions'] = decisions(raw)
        save(output, raw)
    correctness = [(case, c) for case in raw['manifests'] for c in region.MENU]
    for case, c in correctness[len(raw['correctness']):]:
        row = run(raw['manifests'][case], d['method'], d['worker'], 0, SEED, 'reference_O0', c, pairs=2, repetitions=1)
        row.update(role='correctness', choice=c); raw['correctness'].append(row); save(output, raw)
        print('Correct', split, case, c, flush=True)
    def cell(item):
        m = raw['manifests'][item['case']]
        row = run(m, d['method'], d['worker'], item['block'], SEED, item['left'], item['right'], repetitions=m['repetitions'])
        row.update(role=item['role'], choice=item['choice']); raw['records'].append(row); save(output, raw)
        print(split, item['block'] + 1, item['case'], item['role'], item['choice'], flush=True)
    baseline = base_schedule(d, split)
    for item in baseline[len(raw['records']):]:
        cell(item)
    schedule = baseline + candidate_schedule(d, raw)
    for item in schedule[len(raw['records']):]:
        cell(item)
    raw['labels'], raw['diagnostics'] = region.summarize(raw); raw['complete'] = True; verify(raw); save(output, raw)
    print('Complete', split, len(raw['labels']), 'baseline-qualified inputs', len(training_rows(raw['labels'], False)), 'candidate targets')


def fit():
    d = check(); output = path('selection'); model = ROOT / f'models/sl_{NAME}_bundle.joblib'
    if output.exists() or model.exists():
        raise ValueError('Frozen model already exists')
    raw = json.loads(path('train').read_text()); labels, _ = verify(raw)
    if not raw['complete']:
        raise ValueError('Incomplete training')
    experiments = {}
    for alpha, lower, floor, kind, depth in PARAMETERS:
        key = f'{kind}_{alpha}_{lower}_{floor}_{depth}'
        experiments[key] = {'parameters': [alpha, lower, floor, kind, depth],
                            **program_cv(labels, raw['manifests'], alpha, lower, floor, kind, depth)}
    eligible = [k for k, v in experiments.items() if v['eligible'] and v['score']['utility'] > 0
                and v['score']['worst_original_program'] >= .97 and v['score']['confirmed_workloads'] >= 1]
    best = max(eligible, key=lambda k: experiments[k]['score']['utility']) if eligible else None
    selector = NativeSelector(*experiments[best]['parameters']).fit(labels) if best else None
    joblib.dump({'default': 'O3', 'experimental': selector, 'training_sha256': sha(path('train')),
                 'declaration_sha256': sha(DECLARATION), 'cv_certified': bool(best), 'protocol': d['protocol']}, model)
    report = {'training_sha256': sha(path('train')), 'model_sha256': sha(model), 'default': 'O3',
              'experimental': best, 'cv_certified': bool(best), 'experiments': experiments,
              'baseline_qualified_inputs': len(labels), 'distinct_candidate_targets': len(training_rows(labels, False)),
              'effective_original_programs': len({r['program'] for r in training_rows(labels, False)}),
              'scope': 'new timing labels; grouped original-program CV; pilot/probe/earlier clocks excluded'}
    save(output, report); print(json.dumps({k: v for k, v in report.items() if k != 'experiments'}, indent=2))


def evaluate():
    raw = json.loads(path('development').read_text()); verify(raw)
    if not raw['complete']:
        raise ValueError('Incomplete repeated development')
    records = {'cpu': [], 'wall': []}; details = {}
    for case, m in raw['manifests'].items():
        choice = raw['decisions'][case]['choice']; alias = m['aliases'][choice]; rows = [r for r in raw['records'] if r['case'] == case]
        details[case] = {'choice': choice, 'clocks': {}}
        for clock in ['cpu', 'wall']:
            q = clock_effect([r for r in rows if r['role'] == 'qualification'], clock)
            cc = [r for r in rows if r['role'] == 'candidate_control']; ec = [r for r in rows if r['role'] == 'effect']
            control = q if alias == 'O3' else clock_effect(cc, clock) if cc else None
            effect = {'speedup': 1., 'log_speedup': 0., 'interval': [1., 1.], 'blocks': [1.] * 3, 'order_pass': True} if alias == 'O3' else clock_effect(ec, clock) if ec else None
            valid = bool(q['control_pass'] and control and control['control_pass'] and effect and effect['order_pass'])
            gain = bool(valid and effect['interval'][0] > 1.03 and all(v > 1.03 for v in effect['blocks']))
            details[case]['clocks'][clock] = {'qualification': q, 'candidate_control': control, 'effect': effect, 'qualified': valid, 'confirmed_gain': gain}
            if valid:
                records[clock].append({'case': case, 'program': m['program'], 'choice': choice, 'log_speedup': effect['log_speedup'], 'confirmed_gain': gain})
    report = {'source_sha256': sha(path('development')), 'selection_sha256': sha(path('selection')),
              'default': 'O3', 'details': details, 'cpu_score': program_score(records['cpu']), 'wall_score': program_score(records['wall']),
              'cpu_qualified_inputs': len(records['cpu']), 'wall_qualified_inputs': len(records['wall']),
              'scope': 'repeated development on two previously executed implementations; no fresh final-test or broad learned-gain claim',
              'reserved_test_executions': 0}
    output = path('evaluation')
    if output.exists() and json.loads(output.read_text()) != report:
        raise ValueError('Evaluation changed')
    if not output.exists():
        save(output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'details'}, indent=2))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['declare', 'train', 'fit', 'development', 'evaluate'])
    parser.add_argument('--resume', action='store_true'); args = parser.parse_args()
    if args.action == 'declare': declare()
    elif args.action in ['train', 'development']: collect(args.action, args.resume)
    elif args.action == 'fit': fit()
    else: evaluate()


if __name__ == '__main__': main()
