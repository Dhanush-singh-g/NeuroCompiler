"""Export a static library/input decision with an explicit O3 default."""
import argparse
import json
import shutil
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.region import ROOT,NAME,verify


def main():
    p=argparse.ArgumentParser();p.add_argument('--case',required=True)
    p.add_argument('--split',choices=['train','development'],default='development')
    p.add_argument('--output',required=True,type=Path);p.add_argument('--experimental',action='store_true');args=p.parse_args()
    raw=json.loads((ROOT/f'results/{NAME}_{args.split}.json').read_text());verify(raw)
    selection=ROOT/f'results/{NAME}_selection.json';selected=json.loads(selection.read_text())
    model=ROOT/f'models/sl_{NAME}_bundle.joblib'
    if sha(model)!=selected['model_sha256'] or ('selection_sha256' in raw and raw['selection_sha256']!=sha(selection)):
        raise ValueError('Frozen model/selection changed')
    bundle=joblib.load(model)
    if bundle['training_sha256']!=sha(ROOT/f'results/{NAME}_train.json'):raise ValueError('Frozen training changed')
    m=raw['manifests'][args.case];decision={'choice':'O3','scores':{}}
    if args.experimental:
        if bundle['experimental'] is None:raise ValueError('No CV-qualified experimental model')
        decision=bundle['experimental'].choose(m)
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    artifact=m['artifacts'][decision['choice']]
    for source,name in [(artifact['bc'],'program.bc'),(artifact['so'],'candidate.so'),(m['worker'],'isolated_library_worker.out'),(m['input'],'input.dat')]:
        shutil.copy2(source,out/name)
    save(out/'manifest.json',{'case':args.case,'program':m['program'],'decision':decision,'default':'O3',
         'experimental':args.experimental,'static_only':True,'cv_certified':selected['cv_certified'],
         'objective':bundle['objective'],'expected':m['expected'],'model_sha256':sha(model),
         'training_sha256':bundle['training_sha256'],'selection_sha256':sha(selection),
         'files_sha256':{name:sha(out/name) for name in ['program.bc','candidate.so','isolated_library_worker.out','input.dat']},
         'scope':'warm PIC library API and frozen input; excludes process startup and client I/O; CPU prediction alone does not establish wall improvement'})
    print('Exported',args.case,decision['choice'])


if __name__=='__main__':main()
