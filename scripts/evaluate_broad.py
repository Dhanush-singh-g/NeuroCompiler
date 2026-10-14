"""Frozen entire-program holdout, independently qualified native clocks."""
import json
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.broad import ROOT,NAME,PROTOCOL,verify,clock_effect
from src.supervised.broad import program_score
from src.supervised.frozen import predictions_equal


def main():
    path=ROOT/f'results/{NAME}_development.json';raw=json.loads(path.read_text())
    selection=ROOT/f'results/{NAME}_selection.json';selected=json.loads(selection.read_text())
    model=ROOT/f'models/sl_{NAME}_bundle.joblib'
    if not raw['complete'] or raw['split']!='development':raise ValueError('Incomplete development')
    if sha(selection)!=raw['selection_sha256'] or sha(model)!=selected['model_sha256']:raise ValueError('Frozen model changed')
    bundle=joblib.load(model)
    if sha(ROOT/f'results/{NAME}_train.json')!=bundle['training_sha256']:raise ValueError('Training changed after freeze')
    verify(raw);records={'cpu':[],'wall':[]};details={};excluded={}
    for case,m in raw['manifests'].items():
        decision=bundle['experimental'].choose(m) if bundle['experimental'] else {'choice':'O3','scores':{}}
        if not predictions_equal(decision,raw['frozen_decisions'][case]):raise ValueError('Frozen prediction changed')
        choice=decision['choice'];alias=m['aliases'][choice]
        rows=[r for r in raw['records'] if r['case']==case];q=[r for r in rows if r['role']=='qualification']
        if len(q)!=PROTOCOL['blocks']:excluded[case]='below minimum duration';continue
        controls={clock:clock_effect(q,clock) for clock in ['cpu','wall']}
        detail={'choice':choice,'baseline_controls':controls,'outcomes':{}}
        if alias!='O3':
            cc=[r for r in rows if r['role']=='candidate_control' and r['choice']==alias]
            ec=[r for r in rows if r['role']=='effect' and r['choice']==alias]
            if len(ec)!=PROTOCOL['blocks']:excluded[case]='baseline CPU qualification failed';details[case]=detail;continue
        for clock in ['cpu','wall']:
            control=clock_effect(cc,clock) if alias!='O3' else controls[clock]
            s=clock_effect(ec,clock) if alias!='O3' else {'speedup':1.,'log_speedup':0.,'interval':[1.,1.],'blocks':[1.]*PROTOCOL['blocks']}
            valid=controls[clock]['control_pass'] and control['control_pass']
            confirmed=valid and s['interval'][0]>1.03 and all(v>1.03 for v in s['blocks'])
            detail['outcomes'][clock]={'effect':s,'candidate_control':control,'qualified':bool(valid),'confirmed_gain':bool(confirmed)}
            if valid:records[clock].append({'case':case,'program':m['program'],'choice':choice,'log_speedup':s['log_speedup'],'confirmed_gain':bool(confirmed)})
        details[case]=detail
    report={'source_sha256':sha(path),'selection_sha256':sha(selection),'default':'O3','cv_certified':selected['cv_certified'],
            'correct_workloads':len(raw['manifests']),'cpu_qualified_workloads':len(records['cpu']),
            'wall_qualified_workloads':len(records['wall']),'cpu_score':program_score(records['cpu']),
            'wall_score':program_score(records['wall']),'details':details,'excluded':excluded,
            'reserved_test_executions':0,'limitations':['Two held-out upstream programs cannot establish broad generalization.',
              'Clock-specific scores have conditional coverage; program bootstrap omits timing uncertainty.',
              'Native library API time excludes process startup and client input/output work.']}
    out=ROOT/f'results/{NAME}_evaluation.json'
    if out.exists() and json.loads(out.read_text())!=report:raise ValueError('Existing differing evaluation')
    if not out.exists():save(out,report)
    print(json.dumps({k:report[k] for k in ['correct_workloads','cpu_qualified_workloads','wall_qualified_workloads','cpu_score','wall_score','default']},indent=2))


if __name__=='__main__':main()
