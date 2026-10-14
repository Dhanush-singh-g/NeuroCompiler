"""Freeze pooled predictions, then collect new controlled development timings."""
import argparse
import json
import random
from pathlib import Path

import joblib

from src.benchmarks.compact import PROTOCOL,effect,measure_cell,save,sha,verify_report
from src.features.transform import FEATURE_NAMES
from src.supervised.compact import grouped_score
from src.supervised.frozen import predictions_equal


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--resume",action="store_true")
    p.add_argument("--precision",action="store_true",help="Separate 40-pair study with 1% controls and gain floor")
    p.add_argument("--prefix",choices=["transform","transform_policy"],default="transform");args=p.parse_args()
    model_path=Path(f"models/sl_{args.prefix}_bundle.joblib");static_path=Path("data/processed/transform_validation.json")
    if args.precision and args.prefix!='transform_policy':p.error("Precision confirmation uses the frozen policy experiment")
    source=Path("results/compact_validation.json")
    output=Path(f"results/{args.prefix}_{'confirmation' if args.precision else 'development'}.json")
    runtime={**PROTOCOL,**({'pairs':40,'control_tolerance':.01,'gain_floor':.01,'seed':20261013} if args.precision else {})}
    statistic=lambda cells:effect(cells,runtime)
    bundle=joblib.load(model_path);old=json.loads(source.read_text());verify_report(old)
    features=json.loads(static_path.read_text())
    if features["source_sha256"]!=sha(source) or features["feature_names"]!=FEATURE_NAMES:raise ValueError("Feature provenance")
    for path,h in bundle["provenance"].items():
        if sha(path)!=h:raise ValueError("Training provenance changed")
    programs={m["program"] for m in old["manifests"].values()}
    if any(programs & set(m.programs) for m in bundle["models"].values()):raise ValueError("Fitted development program")
    decisions={case:{name:m.choose(s) for name,m in bundle["models"].items()} for case,s in features["cases"].items()}
    protocol={"runtime":runtime,"seed":20261013 if args.precision else 20261012,"model_sha256":sha(model_path),"static_sha256":sha(static_path),
              "source_sha256":sha(source),"selected":bundle["selected"],"experimental":bundle["experimental"],
              "scope":"Previously observed development; new frozen model decisions and fresh timings. Reserved tests excluded."}
    if output.exists():
        if not args.resume:p.error("Output exists; use --resume")
        r=json.loads(output.read_text())
        if r["protocol"]!=protocol or not predictions_equal(decisions,r["decisions"]):raise ValueError("Frozen model decisions changed")
        if r["complete"]:
            from scripts.verify_transform import verify_study
            verify_study(output)
            print("Completed frozen development verified; no repeat timing");return
    else:
        r={"protocol":protocol,"decisions":decisions,"records":[],"complete":False,"results":{}}
        save(output,r)
    eligible=[k for k,v in old["profiles"].items() if v["eligible"]]
    rng=random.Random(protocol["seed"])
    done={(x["case"],x["choice"],x["role"],x["block"]) for x in r["records"]}
    for phase in ("qualification","predictions"):
        for block in range(runtime["blocks"]):
            jobs=[]
            for case in eligible:
                if phase=="qualification":jobs.append((case,"O3","O3","qualification"))
                else:
                    q=[x for x in r["records"] if x["case"]==case and x["role"]=="qualification"]
                    if not statistic(q)["control_pass"]:continue
                    chosen={d["configuration"] for d in decisions[case].values()}-{"O3"}
                    for c in sorted(chosen):jobs.extend([(case,c,c,"candidate_control"),(case,"O3",c,"effect")])
            rng.shuffle(jobs)
            for case,left,right,role in jobs:
                first=rng.choice([True,False]);choice=right if role=="effect" else left
                key=(case,choice,role,block)
                if key in done:continue
                r["records"].append(measure_cell(old["manifests"][case],left,right,block,role,first,runtime))
                done.add(key);save(output,r);print("CELL",len(done),case,choice,role,flush=True)
    for name in bundle["models"]:
        outcomes=[];excluded=[]
        for case in eligible:
            q=statistic([x for x in r["records"] if x["case"]==case and x["role"]=="qualification"])
            choice=decisions[case][name]["configuration"]
            if not q["control_pass"]:excluded.append(case);continue
            if choice=="O3":s={"log_speedup":0.,"speedup":1.,"confirmed_gain":False}
            else:
                c=statistic([x for x in r["records"] if x["case"]==case and x["choice"]==choice and x["role"]=="candidate_control"])
                if not c["control_pass"]:excluded.append(case);continue
                s=statistic([x for x in r["records"] if x["case"]==case and x["choice"]==choice and x["role"]=="effect"])
                floor=1+runtime['gain_floor']
                s["confirmed_gain"]=s["interval"][0]>floor and all(v>floor for v in s["blocks"])
                s["candidate_control"]=c
            outcomes.append({"case":case,"program":old["manifests"][case]["program"],"choice":choice,**s})
        r["results"][name]={"records":outcomes,"excluded":excluded,"score":grouped_score(outcomes),
            "changes":sum(o["choice"]!="O3" for o in outcomes),"confirmed_gains":sum(o["confirmed_gain"] for o in outcomes)}
    r["complete"]=True;save(output,r)
    from scripts.verify_transform import verify_study
    verify_study(output)
    print(json.dumps(r["results"],indent=2))


if __name__=="__main__":main()
