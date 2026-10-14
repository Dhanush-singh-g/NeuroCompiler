"""Audit the frozen, cross-family development study without retuning."""
import json
import argparse
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save, sha
from src.benchmarks.polybench import ROOT, experiment_name, verify
from src.supervised.frozen import predictions_equal
from src.supervised.polybench import score


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--name',default='polybench',type=experiment_name)
    args=p.parse_args()
    path=ROOT/f'results/{args.name}_development.json'
    raw=json.loads(path.read_text())
    selected=ROOT/f'results/{args.name}_selection.json'
    model=ROOT/f'models/sl_{args.name}19_bundle.joblib'
    selection=json.loads(selected.read_text())
    if not raw['complete'] or raw['split']!='development':
        raise ValueError('Incomplete development study')
    if sha(selected)!=raw['frozen_selection_sha256'] or sha(model)!=selection['bundle_sha256']:
        raise ValueError('Frozen learner changed')
    bundle=joblib.load(model)
    if sha(ROOT/f'results/{args.name}_train.json')!=bundle['training_sha256']:
        raise ValueError('Training data changed after freeze')
    for ident,m in raw['manifests'].items():
        expected={'default':'O3','experimental':bundle['experimental'].choose(m)
                  if bundle['experimental'] else {'choice':'O3','scores':{}}}
        if not predictions_equal(expected,raw['frozen_decisions'][ident]):
            raise ValueError('Frozen development prediction mismatch')
    labels,diagnostics=verify(raw)
    records=[]
    for p in labels:
        choice=raw['frozen_decisions'][p['case']]['experimental']['choice']
        s=p['outcomes'][choice]
        records.append({'program':p['case'],'family':p['family'],'choice':choice,
                        'log_speedup':s['log_speedup'],'confirmed_gain':s['confirmed_gain'],
                        'timing_interval':s['interval']})
    trials=[r for c in raw['records'] for side in ['left','right'] for r in c[side+'_trials']]
    report={'source_sha256':sha(path),'selection_sha256':sha(selected),
            'attempted_programs':6,'correct_programs':len(raw['manifests']),
            'qualified_programs':len(labels),'excluded_from_performance':
                sorted(set(raw['manifests'])-{p['case'] for p in labels}),
            'experimental_choices':raw['frozen_decisions'],
            'qualified_experimental_score':score(records),'records':records,
            'default':'O3','reserved_test_executions':0,
            'scheduler_diagnostics':{'trials':len(trials),
              'zero_observed_steal_trials':sum(r['scheduler_delta']['steal']==0 for r in trials),
              'positive_steal_trials':sum(r['scheduler_delta']['steal']>0 for r in trials)},
            'limitations':['Only timing-qualified kernels contribute to this conditional score.',
              'Program bootstrap omits timing uncertainty; per-program timing intervals retained.',
              'One development family is insufficient for broad application generalization.']}
    output=ROOT/f'results/{args.name}_evaluation.json'
    if output.exists() and json.loads(output.read_text())!=report:
        raise ValueError('Existing evaluation differs; refusing overwrite')
    if not output.exists():save(output,report)
    print(json.dumps({k:report[k] for k in ['correct_programs','qualified_programs','qualified_experimental_score','default']},indent=2))


if __name__=='__main__':main()
