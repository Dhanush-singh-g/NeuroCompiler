"""Evaluate static decisions frozen before validation timing."""
import json
from pathlib import Path

import joblib

from src.benchmarks.compact import MENU, save, sha, verify_report
from src.supervised.compact import grouped_score


def main():
    report = json.loads(Path("results/compact_validation.json").read_text())
    verify_report(report)
    if report["split"] != "validation":
        raise ValueError("Expected development-validation data")
    model = Path("models/sl_compact_selector.joblib")
    frozen_path = Path("results/compact_validation_decisions.json")
    frozen = json.loads(frozen_path.read_text())
    if sha(model) != report["model_sha256"] or sha(frozen_path) != report["decisions_sha256"]:
        raise ValueError("Frozen validation provenance changed")
    if frozen["decisions"] != report["decisions"] or frozen["model_sha256"] != sha(model):
        raise ValueError("Frozen decisions do not match measured report")
    comparators = Path("models/sl_compact_comparators.joblib")
    if sha(comparators) != frozen["comparator_sha256"] or frozen["comparator_decisions"] != report["comparator_decisions"]:
        raise ValueError("Frozen comparator provenance changed")
    selected_model = joblib.load(model)
    diagnostic_models = joblib.load(comparators)
    if selected_model.training_sha256 != sha("results/compact_train.json"):
        raise ValueError("Training data changed after fitting")
    held_programs = {m["program"] for m in report["manifests"].values()}
    if held_programs & set(selected_model.programs) or any(held_programs & set(m.programs) for m in diagnostic_models.values()):
        raise ValueError("Evaluation contains a fitted program")
    for ident, m in report["manifests"].items():
        if frozen["features"][ident] != m["features"] or selected_model.choose(m["features"]) != frozen["decisions"][ident]:
            raise ValueError("Selected model does not reproduce frozen decision")
        if {name: candidate.choose(m["features"]) for name, candidate in diagnostic_models.items()} != frozen["comparator_decisions"][ident]:
            raise ValueError("Diagnostic models do not reproduce frozen decisions")
    rows = report["labels"]
    records = []
    for row in rows:
        choice = frozen["decisions"][row["case"]]["configuration"]
        outcome = row["outcomes"][choice]
        records.append({"program": row["program"], "case": row["case"], "choice": choice,
                        "log_speedup": outcome["log_speedup"], "confirmed_gain": outcome["confirmed_gain"]})
    fixed = {choice: grouped_score([
        {"program": r["program"], "log_speedup": r["outcomes"][choice]["log_speedup"]}
        for r in rows]) for choice in MENU}
    diagnostic = {}
    for name in next(iter(frozen["comparator_decisions"].values()), {}):
        replay = []
        for r in rows:
            choice = frozen["comparator_decisions"][r["case"]][name]["configuration"]
            outcome = r["outcomes"][choice]
            replay.append({"program": r["program"], "case": r["case"], "choice": choice,
                           "log_speedup": outcome["log_speedup"], "confirmed_gain": outcome["confirmed_gain"]})
        diagnostic[name] = {"score": grouped_score(replay), "records": replay,
                            "changes": sum(r["choice"] != "O3" for r in replay),
                            "confirmed_gains": sum(r["confirmed_gain"] for r in replay)}
    result = {"source_sha256": sha("results/compact_validation.json"),
              "model_sha256": sha(model), "decision_sha256": sha(frozen_path),
              "score": grouped_score(records), "records": records,
              "eligible_complete_menus": len(rows), "excluded_cases": sorted(set(report["manifests"]) - {r["case"] for r in rows}),
              "changes": sum(r["choice"] != "O3" for r in records),
              "confirmed_gains": sum(r["confirmed_gain"] for r in records), "fixed": fixed,
              "frozen_diagnostic_models": diagnostic,
              "scope": "Previously inspected development programs; fresh timings, fit-disjoint, not pristine final test. Related JPEG/TIFF families share library code.",
              "interval_limitation": "Program point-estimate bootstrap omits timing uncertainty; raw per-case paired intervals retained in source. Small program count cannot establish suite-wide generalization."}
    save("results/compact_evaluation.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
