"""Train pooled candidate predictors from controlled real and synthetic menus."""
import json
import argparse
from pathlib import Path

import joblib

from scripts.collect_kernels import verify as verify_kernels
from src.benchmarks.compact import save,sha,verify_report
from src.features.transform import FEATURE_NAMES
from src.supervised.transform import TransformSelector,cross_validate,join_labels,select_policies


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",choices=["transform","transform_policy"],default="transform")
    args=parser.parse_args()
    output=Path(f"results/{args.prefix}_selection.json");model_path=Path(f"models/sl_{args.prefix}_bundle.joblib")
    if output.exists() or model_path.exists():raise ValueError("Frozen artifacts already exist")
    raw=json.loads(Path("results/compact_train.json").read_text());verify_report(raw)
    static=json.loads(Path("data/processed/transform_train.json").read_text())
    if static["source_sha256"]!=sha("results/compact_train.json") or static["feature_names"]!=FEATURE_NAMES:
        raise ValueError("Static training provenance changed")
    kernels=json.loads(Path("results/kernel_train.json").read_text());verify_kernels(kernels)
    if kernels["feature_names"]!=FEATURE_NAMES:raise ValueError("Kernel feature contract changed")
    rows=join_labels(raw,static["cases"])+join_labels(kernels,kernels["static_cases"])
    floors=(0.,.01,.03) if args.prefix=="transform_policy" else (.03,)
    cv=cross_validate(rows,floors);selected,experimental=select_policies(cv)
    models={}
    for name in dict.fromkeys([selected,experimental]):
        spec=cv[name] if name!="O3" else {"mode":"O3","guarded":False,"floor":.03}
        models[name]=TransformSelector(spec["mode"],spec["guarded"],spec["floor"]).fit(rows)
    provenance={str(p):sha(p) for p in map(Path,["results/compact_train.json","data/processed/transform_train.json","results/kernel_train.json"])}
    bundle={"models":models,"selected":selected,"experimental":experimental,"provenance":provenance,
            "feature_names":FEATURE_NAMES,"menu":raw["protocol"]["menu"]}
    joblib.dump(bundle,model_path)
    result={"model_sha256":sha(model_path),"provenance":provenance,"selected":selected,"experimental":experimental,
        "rows":len(rows),"real_programs":len({r['program'] for r in rows if r['program'].startswith('benchmark:')}),
        "synthetic_programs":len({r['program'] for r in rows if r['program'].startswith('kernel:')}),
        "cross_validation":cv,"decision_floors":floors,"selection_rule":"mean>1.01, program-bootstrap lower>1, worst>=1/1.03, >=2 confirmed held-program gains; else O3",
        "limitations":"CV conditional on prior training-wide menu selection and development-informed feature design; synthetic kernels are not additional real-world coverage. Experimental policy is frozen using CV rank even when deployment gates fail."}
    save(output,result)
    print(json.dumps({k:result[k] for k in ['selected','experimental','rows','real_programs','synthetic_programs']},indent=2))
    for k,v in cv.items():print(k,v['score']['geomean'],v['changes'],v['confirmed_programs'],flush=True)


if __name__=="__main__":main()
