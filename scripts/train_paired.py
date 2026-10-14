"""Freeze CPU-service-time SL; never promote CPU gains as wall gains."""
import argparse
import json
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.polybench import ROOT,experiment_name
from src.benchmarks.paired import MENU,PROTOCOL,verify
from src.supervised.polybench import Selector,family_cv
from src.supervised.partial import POLICY,partial_labels


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='paired_native_20261011',type=experiment_name)
    p.add_argument('--policy-name',type=experiment_name)
    p.add_argument('--fixed-preset',action='store_true')
    p.add_argument('--partial-declaration',type=Path,default=ROOT/'results/paired_partial_declaration.json')
    p.add_argument('--preset-declaration',type=Path,default=ROOT/'results/paired_preset_declaration.json')
    args=p.parse_args();source=ROOT/f'results/{args.name}_train.json'
    policy_name=args.policy_name or args.name
    output=ROOT/f'results/{policy_name}_selection.json';model=ROOT/f'models/sl_{policy_name}_bundle.joblib'
    if output.exists() or model.exists():raise ValueError('Existing frozen model; refusing overwrite')
    raw=json.loads(source.read_text())
    if not raw['complete'] or raw['split']!='train':raise ValueError('Incomplete training experiment')
    full_labels,_=verify(raw)
    policy_path=args.partial_declaration.resolve()
    if not policy_path.exists():raise ValueError('Declare partial-label policy before fitting')
    declaration=json.loads(policy_path.read_text())
    if declaration['policy']!=POLICY or declaration['raw_sha256']!=sha(source):raise ValueError('Partial policy changed')
    labels=partial_labels(raw);choices=list(MENU)[1:];experiments={}
    oracle=[]
    for label in labels:
        best=max(label['outcomes'],key=lambda c:label['outcomes'][c]['speedup'])
        oracle.append({'program':label['case'],'choice':best,
            'speedup':label['outcomes'][best]['speedup'],
            'confirmed_cpu_gain':label['outcomes'][best]['confirmed_gain'],
            'scope':'measured training oracle, not a learned or held-out result'})
    for alpha in [1.,10.]:
        for lower in [False,True]:
            for floor in [.01,.03]:
                key=f"ridge{alpha:g}_{'lower' if lower else 'point'}_{floor}"
                experiments[key]={'parameters':[alpha,lower,floor],**family_cv(labels,raw['manifests'],alpha,lower,floor,choices)}
    eligible=[k for k,v in experiments.items() if v['eligible']]
    selected=max(eligible,key=lambda k:experiments[k]['score']['utility']) if eligible else None
    selector=Selector(*experiments[selected]['parameters'],choices=choices).fit(labels) if selected else None
    if args.fixed_preset:
        preset=args.preset_declaration.resolve()
        d=json.loads(preset.read_text())
        if d['training_sha256']!=sha(source) or d['parameters']!=[10.,True,.03] or d['policy_name']!=policy_name:
            raise ValueError('Fixed hypothesis declaration mismatch')
        selected='fixed_lower_ridge10_floor003'
        selector=Selector(10.,True,.03,choices=choices).fit(labels)
    bundle={'default':'O3','experimental':selector,'training_sha256':sha(source),
        'objective':PROTOCOL['objective'],'protocol':PROTOCOL,'training_programs':[p['case'] for p in labels],
        'partial_policy_sha256':sha(policy_path),'training_path':str(source),
        'cv_certified':not args.fixed_preset and bool(eligible)}
    joblib.dump(bundle,model)
    report={'protocol':PROTOCOL,'training_sha256':sha(source),'model_sha256':sha(model),
        'correct_programs':len(raw['manifests']),'qualified_training_programs':len(labels),
        'complete_menu_programs':len(full_labels),
        'qualified_candidate_labels':sum(len(p['outcomes'])-1 for p in labels),
        'qualified_measured_nonbaseline_labels':sum(raw['manifests'][p['case']]['aliases'][c]!='O3'
            for p in labels for c in p['outcomes'] if c!='O3'),
        'partial_policy':POLICY,'partial_policy_sha256':sha(policy_path),
        'training_programs':[p['case'] for p in labels],
        'experimental':selected,'experiments':experiments,'default':'O3',
        'cv_certified':not args.fixed_preset and bool(eligible),
        'selection_method':'fixed diagnostic hypothesis, not CV selection' if args.fixed_preset else 'fully scorable CV only',
        'training_oracle':oracle,
        'promotion':'requires independently qualified frozen wall-latency improvement on unseen programs',
        'limitations':['CPU service time differs from wall latency','hyperparameter-selected CV is conditional',
                       'program bootstrap omits timing uncertainty','scientific kernels differ from applications']}
    save(output,report)
    print(json.dumps({k:report[k] for k in ['correct_programs','qualified_training_programs','qualified_candidate_labels','experimental','default']},indent=2))


if __name__=='__main__':main()
