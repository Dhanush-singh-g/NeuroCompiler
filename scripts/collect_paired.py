"""Fixed-budget native training or frozen policy-only development study."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.polybench import ROOT,experiment_name,inventory
from src.benchmarks.paired import PROTOCOL,MENU,build,worker,run_cell,clock_effect,verify


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--name',default='paired_native_20261011',type=experiment_name)
    p.add_argument('--split',choices=['train','development'],default='train')
    p.add_argument('--policy-name',type=experiment_name)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--build-only',action='store_true')
    args=p.parse_args()
    path=ROOT/f'results/{args.name}_{args.split}.json'
    base=ROOT/f'data/processed/paired19/{args.name}'
    if path.exists():
        if not args.resume:raise ValueError('Existing experiment; use --resume')
        report=json.loads(path.read_text());verify(report)
        if report['complete']:print('Verified completed paired study; no new trials.');return
    else:
        report={'protocol':PROTOCOL,'inventory':inventory(),'split':args.split,'name':args.name,
            'manifests':{},'failures':{},'records':[],'complete':False}
        if args.split=='development':
            report['policy_name']=args.policy_name or args.name
            report['selection_sha256']=sha(ROOT/f"results/{report['policy_name']}_selection.json")
        save(path,report)
    worker_path=base/'paired_worker.out'
    if not worker_path.exists():worker(base)
    for item in report['inventory']:
        ident=item['id']
        if item['split']!=args.split or ident in report['manifests'] or ident in report['failures']:continue
        try:
            report['manifests'][ident]=build(item,base/args.split/ident,worker_path)
            m=report['manifests'][ident]
            print(f"Built {ident}: 8 pipelines correct; eligible={m['eligible']}; distinct={len(set(m['aliases'].values()))}",flush=True)
        except Exception as e:
            report['failures'][ident]={'type':type(e).__name__,'message':str(e),
                'stderr':getattr(e,'stderr',b'').decode(errors='replace')}
            print('Excluded build',ident,str(e),flush=True)
        save(path,report)
    if args.build_only:return
    if args.split=='development':
        import joblib
        policy_name=report.get('policy_name',args.name)
        selection_path=ROOT/f'results/{policy_name}_selection.json'
        selected=json.loads(selection_path.read_text());model=ROOT/f'models/sl_{policy_name}_bundle.joblib'
        if sha(model)!=selected['model_sha256'] or sha(selection_path)!=report['selection_sha256']:
            raise ValueError('Frozen learner changed')
        bundle=joblib.load(model)
        if sha(ROOT/f'results/{args.name}_train.json')!=bundle['training_sha256']:
            raise ValueError('Training changed after model freeze')
        decisions={ident:bundle['experimental'].choose(m) if bundle['experimental'] else
                   {'choice':'O3','scores':{}} for ident,m in report['manifests'].items()}
        if 'frozen_decisions' in report and decisions!=report['frozen_decisions']:raise ValueError('Predictions changed')
        report['frozen_decisions']=decisions
        report['active_choices']={ident:['O3',d['choice']] if d['choice']!='O3' else ['O3'] for ident,d in decisions.items()}
        save(path,report)
    completed={(r['case'],r['choice'],r['block'],r['role']) for r in report['records']}
    for block in range(PROTOCOL['blocks']):
        for ident,m in sorted(report['manifests'].items()):
            if not m['eligible']:continue
            key=(ident,'O3',block,'qualification')
            if key not in completed:
                report['records'].append(run_cell(m,'O3','O3_copy',block,'qualification'))
                completed.add(key);save(path,report)
            print('Qualification',block+1,ident,flush=True)
    qualified={ident for ident,m in report['manifests'].items() if m['eligible'] and
        clock_effect([r for r in report['records'] if r['case']==ident and r['role']=='qualification'],'cpu')['control_pass']}
    report['o3_cpu_qualified_programs']=sorted(qualified);save(path,report)
    print('CPU baseline controls passed',len(qualified),'programs',flush=True)
    for block in range(PROTOCOL['blocks']):
        for ident in sorted(qualified):
            m=report['manifests'][ident]
            choices=report.get('active_choices',{}).get(ident,list(MENU))
            measured=set()
            for c in choices:
                alias=m['aliases'][c]
                if alias=='O3' or alias in measured:continue
                measured.add(alias)
                for role in ['candidate_control','effect']:
                    key=(ident,alias,block,role)
                    if key in completed:continue
                    left=alias if role=='candidate_control' else 'O3'
                    report['records'].append(run_cell(m,left,alias,block,role))
                    completed.add(key);save(path,report)
            print('Candidate block',block+1,ident,flush=True)
    report['complete']=True
    labels,diagnostics=verify(report)
    report['labels']=labels;report['diagnostics']=diagnostics;save(path,report)
    print('Complete:',len(report['manifests']),'correct;',len(labels),'CPU-qualified;',
          sum(d['wall_menu_qualified'] for d in diagnostics.values()),'wall-qualified',flush=True)


if __name__=='__main__':main()
