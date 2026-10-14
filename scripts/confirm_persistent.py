"""One declared confirmation and one conditional training-headroom probe.

The budgets and case were fixed in the pilot declaration. Neither output is
a supervised label source. A complete resume verifies without sampling again.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import measure_persistent as pilot
from src.benchmarks.compact import save, sha
from src.benchmarks.persistent import BASE, run, validate, clock_effect
from src.benchmarks.region import ROOT, PROTOCOL

SEEDS = {'confirmation': 20261105, 'probe': 20261106}
ROLES = [('qualification', 'O3', 'O3'),
         ('candidate_control', 'O3_no_vector', 'O3_no_vector'),
         ('effect', 'O3', 'O3_no_vector')]


def paths(stage):
    return (ROOT / f'results/persistent_{stage}_declaration.json',
            ROOT / f'results/persistent_{stage}.json')


def prior(stage):
    raw = json.loads(pilot.OUTPUT.read_text())
    pilot.verify(raw)
    if not raw['complete']:
        raise ValueError('Pilot must be complete')
    method = raw['summary']['selected_method']
    if stage == 'probe':
        _, output = paths('confirmation')
        confirmation = json.loads(output.read_text())
        verify('confirmation', confirmation)
        if not confirmation['complete']:
            raise ValueError('Confirmation must be complete')
        if not confirmation['summary']['passed']:
            method = None
    return raw, method


def schedule(stage, method):
    if method is None:
        return []
    rng = np.random.default_rng(SEEDS[stage]); result = []
    for block in range(PROTOCOL['blocks']):
        if stage == 'confirmation':
            items = [{'case': pilot.CASES[i], 'role': 'qualification', 'left': 'O3', 'right': 'O3'}
                     for i in rng.permutation(len(pilot.CASES))]
        else:
            items = [{'case': 'blake2_random', 'role': role, 'left': left, 'right': right}
                     for role, left, right in [ROLES[(block + j) % 3] for j in range(3)]]
        for item in items:
            result.append({**item, 'method': method, 'block': block})
    return result


def bindings(stage):
    result = {'pilot_declaration': sha(pilot.DECLARATION), 'pilot_results': sha(pilot.OUTPUT)}
    if stage == 'probe':
        declaration, output = paths('confirmation')
        result.update(confirmation_declaration=sha(declaration), confirmation_results=sha(output))
    return result


def declare(stage):
    declaration, output = paths(stage)
    if declaration.exists() or output.exists():
        raise ValueError('Existing declaration/results; no repeated study')
    raw, method = prior(stage)
    cases = pilot.CASES if stage == 'confirmation' else ['blake2_random']
    manifests = {case: raw['manifests'][case] for case in cases}
    artifacts = {}
    for m in manifests.values():
        choices = ['O3'] if stage == 'confirmation' else ['O3', 'O3_no_vector']
        for choice in choices:
            artifact = m['artifacts'][choice]
            if sha(artifact['so']) != artifact['so_sha256']:
                raise ValueError('Pinned implementation changed')
            artifacts[artifact['so']] = artifact['so_sha256']
    name = 'scripts/confirm_persistent.py'; digest = sha(ROOT / name)
    copy = BASE / stage / 'declared_sources' / name
    copy.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / name, copy)
    worker = pilot.check_declaration_local()['worker']
    save(declaration, {'declared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'stage': stage, 'seed': SEEDS[stage], 'method': method, 'schedule': schedule(stage, method),
        'manifests': manifests, 'bindings': bindings(stage), 'artifact_sha256': artifacts,
        'worker': worker, 'worker_sha256': sha(worker), 'source': name, 'source_sha256': digest,
        'protocol': pilot.PILOT_PROTOCOL,
        'scope': 'training-only method confirmation' if stage == 'confirmation' else 'preselected training-only BLAKE2/no-vector headroom; no model fit',
        'gate': 'at least 6/8 CPU and 6/8 wall controls' if stage == 'confirmation' else 'both self-controls and effect order; all blocks and interval lower bound >1.03x',
        'retry_policy': 'one fixed schedule; retain every sample; no replacement or repeated failed controls'})
    print('Declared', stage, method, len(schedule(stage, method)), 'cells')


def check(stage):
    declaration, _ = paths(stage); d = json.loads(declaration.read_text()); raw, method = prior(stage)
    cases = pilot.CASES if stage == 'confirmation' else ['blake2_random']
    if (d['stage'] != stage or d['method'] != method or d['seed'] != SEEDS[stage]
        or d['schedule'] != schedule(stage, method) or d['bindings'] != bindings(stage)
        or d['protocol'] != pilot.PILOT_PROTOCOL
        or d['manifests'] != {case: raw['manifests'][case] for case in cases}):
        raise ValueError('Follow-up declaration/binding changed')
    if sha(ROOT / d['source']) != d['source_sha256'] or sha(BASE / stage / 'declared_sources' / d['source']) != d['source_sha256']:
        raise ValueError('Frozen follow-up source changed')
    if d['worker'] != pilot.check_declaration_local()['worker'] or sha(d['worker']) != d['worker_sha256']:
        raise ValueError('Frozen worker changed')
    expected = {m['artifacts'][c]['so']: m['artifacts'][c]['so_sha256'] for m in d['manifests'].values()
                for c in (['O3'] if stage == 'confirmation' else ['O3', 'O3_no_vector'])}
    if d['artifact_sha256'] != expected or any(sha(p) != h for p, h in expected.items()):
        raise ValueError('Frozen artifact changed')
    return d


def summarize(stage, raw):
    if raw['method'] is None:
        return {'passed': False, 'status': 'not_run', 'fit_targets': 0,
                'reason': 'pilot method gate failed' if stage == 'confirmation' else 'independent confirmation gate failed'}
    if stage == 'confirmation':
        stats = {case: {clock: clock_effect([r for r in raw['records'] if r['case'] == case], clock)
                        for clock in ['cpu', 'wall']} for case in pilot.CASES}
        coverage = {clock: sum(int(s[clock]['control_pass']) for s in stats.values()) for clock in ['cpu', 'wall']}
        return {'statistics': stats, 'coverage': coverage, 'passed': min(coverage.values()) >= 6,
                'status': 'complete', 'fit_targets': 0, 'scope': 'independent null-control confirmation; no gain/model claim'}
    stats = {}
    for clock in ['cpu', 'wall']:
        detail = {role: clock_effect([r for r in raw['records'] if r['role'] == role], clock) for role, _, _ in ROLES}
        valid = detail['qualification']['control_pass'] and detail['candidate_control']['control_pass'] and detail['effect']['order_pass']
        effect = detail['effect']; gain = valid and effect['interval'][0] > 1.03 and all(v > 1.03 for v in effect['blocks'])
        detail.update(qualified=bool(valid), confirmed_gain=bool(gain)); stats[clock] = detail
    return {'statistics': stats, 'passed': all(s['confirmed_gain'] for s in stats.values()), 'status': 'complete',
            'fit_targets': 0, 'scope': 'one preselected training-only headroom comparison; no SL/generalization claim'}


def verify(stage, raw):
    d = check(stage); declaration, _ = paths(stage)
    if raw['declaration_sha256'] != sha(declaration) or raw['method'] != d['method']:
        raise ValueError('Result binding changed')
    if len(raw['records']) > len(d['schedule']) or (raw['complete'] and len(raw['records']) != len(d['schedule'])):
        raise ValueError('Schedule coverage changed')
    for row, item in zip(raw['records'], d['schedule']):
        if any(row[k] != v for k, v in item.items()):
            raise ValueError('Follow-up schedule changed')
        m = d['manifests'][row['case']]
        validate(row, m, PROTOCOL['pairs'], m['repetitions'], row['first'], row['method'])
        if row['method'] == 'fresh':
            seed = PROTOCOL['seed'] + int(hashlib.sha256(f'{m["id"]}:{row["left"]}:{row["right"]}:qualification:{row["block"]}'.encode()).hexdigest()[:8], 16)
        else:
            seed = d['seed'] + int(hashlib.sha256(f'{m["id"]}:{row["method"]}:{row["block"]}:{row["left"]}:{row["right"]}'.encode()).hexdigest()[:8], 16)
        if row['first'] != bool(np.random.default_rng(seed).integers(2)) or row['choice'] != row['right']:
            raise ValueError('Starting order/comparison changed')
    if raw['complete'] and raw.get('summary') != summarize(stage, raw):
        raise ValueError('Follow-up statistics changed')
    return d


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('stage', choices=SEEDS)
    parser.add_argument('--declare', action='store_true'); parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.declare:
        declare(args.stage); return
    d = check(args.stage); declaration, output = paths(args.stage)
    if output.exists():
        if not args.resume:
            raise ValueError('Existing results; use --resume')
        raw = json.loads(output.read_text()); verify(args.stage, raw)
        if raw['complete']:
            print('Verified complete', args.stage, '; no new timings'); return
    else:
        raw = {'declaration_sha256': sha(declaration), 'method': d['method'], 'records': [], 'complete': False}; save(output, raw)
    for item in d['schedule'][len(raw['records']):]:
        m = d['manifests'][item['case']]
        row = run(m, item['method'], d['worker'], item['block'], d['seed'], item['left'], item['right'], repetitions=m['repetitions'])
        row.update(role=item['role'], choice=item['right'])
        raw['records'].append(row); save(output, raw)
        print(args.stage, item['block'] + 1, item['case'], item['role'], flush=True)
    raw['summary'] = summarize(args.stage, raw); raw['complete'] = True; verify(args.stage, raw); save(output, raw)
    print(json.dumps({k: v for k, v in raw['summary'].items() if k != 'statistics'}, indent=2))


if __name__ == '__main__':
    main()
