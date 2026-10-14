"""Export a static kernel choice with explicit O3 default and CPU-model opt-in."""
import argparse
import json
import shutil
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.polybench import ROOT,experiment_name
from src.benchmarks.paired import verify


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='paired_native_20261011',type=experiment_name)
    p.add_argument('--split',choices=['train','development'],default='development')
    p.add_argument('--case',required=True);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--experimental',action='store_true');args=p.parse_args()
    raw=json.loads((ROOT/f'results/{args.name}_{args.split}.json').read_text());verify(raw)
    m=raw['manifests'][args.case];policy_name=raw.get('policy_name',args.name)
    selection_path=ROOT/f'results/{policy_name}_selection.json'
    selection=json.loads(selection_path.read_text())
    if 'selection_sha256' in raw and sha(selection_path)!=raw['selection_sha256']:
        raise ValueError('Frozen selection changed')
    model=ROOT/f'models/sl_{policy_name}_bundle.joblib'
    if sha(model)!=selection['model_sha256']:raise ValueError('Frozen learner changed')
    bundle=joblib.load(model);decision={'choice':'O3','scores':{}}
    if sha(ROOT/f'results/{args.name}_train.json')!=bundle['training_sha256']:raise ValueError('Training changed')
    if args.experimental:
        if bundle['experimental'] is None:raise ValueError('No qualified CPU learner')
        decision=bundle['experimental'].choose(m)
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    a=m['artifacts'][decision['choice']]
    for src,name in [(a['bc'],'program.bc'),(a['so'],'candidate.so'),(m['worker'],'paired_worker.out')]:
        shutil.copy2(src,out/name)
    save(out/'manifest.json',{'case':args.case,'decision':decision,'experimental':args.experimental,
        'default':'O3','static_only':True,'objective':bundle['objective'],'expected':m['expected'],
        'policy_name':policy_name,'cv_certified':bundle['cv_certified'],
        'cpu_performance_qualified':raw.get('diagnostics',{}).get(args.case,{}).get('cpu_menu_qualified',False),
        'selection_sha256':sha(selection_path),'training_sha256':bundle['training_sha256'],
        'model_sha256':sha(model),'bc_sha256':sha(out/'program.bc'),'so_sha256':sha(out/'candidate.so'),
        'worker_sha256':sha(out/'paired_worker.out'),
        'scope':'PIC scientific kernel; CPU prediction alone does not establish wall latency improvement'})
    print('Exported',args.case,decision['choice'])


if __name__=='__main__':main()
