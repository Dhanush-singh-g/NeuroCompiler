"""Freeze an independent learner from qualified LLVM19 training labels."""
import json
import argparse
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save, sha
from src.benchmarks.polybench import ROOT, PROTOCOL, experiment_name, verify
from src.supervised.polybench import Selector, family_cv


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', default='polybench', type=experiment_name)
    args = p.parse_args()
    source = ROOT / f"results/{args.name}_train.json"
    output = ROOT / f"results/{args.name}_selection.json"
    model = ROOT / f"models/sl_{args.name}19_bundle.joblib"
    if output.exists() or model.exists():
        raise ValueError("Frozen selection already exists; refusing overwrite")
    raw = json.loads(source.read_text())
    if not raw["complete"] or raw["split"] != "train":
        raise ValueError("Incomplete training experiment")
    programs, diagnostics = verify(raw)
    experiments = {}
    for alpha in [1., 10.]:
        for lower in [False, True]:
            for floor in [.01, .03]:
                key = f"ridge{alpha:g}_{'lower' if lower else 'point'}_floor{floor}"
                cv = family_cv(programs, raw["manifests"], alpha, lower, floor)
                experiments[key] = {"parameters": [alpha, lower, floor], **cv}
    eligible = [k for k,v in experiments.items() if v["eligible"]]
    experimental = max(eligible, key=lambda k: experiments[k]["score"]["utility"]) if eligible else None
    selector = Selector(*experiments[experimental]["parameters"]).fit(programs) if experimental else None
    # CV is conditional on tuning. Frozen cross-family development is needed
    # before promoting a deployment policy; the reserved final tests stay closed.
    decisions = {i["id"]: "O3" for i in raw["inventory"] if i["split"] == "development"}
    bundle = {"default": "O3", "experimental": selector, "protocol": PROTOCOL,
              "training_sha256": sha(source), "training_programs": [p["case"] for p in programs]}
    joblib.dump(bundle, model)
    report = {"training_sha256": sha(source), "bundle_sha256": sha(model), "protocol": PROTOCOL,
              "attempted_programs": sum(i["split"] == "train" for i in raw["inventory"]),
              "correct_programs": len(raw["manifests"]), "qualified_programs": len(programs),
              "qualified_candidate_labels": len(programs)*5,
              "training_programs": [p["case"] for p in programs], "default": "O3",
              "experimental": experimental, "experiments": experiments,
              "development_default_choices": decisions,
              "promotion": "requires frozen cross-family development and final validation",
              "limitations": ["three kernel families maximum in training CV",
                "program bootstrap does not propagate timing uncertainty",
                "candidate hyperparameters chosen using these conditional CV results",
                "scientific kernels and kernel latency differ from end-to-end application runtime"]}
    save(output, report)
    print(json.dumps({k:report[k] for k in ["attempted_programs", "correct_programs", "qualified_programs", "experimental", "default"]}, indent=2))


if __name__ == "__main__":
    main()
