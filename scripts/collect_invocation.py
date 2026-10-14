"""One frozen invocation-paired library study; completed runs never resample."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.invocation import *


def pilot():
    path=ROOT/'results/invocation_pilot.json'
    if path.exists():raise ValueError('Existing pilot; no retries')
    original=json.loads((ROOT/'results/paired_native_20261011_train.json').read_text())
    source=ROOT/'src/benchmarks/invocation_worker.c';worker=compile_worker()
    report={'protocol':PROTOCOL,'cases':['correlation','gemm','durbin'],
            'stage':'unchanged-control diagnostic only; no pilot labels admitted',
            'worker_source_sha256':sha(source),'records':[],'diagnostics':{}}
    save(ROOT/'results/invocation_pilot_declaration.json',{k:v for k,v in report.items() if k not in ['records','diagnostics']})
    cases={}
    for ident in report['cases']:
        m=dict(original['manifests'][ident]);m['worker']=str(worker);m['worker_sha256']=sha(worker)
        cal=run_cell(m,'O3','O3_copy',0,'calibration',pairs=3,repetitions=1)
        duration=float(np.median([s[t]['cpu_seconds'] for s in cal['samples'] for t in ['left','right']]))
        m['repetitions']=min(PROTOCOL['max_repetitions'],max(1,math.ceil(.04/duration)));cases[ident]=m
    for block in range(PROTOCOL['blocks']):
        for ident,m in cases.items():
            report['records'].append(run_cell(m,'O3','O3_copy',block,'qualification'));save(path,report)
            print('Pilot',block+1,ident,flush=True)
    report['diagnostics']={ident:{clock:clock_effect([r for r in report['records'] if r['case']==ident],clock)
                                for clock in ['cpu','wall']} for ident in cases}
    save(path,report)
    print('Pilot qualified',sum(d['cpu']['control_pass'] for d in report['diagnostics'].values()),'of3',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--split',choices=['train','development'],default='train')
    parser.add_argument('--resume',action='store_true');parser.add_argument('--build-only',action='store_true')
    args=parser.parse_args()
    if args.pilot:pilot();return
    declaration=ROOT/'results/invocation_declaration.json'
    if not declaration.exists():raise ValueError('Declare the complete protocol before collection')
    declared=json.loads(declaration.read_text())
    if declared['protocol']!=PROTOCOL or declared['source_pins']!=pins():raise ValueError('Changed declared experiment')
    path=ROOT/f'results/{NAME}_{args.split}.json'
    if path.exists():
        if not args.resume:raise ValueError('Existing study; use --resume')
        raw=json.loads(path.read_text());verify(raw)
        if raw['complete']:print('Verified completed invocation study; no new measurements.');return
    else:
        raw={'protocol':PROTOCOL,'source_pins':pins(),'split':args.split,'manifests':{},'failures':{},'records':[],
             'complete':False,'declaration_sha256':sha(declaration)}
        if args.split=='development':
            raw['selection_sha256']=sha(ROOT/f'results/{NAME}_selection.json')
        save(path,raw)
    worker_path=BASE/'invocation_worker.out'
    if not worker_path.exists():worker_path=compile_worker()
    cases=CASES if args.split=='train' else DEVELOPMENT
    for program in dict.fromkeys(case.split('_')[0] for case in cases):
        manifests=BASE/'programs'/program/'manifest.json'
        prepared=None
        for case in cases:
            if not case.startswith(program+'_') or case in raw['manifests'] or case in raw['failures']:continue
            try:
                if prepared is None:
                    prepared=json.loads(manifests.read_text()) if manifests.exists() else compile_program(program,worker_path)
                raw['manifests'][case]=prepare_case(case,prepared)
                print('Built',case,'five pipelines correct; eligible',raw['manifests'][case]['eligible'],flush=True)
            except Exception as e:
                raw['failures'][case]={'type':type(e).__name__,'message':str(e),'stderr':getattr(e,'stderr',b'').decode(errors='replace')}
                print('Excluded',case,raw['failures'][case],flush=True)
            save(path,raw)
    if args.build_only:return
    if args.split=='development':
        import joblib
        selection=ROOT/f'results/{NAME}_selection.json';selected=json.loads(selection.read_text())
        model=ROOT/f'models/sl_{NAME}_bundle.joblib'
        if sha(selection)!=raw['selection_sha256'] or sha(model)!=selected['model_sha256']:raise ValueError('Frozen policy changed')
        bundle=joblib.load(model)
        if sha(ROOT/f'results/{NAME}_train.json')!=bundle['training_sha256']:raise ValueError('Training changed')
        decisions={case:bundle['experimental'].choose(m) if bundle['experimental'] else {'choice':'O3','scores':{}}
                   for case,m in raw['manifests'].items()}
        if 'frozen_decisions' in raw and raw['frozen_decisions']!=decisions:raise ValueError('Predictions changed')
        raw['frozen_decisions']=decisions
        raw['active_choices']={case:['O3',d['choice']] if d['choice']!='O3' else ['O3'] for case,d in decisions.items()}
        save(path,raw)
    completed={(r['case'],r['choice'],r['role'],r['block']) for r in raw['records']}
    for block in range(PROTOCOL['blocks']):
        for case,m in raw['manifests'].items():
            if not m['eligible'] or (case,'O3','qualification',block) in completed:continue
            raw['records'].append(run_cell(m,'O3','O3_copy',block,'qualification'));save(path,raw)
            print('Qualification',block+1,case,flush=True)
    qualified=[case for case,m in raw['manifests'].items() if m['eligible'] and clock_effect(
        [r for r in raw['records'] if r['case']==case and r['role']=='qualification'],'cpu')['control_pass']]
    print('Baseline CPU controls passed',len(qualified),'of',sum(m['eligible'] for m in raw['manifests'].values()),flush=True)
    for block in range(PROTOCOL['blocks']):
        for case in qualified:
            m=raw['manifests'][case];measured=set()
            for c in raw.get('active_choices',{}).get(case,list(MENU)):
                alias=m['aliases'][c]
                if alias=='O3' or alias in measured:continue
                measured.add(alias)
                for role,left,right in [('candidate_control',alias,alias+'_copy'),('effect','O3',alias)]:
                    if (case,alias,role,block) in completed:continue
                    raw['records'].append(run_cell(m,left,right,block,role));save(path,raw)
            print('Candidate block',block+1,case,flush=True)
    raw['complete']=True;raw['labels'],raw['diagnostics']=verify(raw);save(path,raw)
    print('Completed',len(raw['labels']),'baseline-qualified cases',flush=True)


if __name__=='__main__':main()
