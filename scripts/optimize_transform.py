"""Compile new C/LLVM bitcode and select a pipeline using static SL features.

Never executes the input program. Runtime gains require separate evaluation.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import joblib

from src.benchmarks.compact import CODEGEN,MENU,save,sha
from src.benchmarks.kernels import FRONTEND
from src.features.transform import FEATURE_NAMES,extract_manifest


def main():
    from compiler_gym.third_party import llvm
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--executable",type=Path);p.add_argument("--input-bytes",type=int,default=0)
    p.add_argument("--iterations",type=int,default=0)
    policy_flags=p.add_mutually_exclusive_group()
    policy_flags.add_argument("--experimental",action="store_true")
    policy_flags.add_argument("--risk-aware",action="store_true",help="Use the experimental uncertainty-penalized policy from a compatible bundle")
    p.add_argument("--link",action="append",default=[])
    p.add_argument("--model",type=Path,default=Path("models/sl_transform_bundle.joblib"))
    args=p.parse_args()
    if args.input_bytes<0 or args.iterations<0:p.error("Workload metadata must be nonnegative")
    for path in [args.output,args.output.with_suffix('.json'),args.executable]:
        if path and path.exists():p.error(f"Output exists: {path}")
    model_path=args.model;b=joblib.load(model_path)
    if b['feature_names']!=FEATURE_NAMES or b['menu']!=MENU:raise ValueError("Model feature/menu mismatch")
    if args.risk_aware and 'risk_policy' not in b:p.error('This model bundle has no risk-aware policy')
    policy=b['risk_policy'] if args.risk_aware else b['experimental'] if args.experimental else b['selected'];model=b['models'][policy]
    with tempfile.TemporaryDirectory(prefix="neurocompiler-infer-") as temporary:
        root=Path(temporary);initial=root/'initial.bc'
        if args.input.suffix=='.c':
            subprocess.run([str(llvm.clang_path()),*FRONTEND,'-emit-llvm','-c',str(args.input.resolve()),'-o',str(initial)],check=True)
        else:initial.write_bytes(args.input.read_bytes())
        manifest={'program':'inference://input','features':[args.input_bytes,args.iterations],'artifacts':{},'aliases':{}}
        for choice,stages in MENU.items():
            dest=root/choice;dest.mkdir();current=initial
            for i,flags in enumerate(stages):
                path=dest/f'stage{i}.bc';subprocess.run([str(llvm.opt_path()),*flags,str(current),'-o',str(path)],check=True);current=path
            bc=dest/'program.bc';bc.write_bytes(current.read_bytes())
            subprocess.run([str(llvm.clang_path()),str(bc),*CODEGEN,*args.link,'-o',str(dest/'a.out')],check=True)
            manifest['artifacts'][choice]={'directory':str(dest),'bc_sha256':sha(bc),'elf_sha256':sha(dest/'a.out')}
            manifest['aliases'][choice]=next(c for c,a in manifest['artifacts'].items() if a['elf_sha256']==manifest['artifacts'][choice]['elf_sha256'])
        static=extract_manifest(manifest);decision=model.choose(static);choice=decision['configuration']
        args.output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/choice/'program.bc',args.output)
        if args.executable:
            args.executable.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/choice/'a.out',args.executable)
        save(args.output.with_suffix('.json'),{'source_sha256':sha(args.input),'model_sha256':sha(model_path),
            'bitcode_sha256':sha(args.output),'decision':decision,'policy':policy,
            'experimental':args.experimental or args.risk_aware,'risk_aware':args.risk_aware,'native_execution':False,'feature_names':FEATURE_NAMES,
            'static':static['features'],'scope':'LLVM 10 opt O3 comparator, native codegen O3; no runtime claim from prediction'})
        print(json.dumps({'policy':policy,'configuration':choice,'bitcode':str(args.output),'native_execution':False}))


if __name__=="__main__":main()
