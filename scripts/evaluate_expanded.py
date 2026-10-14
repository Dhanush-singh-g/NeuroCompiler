"""Frozen fresh-implementation development evaluation; no selection feedback."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import expanded_study as study
from src.benchmarks.compact import save, sha
from src.benchmarks.region import clock_effect
from src.supervised.region import program_score


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); args = p.parse_args()
    base = args.output.resolve(); raw = json.loads((base / 'development.json').read_text()); study.verify_study(base, raw)
    if not raw['complete']: raise ValueError('Incomplete fresh development')
    records = {'cpu': [], 'wall': []}; details = {}
    for case, m in raw['manifests'].items():
        choice = raw['decisions'][case]['choice']; alias = m['aliases'][choice]
        rows = [r for r in raw['records'] if r['case'] == case]
        details[case] = {'choice': choice, 'clocks': {}}
        for clock in ['cpu', 'wall']:
            q = [r for r in rows if r['role'] == 'qualification']
            if len(q) != study.e.PROTOCOL['blocks']:
                details[case]['clocks'][clock] = {'qualified': False, 'reason': 'below minimum duration'}; continue
            baseline = clock_effect(q, clock)
            if alias == 'O3':
                control = baseline; effect = {'speedup': 1., 'log_speedup': 0., 'interval': [1., 1.], 'blocks': [1.] * 3, 'order_pass': True}
            else:
                cc = [r for r in rows if r['role'] == 'candidate_control']; ec = [r for r in rows if r['role'] == 'effect']
                control = clock_effect(cc, clock) if cc else None; effect = clock_effect(ec, clock) if ec else None
            valid = bool(baseline['control_pass'] and control and control['control_pass'] and effect and effect['order_pass'])
            gain = bool(valid and effect['interval'][0] > 1.03 and all(v > 1.03 for v in effect['blocks']))
            details[case]['clocks'][clock] = {'baseline': baseline, 'candidate_control': control, 'effect': effect, 'qualified': valid, 'confirmed_gain': gain}
            if valid: records[clock].append({'case': case, 'program': m['program'], 'choice': choice, 'log_speedup': effect['log_speedup'], 'confirmed_gain': gain})
    report = {'development_sha256': sha(base / 'development.json'), 'selection_sha256': sha(base / 'selection.json'),
        'default': 'O3', 'correct_inputs': len(raw['manifests']), 'cpu_qualified_inputs': len(records['cpu']),
        'wall_qualified_inputs': len(records['wall']), 'cpu_score': program_score(records['cpu']), 'wall_score': program_score(records['wall']),
        'details': details, 'scope': 'two fresh implementations/four inputs; conditional coverage, excludes startup/client I/O; no broad final-test certification',
        'reserved_test_executions': 0}
    path = base / 'evaluation.json'
    if path.exists() and json.loads(path.read_text()) != report: raise ValueError('Frozen evaluation changed')
    if not path.exists(): save(path, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'details'}, indent=2))


if __name__ == '__main__': main()
