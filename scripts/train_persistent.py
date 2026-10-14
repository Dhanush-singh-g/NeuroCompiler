"""Fit the unchanged SL menu with an explicit full-study protocol description.

The collector declaration inherited the pilot's descriptive scope string.
Its numeric gates, full split manifests and model menu remain authoritative.
This pre-fit clarification changes descriptions only, never data or decisions.
"""
import json
import shutil
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import study_persistent as study
from src.benchmarks.compact import save, sha
from src.supervised.region import NativeSelector, program_cv, training_rows

CLARIFICATION = study.ROOT / 'results/persistent_sl_protocol_clarification.json'


def main():
    d = study.check(); output = study.path('selection'); model = study.ROOT / f'models/sl_{study.NAME}_bundle.joblib'
    if output.exists() or model.exists() or CLARIFICATION.exists():
        raise ValueError('Existing fit/clarification; refusing overwrite')
    raw = json.loads(study.path('train').read_text()); labels, _ = study.verify(raw)
    if not raw['complete']:
        raise ValueError('Incomplete training')
    protocol = {key: d['protocol'][key] for key in ['blocks', 'pairs', 'cpu', 'control_tolerance', 'gain_floor', 'bootstrap_replicates', 'seed']}
    protocol.update(method=d['method'], scope='13-program supervised training; four repeated-development inputs; no fresh final test',
        objective='warm native PIC library API CPU service time, with independent wall qualification',
        ordering='frozen shuffled case order; micro alternation after each API invocation; equal even repetitions',
        controls='same exact implementation file in separate children; actual pooled and every-block order bounds',
        label_policy=d['label_policy'])
    source_copy = study.BASE / 'prefit/declared_sources/scripts/train_persistent.py'
    source_copy.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(Path(__file__), source_copy)
    save(CLARIFICATION, {'declaration_sha256': sha(study.DECLARATION), 'training_sha256': sha(study.path('train')),
        'source_sha256': sha(Path(__file__)), 'protocol': protocol,
        'change': 'correct inherited pilot description; numeric gates, splits, menu, parameters, labels, folds and selection unchanged'})
    experiments = {}
    for alpha, lower, floor, kind, depth in study.PARAMETERS:
        key = f'{kind}_{alpha}_{lower}_{floor}_{depth}'
        experiments[key] = {'parameters': [alpha, lower, floor, kind, depth],
                            **program_cv(labels, raw['manifests'], alpha, lower, floor, kind, depth)}
    eligible = [k for k, v in experiments.items() if v['eligible'] and v['score']['utility'] > 0
                and v['score']['worst_original_program'] >= .97 and v['score']['confirmed_workloads'] >= 1]
    best = max(eligible, key=lambda k: experiments[k]['score']['utility']) if eligible else None
    selector = NativeSelector(*experiments[best]['parameters']).fit(labels) if best else None
    joblib.dump({'default': 'O3', 'experimental': selector, 'training_sha256': sha(study.path('train')),
                 'declaration_sha256': sha(study.DECLARATION), 'protocol_clarification_sha256': sha(CLARIFICATION),
                 'cv_certified': bool(best), 'protocol': protocol}, model)
    report = {'training_sha256': sha(study.path('train')), 'model_sha256': sha(model), 'default': 'O3',
              'experimental': best, 'cv_certified': bool(best), 'experiments': experiments,
              'baseline_qualified_inputs': len(labels), 'distinct_candidate_targets': len(training_rows(labels, False)),
              'effective_original_programs': len({r['program'] for r in training_rows(labels, False)}),
              'protocol': protocol, 'protocol_clarification_sha256': sha(CLARIFICATION),
              'scope': 'new timing labels; grouped original-program CV; pilot/probe/earlier clocks excluded'}
    save(output, report); print(json.dumps({k: v for k, v in report.items() if k != 'experiments'}, indent=2))


if __name__ == '__main__': main()
