"""Freeze an experimental policy only when complete original-program CV passes."""
import json
import sys
from pathlib import Path

import joblib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.invocation import ROOT,NAME,PROTOCOL,verify
from src.supervised.invocation import NativeSelector,program_cv,training_rows


def main():
    source=ROOT/f'results/{NAME}_train.json';output=ROOT/f'results/{NAME}_selection.json'
    model=ROOT/f'models/sl_{NAME}_bundle.joblib'
    if output.exists() or model.exists():raise ValueError('Existing frozen model; refusing overwrite')
    raw=json.loads(source.read_text())
    if not raw['complete']:raise ValueError('Incomplete training')
    labels,diagnostics=verify(raw);experiments={}
    for alpha in [1.,10.]:
        for lower in [False,True]:
            for floor in [.01,.03]:
                name=f'ridge{alpha:g}_{"lower" if lower else "point"}_{floor}'
                experiments[name]={'parameters':[alpha,lower,floor],**program_cv(labels,raw['manifests'],alpha,lower,floor)}
    eligible=[k for k,v in experiments.items() if v['eligible'] and v['score']['utility']>0 and
              v['score']['worst_original_program']>=.97 and v['score']['confirmed_workloads']>=1]
    best=max(eligible,key=lambda k:experiments[k]['score']['utility']) if eligible else None
    selector=NativeSelector(*experiments[best]['parameters']).fit(labels) if best else None
    bundle={'default':'O3','experimental':selector,'training_sha256':sha(source),'protocol':PROTOCOL,
            'cv_certified':bool(best),'objective':PROTOCOL['objective']}
    joblib.dump(bundle,model)
    oracle=[]
    for p in labels:
        c=max(p['outcomes'],key=lambda c:p['outcomes'][c]['speedup']);s=p['outcomes'][c]
        oracle.append({'case':p['case'],'program':p['program'],'choice':c,'speedup':s['speedup'],'confirmed_gain':s['confirmed_gain']})
    report={'training_sha256':sha(source),'model_sha256':sha(model),'protocol':PROTOCOL,
            'correct_workloads':len(raw['manifests']),'baseline_qualified_workloads':len(labels),
            'distinct_candidate_targets':len(training_rows(labels,False)),
            'effective_original_programs':len({r['program'] for r in training_rows(labels,False)}),
            'default':'O3','experimental':best,'cv_certified':bool(best),'experiments':experiments,'training_oracle':oracle,
            'scope':'native library API CPU time; training oracle is not unseen improvement; real and scientific targets remain separate'}
    save(output,report)
    print(json.dumps({k:report[k] for k in ['correct_workloads','baseline_qualified_workloads','distinct_candidate_targets','effective_original_programs','experimental','default']},indent=2))


if __name__=='__main__':main()
