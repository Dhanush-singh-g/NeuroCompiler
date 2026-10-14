"""Freeze policies from real-program CV with uncertainty and regression costs."""
import json
import argparse
from pathlib import Path

import joblib

from scripts.collect_kernels import verify as verify_kernels
from scripts.collect_real import verify as verify_real
from src.benchmarks.compact import MENU,save,sha,verify_report
from src.features.transform import FEATURE_NAMES
from src.supervised.robust import RobustSelector,is_real,real_cross_validate,select_robust,uncertainty_rows
from src.supervised.transform import TransformSelector


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--longer',action='store_true');args=p.parse_args()
    prefix='robust_long' if args.longer else 'robust'
    output=Path(f'results/{prefix}_selection.json');model_path=Path(f'models/sl_{prefix}_bundle.joblib')
    if output.exists() or model_path.exists():raise ValueError('Preserve frozen artifacts')
    raw=json.loads(Path('results/compact_train.json').read_text());verify_report(raw)
    features=json.loads(Path('data/processed/transform_train.json').read_text())
    if features['source_sha256']!=sha('results/compact_train.json') or features['feature_names']!=FEATURE_NAMES:raise ValueError('Static provenance changed')
    kernels=json.loads(Path('results/kernel_train.json').read_text());verify_kernels(kernels)
    real=json.loads(Path('results/real_train.json').read_text());verify_real(real)
    rows=uncertainty_rows(raw,features['cases'])+uncertainty_rows(kernels,kernels['static_cases'])+uncertainty_rows(real,real['static_cases'])
    if args.longer:
        from scripts.collect_real_long import verify as verify_long
        longer=json.loads(Path('results/real_train_long.json').read_text());verify_long(longer)
        rows+=uncertainty_rows(longer,longer['static_cases'],case_prefix='long:')
    cv=real_cross_validate(rows);selected,experimental=select_robust(cv);models={}
    risk_eligible=[k for k,v in cv.items() if v['variant']=='lower_risk' and v['utility_log']>0]
    risk_policy=max(risk_eligible,key=lambda k:cv[k]['utility_log']) if risk_eligible else 'O3'
    for name in dict.fromkeys([selected,experimental,risk_policy]):
        if name=='O3':models[name]=TransformSelector().fit([r for r in rows if is_real(r['program'])])
        else:
            spec=cv[name];fit=[r for r in rows if spec['domain']=='with_kernels' or is_real(r['program'])]
            models[name]=RobustSelector(spec['variant'],spec['alpha'],spec['floor']).fit(fit)
    previous=Path('models/sl_transform_policy_bundle.joblib');old=joblib.load(previous)
    # A fixed reference, not a validation-selected contender or refitted model.
    models['previous_frozen']=old['models'][old['experimental']]
    paths=['results/compact_train.json','data/processed/transform_train.json','results/kernel_train.json','results/real_train.json',str(previous)]
    if args.longer:paths.append('results/real_train_long.json')
    provenance={p:sha(p) for p in paths}
    bundle={'models':models,'selected':selected,'experimental':experimental,'reference':'previous_frozen',
        'risk_policy':risk_policy,'provenance':provenance,'feature_names':FEATURE_NAMES,'menu':MENU}
    joblib.dump(bundle,model_path)
    r={'selected':selected,'experimental':experimental,'risk_policy':risk_policy,'reference':'previous_frozen','model_sha256':sha(model_path),
       'provenance':provenance,'candidate_rows':len(rows),'real_programs':len({r['program'] for r in rows if is_real(r['program'])}),
       'synthetic_programs':len({r['program'] for r in rows if not is_real(r['program'])}),'cross_validation':cv,
       'selection_rule':'real-program CV only; mean>1.01, bootstrap lower>1, worst program>=1/1.03, worst input>=1/1.01, >=2 confirmed held-program gains; else O3',
       'experimental_rule':'maximize mean real-program log gain minus twice mean real-program negative log gain; O3 when no positive utility',
       'limitations':'Lower timing bounds and loss weights are predictive heuristics, not runtime guarantees. Model-grid selection is adaptive on training CV. Prior menu and feature design used earlier development observations. Synthetic programs supply optional training data but never statistical support in scores.'}
    save(output,r)
    print(json.dumps({k:r[k] for k in ['selected','experimental','risk_policy','candidate_rows','real_programs','synthetic_programs']},indent=2))
    for k,v in cv.items():print(k,v['score']['geomean'],v['utility_log'],v['changes'],v['worst_input'],v['confirmed_programs'],flush=True)


if __name__=='__main__':main()
