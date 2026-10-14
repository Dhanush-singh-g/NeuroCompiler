"""Export a frozen static choice for a built training/development kernel."""
import argparse
import json
import shutil
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.polybench import ROOT,experiment_name,verify


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--split',choices=['train','development'],default='development')
    p.add_argument('--name',default='polybench',type=experiment_name)
    p.add_argument('--case',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--experimental',action='store_true')
    args=p.parse_args()
    raw=json.loads((ROOT/f'results/{args.name}_{args.split}.json').read_text())
    verify(raw)
    manifest=raw['manifests'][args.case]
    selection=json.loads((ROOT/f'results/{args.name}_selection.json').read_text())
    model=ROOT/f'models/sl_{args.name}19_bundle.joblib'
    if sha(model)!=selection['bundle_sha256']:
        raise ValueError('Frozen model changed')
    bundle=joblib.load(model)
    choice='O3'
    if args.experimental:
        if not bundle['experimental']:
            raise ValueError('No qualified experimental learner')
        choice=bundle['experimental'].choose(manifest)['choice']
    output=args.output.resolve()
    paths=[output.with_suffix(s) for s in ['.bc','.out','.json']]
    if any(path.exists() for path in paths):
        raise ValueError('Existing export; refusing overwrite')
    output.parent.mkdir(parents=True,exist_ok=True)
    artifact=manifest['artifacts'][choice]
    shutil.copyfile(artifact['bc'],paths[0]);shutil.copy2(artifact['elf'],paths[1])
    save(paths[2],{'case':args.case,'choice':choice,'default':'O3',
                  'experimental':args.experimental,'static_only':True,
                  'bundle_sha256':sha(model),'bc_sha256':sha(paths[0]),'elf_sha256':sha(paths[1]),
                  'expected':manifest['expected'],'repetitions':manifest['repetitions']})
    print(f"Exported {args.case}: {choice}")


if __name__=='__main__':main()
