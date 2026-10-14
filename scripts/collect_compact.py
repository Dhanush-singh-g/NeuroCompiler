"""python -m scripts.collect_compact --split train [--resume]"""
import argparse
import json
import platform
import random
from pathlib import Path

import joblib
import numpy as np

from src.benchmarks.compact import (MENU, PROTOCOL, SEED, case_id, effect, freeze,
    measure_cell, run, save, scope, sha, summarize, verify_report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", choices=["train", "validation"], required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--model", type=Path)
    p.add_argument("--comparators", type=Path)
    args = p.parse_args()
    output = Path(f"results/compact_{args.split}.json")
    if args.split == "validation" and not args.model:
        p.error("Validation requires a frozen trained model")
    if args.split == "train" and (args.model or args.comparators):
        p.error("Training collection cannot use models")
    if args.split == "validation" and args.comparators is None:
        args.comparators = Path("models/sl_compact_comparators.joblib")
    if output.exists():
        if not args.resume:
            p.error("Output exists; use --resume to verify/resume")
        report = json.loads(output.read_text())
        verify_report(report, completed=report["complete"])
        if args.model and sha(args.model) != report["model_sha256"]:
            raise ValueError("Frozen model changed")
        if args.comparators and sha(args.comparators) != report["comparator_sha256"]:
            raise ValueError("Frozen comparator models changed")
        if report["complete"]:
            print("Complete experiment verified; no timings repeated", flush=True)
            return
    else:
        report = {"schema": 1, "protocol": PROTOCOL, "split": args.split, "complete": False,
                  "platform": platform.platform(), "manifests": {}, "profiles": {}, "records": [],
                  "labels": [], "decisions": {}, "model_sha256": sha(args.model) if args.model else None}
        report["comparator_sha256"] = sha(args.comparators) if args.comparators else None
        report["comparator_decisions"] = {}
        save(output, report)
    model = joblib.load(args.model) if args.model else None
    comparators = joblib.load(args.comparators) if args.comparators else {}
    if model:
        validation_programs = {f"benchmark://cbench-v1/{c[0]}" for c in scope("validation")}
        if model.menu != MENU or model.training_sha256 != sha("results/compact_train.json"):
            raise ValueError("Model menu/training provenance mismatch")
        if set(model.programs) & validation_programs or any(set(m.programs) & validation_programs for m in comparators.values()):
            raise ValueError("Validation program present in model training")
    for case in scope(args.split):
        ident = case_id(case)
        if ident not in report["manifests"]:
            print("BUILD", ident, flush=True)
            m = freeze(case, Path(f"data/processed/compact_{args.split}") / ident, args.split)
            report["manifests"][ident] = m
            if model:
                report["decisions"][ident] = model.choose(m["features"])
                report["comparator_decisions"][ident] = {
                    name: candidate.choose(m["features"]) for name, candidate in comparators.items()}
            # Freeze the static decision before even the O3 duration profile.
            save(output, report)
        if ident not in report["profiles"]:
            m = report["manifests"][ident]
            run(m, "O3", True)
            times = [run(m, "O3") for _ in range(PROTOCOL["profile_runs"])]
            eligible = PROTOCOL["duration_seconds"][0] <= float(np.median(times)) <= PROTOCOL["duration_seconds"][1]
            report["profiles"][ident] = {"seconds": times, "eligible": bool(eligible)}
            save(output, report)
            print("PROFILE", ident, round(float(np.median(times)), 4), "eligible", eligible, flush=True)
    if model:
        frozen = {"model_sha256": report["model_sha256"], "decisions": report["decisions"],
                  "comparator_sha256": report["comparator_sha256"],
                  "comparator_decisions": report["comparator_decisions"],
                  "features": {k: m["features"] for k, m in report["manifests"].items()}}
        decision_path = Path("results/compact_validation_decisions.json")
        if decision_path.exists() and json.loads(decision_path.read_text()) != frozen:
            raise ValueError("Validation decisions changed")
        save(decision_path, frozen)
        report["decisions_sha256"] = sha(decision_path)
        save(output, report)
    rng = random.Random(SEED)
    eligible = [k for k, v in report["profiles"].items() if v["eligible"]]
    done = {(r["case"], r["role"], r["choice"], r["block"]) for r in report["records"]}
    for phase in ("qualification", "candidates"):
        for block in range(PROTOCOL["blocks"]):
            jobs = []
            for ident in eligible:
                m = report["manifests"][ident]
                if phase == "qualification":
                    jobs.append((ident, "O3", "O3", "qualification"))
                else:
                    q = [r for r in report["records"] if r["case"] == ident and r["role"] == "qualification"]
                    if not effect(q)["control_pass"]:
                        continue
                    for choice in dict.fromkeys(m["aliases"].values()):
                        if choice != "O3":
                            jobs.extend([(ident, choice, choice, "candidate_control"),
                                         (ident, "O3", choice, "effect")])
            rng.shuffle(jobs)
            for ident, left, right, role in jobs:
                first = rng.choice([True, False])
                choice = right if role == "effect" else left
                key = (ident, role, choice, block)
                if key in done:
                    continue
                record = measure_cell(report["manifests"][ident], left, right, block, role, first)
                report["records"].append(record)
                save(output, report)
                done.add(key)
                print("CELL", len(done), phase, block, ident, choice, role, flush=True)
    report["labels"] = summarize(report)
    report["complete"] = True
    verify_report(report)
    save(output, report)
    print("COMPLETE", len(report["labels"]), "complete menus",
          len({r["program"] for r in report["labels"]}), "programs", flush=True)


if __name__ == "__main__":
    main()
