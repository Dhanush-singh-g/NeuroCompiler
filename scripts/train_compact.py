"""Fit a new compact selector; never overwrite the legacy model."""
import argparse
import json
from pathlib import Path

import joblib

from src.benchmarks.compact import MENU, save, sha, verify_report
from src.supervised.compact import Selector, cross_validate, grouped_score, select_policy


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=Path("results/compact_train.json"))
    args = p.parse_args()
    model_path = Path("models/sl_compact_selector.joblib")
    output = Path("results/compact_selection.json")
    comparator_path = Path("models/sl_compact_comparators.joblib")
    if model_path.exists() or output.exists() or comparator_path.exists():
        p.error("Model/report already exists; preserve the frozen experiment")
    report = json.loads(args.data.read_text())
    verify_report(report)
    if report["split"] != "train":
        raise ValueError("Only training programs may be fitted")
    rows = report["labels"]
    cv = cross_validate(rows)
    selected = select_policy(cv)
    model = Selector(selected.removeprefix("guarded_"), guarded=True).fit(rows)
    model.training_sha256 = sha(args.data)
    model.menu = MENU
    model_path.parent.mkdir(exist_ok=True)
    joblib.dump(model, model_path)
    comparators = {}
    if len(model.programs) >= 4:
        for mode in ("ridge", "constant"):
            for guarded in (False, True):
                key = ("guarded_" if guarded else "raw_") + mode
                comparators[key] = Selector(mode, guarded).fit(rows)
    joblib.dump(comparators, comparator_path)
    fixed = {choice: grouped_score([
        {"program": r["program"], "log_speedup": r["outcomes"][choice]["log_speedup"]}
        for r in rows]) for choice in MENU}
    result = {"source_sha256": sha(args.data), "model_sha256": sha(model_path),
              "comparator_sha256": sha(comparator_path),
              "selected": selected, "effective_programs": model.programs, "menus": len(rows),
              "cross_validation": cv, "fixed": fixed,
              "selection_rule": "guarded only: CV mean>1.01, program-bootstrap lower>1, worst>=1/1.03; else O3",
              "cv_limitation": "Menu inherited from previous training-wide search; CV is conditional, not an independent estimate of search plus learning generalization",
              "final_calibration": model.calibration}
    save(output, result)
    print(json.dumps({k: result[k] for k in ["selected", "menus", "effective_programs", "fixed"]}, indent=2))


if __name__ == "__main__":
    main()
