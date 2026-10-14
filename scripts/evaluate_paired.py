"""Report frozen development outcomes independently for both native clocks."""
import argparse
import json
import math
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.polybench import ROOT,experiment_name
from src.benchmarks.paired import PROTOCOL,clock_effect,verify
from src.supervised.frozen import predictions_equal
from src.supervised.polybench import score


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='paired_native_20261011',type=experiment_name)
    args=p.parse_args();path=ROOT/f'results/{args.name}_development.json'
    raw=json.loads(path.read_text());policy_name=raw.get('policy_name',args.name)
    selection=ROOT/f'results/{policy_name}_selection.json'
    selected=json.loads(selection.read_text());model=ROOT/f'models/sl_{policy_name}_bundle.joblib'
    if not raw['complete'] or raw['split']!='development':raise ValueError('Incomplete development')
    if sha(selection)!=raw['selection_sha256'] or sha(model)!=selected['model_sha256']:raise ValueError('Learner changed')
    bundle=joblib.load(model)
    if sha(ROOT/f'results/{args.name}_train.json')!=bundle['training_sha256']:raise ValueError('Training changed')
    verify(raw);cpu_records=[];wall_records=[];excluded={};details={}
    for ident,m in raw['manifests'].items():
        expected=bundle['experimental'].choose(m) if bundle['experimental'] else {'choice':'O3','scores':{}}
        if not predictions_equal(expected,raw['frozen_decisions'][ident]):raise ValueError('Frozen prediction changed')
        choice=raw['frozen_decisions'][ident]['choice'];alias=m['aliases'][choice]
        rows=[r for r in raw['records'] if r['case']==ident]
        q=[r for r in rows if r['role']=='qualification']
        if len(q)!=PROTOCOL['blocks']:excluded[ident]='too short/ineligible';continue
        cs={clock:clock_effect(q,clock) for clock in ['cpu','wall']}
        detail={'choice':choice,'baseline_controls':cs,'outcomes':{}}
        if alias!='O3':
            ec=[r for r in rows if r['role']=='effect' and r['choice']==alias]
            cc=[r for r in rows if r['role']=='candidate_control' and r['choice']==alias]
            if len(ec)!=PROTOCOL['blocks']:excluded[ident]='baseline CPU control failed';details[ident]=detail;continue
        for clock,destination in [('cpu',cpu_records),('wall',wall_records)]:
            control=clock_effect(cc,clock) if alias!='O3' else cs[clock]
            s=clock_effect(ec,clock) if alias!='O3' else {'log_speedup':0.,'speedup':1.,'interval':[1.,1.],'blocks':[1.]*PROTOCOL['blocks']}
            valid=cs[clock]['control_pass'] and control['control_pass']
            confirmed=valid and s['interval'][0]>1.03 and all(v>1.03 for v in s['blocks'])
            detail['outcomes'][clock]={'effect':s,'candidate_control':control,'qualified':bool(valid),'confirmed_gain':bool(confirmed)}
            if valid:destination.append({'program':ident,'choice':choice,'log_speedup':s['log_speedup'],'confirmed_gain':bool(confirmed)})
        details[ident]=detail
    trials=[s for r in raw['records'] for s in r['samples']]
    report={'source_sha256':sha(path),'selection_sha256':sha(selection),'default':'O3',
        'policy_name':policy_name,'cv_certified':selected['cv_certified'],
        'correct_programs':len(raw['manifests']),'cpu_qualified_programs':len(cpu_records),
        'wall_qualified_programs':len(wall_records),'cpu_service_score':score(cpu_records),
        'wall_latency_score':score(wall_records),'details':details,'excluded':excluded,
        'pairs_retained':len(trials),'reserved_test_executions':0,
        'limitations':['Wall and CPU scores have separately qualified conditional coverage.',
                       'Do not compare aggregate scores with different contributing programs.',
                       'Aggregate bootstrap omits timing uncertainty; retain per-program intervals.',
                       'A single development family does not establish application generalization.']}
    out=ROOT/f'results/{args.name}_evaluation.json'
    if out.exists() and json.loads(out.read_text())!=report:raise ValueError('Existing differing evaluation')
    if not out.exists():save(out,report)
    print(json.dumps({k:report[k] for k in ['correct_programs','cpu_qualified_programs','wall_qualified_programs','cpu_service_score','wall_latency_score','default']},indent=2))


if __name__=='__main__':main()
