"""Collect the fixed complete-menu LLVM19 scientific-kernel experiment."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save, sha, effect
from src.benchmarks.polybench import PROTOCOL, MENU, ROOT, DEVELOPMENT_INPUT_FIXES, build, cell, experiment_name, inventory, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["train", "development"], default="train")
    parser.add_argument("--name", default="polybench", type=experiment_name)
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    destination = ROOT / f"results/{args.name}_{args.split}.json"
    if destination.exists():
        if not args.resume:
            raise ValueError("Existing experiment; use --resume to verify/continue")
        report = json.loads(destination.read_text())
        _, diagnostics = verify(report)
        if report["complete"]:
            if args.preflight_only:
                ready = bool(diagnostics) and all(d["o3_control"]["control_pass"] for d in diagnostics.values())
                print("Verified existing controls: " + ("passed" if ready else "failed") + "; no new timings.")
                return 0 if ready else 2
            print("Verified completed experiment; no new timings."); return
    else:
        report = {"protocol": PROTOCOL, "inventory": inventory(), "split": args.split,
                  "collector_revision": 2,
                  "manifests": {}, "failures": {}, "records": [], "complete": False}
        if args.split == "development":
            frozen = ROOT / f"results/{args.name}_selection.json"
            if not frozen.exists():
                raise ValueError("Freeze training-only learner before development execution")
            report["frozen_selection_sha256"] = sha(frozen)
            report["development_input_fixes"] = DEVELOPMENT_INPUT_FIXES
        save(destination, report)
    for item in report["inventory"]:
        ident = item["id"]
        if item["split"] != args.split or ident in report["manifests"] or ident in report["failures"]:
            continue
        try:
            base = ROOT / "data/processed/polybench19"
            if args.name != "polybench":
                base = base / args.name
            variant = "development_zeroed" if args.split == "development" else "valid_inputs"
            m = build(item, base / variant / args.split / ident)
            report["manifests"][ident] = m
            print(f"Built {ident}: O0+six pipelines correct, repetitions={m['repetitions']}", flush=True)
        except Exception as error:
            report["failures"][ident] = {"type": type(error).__name__, "message": str(error),
                "stderr": getattr(error, "stderr", b"").decode(errors="replace")}
            print(f"Excluded {ident}: {error}", flush=True)
        save(destination, report)
    if args.build_only:
        print(f"Build summary: {len(report['manifests'])} valid, {len(report['failures'])} excluded.")
        return
    if report.get("collector_revision", 1) != 2:
        raise ValueError("Legacy incomplete collector; preserve it and start a fresh --name experiment")
    if args.split == "development":
        import joblib
        model = ROOT / f"models/sl_{args.name}19_bundle.joblib"
        selection_path = ROOT / f"results/{args.name}_selection.json"
        selection = json.loads(selection_path.read_text())
        if sha(model) != selection["bundle_sha256"] or sha(selection_path) != report["frozen_selection_sha256"]:
            raise ValueError("Changed frozen learner")
        bundle = joblib.load(model)
        if bundle["experimental"] is None:
            raise ValueError("No timing-qualified learner: development correctness is available, timing study is blocked")
        decisions = {ident: {"default": "O3", "experimental":
                     bundle["experimental"].choose(m) if bundle["experimental"] else {"choice": "O3", "scores": {}}}
                     for ident,m in report["manifests"].items()}
        if "frozen_decisions" in report and decisions != report["frozen_decisions"]:
            raise ValueError("Frozen development choices changed")
        report["frozen_decisions"] = decisions
        save(destination, report)
    completed = {(c["case"], c["choice"], c["block"], c["role"]) for c in report["records"]}
    # Require unchanged-code readiness before spending the candidate budget.
    # This first stage also permits a small qualification-only run on a new host.
    for block in range(PROTOCOL["blocks"]):
        for ident,m in sorted(report["manifests"].items()):
            key = (ident,"O3",block,"qualification")
            if key not in completed:
                report["records"].append(cell(m,"O3",block,"qualification"))
                completed.add(key)
                save(destination,report)
    qualifications = {ident: effect([c for c in report["records"] if
        c["case"] == ident and c["role"] == "qualification"], PROTOCOL)
        for ident in report["manifests"]}
    report["preflight_complete"] = True
    report["preflight_ready"] = bool(qualifications) and all(q["control_pass"] for q in qualifications.values())
    save(destination,report)
    if not report["preflight_ready"]:
        print("Preflight failed unchanged-code controls; candidate timing is blocked.",flush=True)
        return 2
    if args.preflight_only:
        print("Preflight passed. Candidate timing has not run.",flush=True)
        return 0
    # Interleave programs and pass choices across blocks to expose slow drift.
    for block in range(PROTOCOL["blocks"]):
        for ident, m in sorted(report["manifests"].items()):
            schedule = [("O3", "qualification")]
            for choice in MENU:
                if choice != "O3" and m["aliases"][choice] == choice:
                    schedule += [(choice, "candidate_control"), (choice, "effect")]
            for choice, role in schedule:
                key = (ident, choice, block, role)
                if key in completed:
                    continue
                report["records"].append(cell(m, choice, block, role))
                save(destination, report)
            print(f"Block {block+1}/{PROTOCOL['blocks']} {ident} complete", flush=True)
    report["complete"] = True
    accepted, diagnostics = verify(report)
    report["accepted"] = accepted
    report["diagnostics"] = diagnostics
    save(destination, report)
    print(f"Complete: {len(report['manifests'])} correct, {len(accepted)} timing-qualified programs.")


if __name__ == "__main__":
    sys.exit(main())
