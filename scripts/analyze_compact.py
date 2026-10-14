"""Recompute coverage, exclusions and measured gains from completed raw data."""
import argparse
import json
from pathlib import Path

from src.benchmarks.compact import MENU, effect, save, sha, verify_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "validation"], required=True)
    args = parser.parse_args()
    source = Path(f"results/compact_{args.split}.json")
    report = json.loads(source.read_text())
    verify_report(report)
    accepted = {r["case"]: r for r in report["labels"]}
    coverage = []
    for ident, m in report["manifests"].items():
        records = [r for r in report["records"] if r["case"] == ident]
        profile = report["profiles"][ident]
        q = [r for r in records if r["role"] == "qualification"]
        qualification = effect(q) if q else None
        bad_candidates = []
        for c in dict.fromkeys(m["aliases"].values()):
            controls = [r for r in records if r["role"] == "candidate_control" and r["choice"] == c]
            if controls and not effect(controls)["control_pass"]:
                bad_candidates.append(c)
        reason = ("accepted_complete_menu" if ident in accepted else
                  "outside_duration_range" if not profile["eligible"] else
                  "O3_control_failed" if qualification and not qualification["control_pass"] else
                  "candidate_control_failed")
        coverage.append({"case": ident, "program": m["program"], "status": reason,
                         "o3_qualification": qualification, "bad_candidate_controls": bad_candidates,
                         "outcomes": accepted[ident]["outcomes"] if ident in accepted else None})
    gains = [{"case": r["case"], "program": r["program"], "choice": c, "speedup": s["speedup"],
              "interval": s["interval"]} for r in report["labels"] for c, s in r["outcomes"].items()
             if s["confirmed_gain"]]
    result = {"source_sha256": sha(source), "split": args.split, "coverage": coverage,
              "declared_inputs": len(report["manifests"]),
              "complete_menus": len(report["labels"]),
              "effective_programs": len({r["program"] for r in report["labels"]}),
              "cells": len(report["records"]),
              "paired_timed_executions": sum(len(r["left_seconds"]) + len(r["right_seconds"]) for r in report["records"]),
              "cell_warmup_executions": 2 * len(report["records"]),
              "confirmed_gains": gains,
              "unique_executables": sum(len(set(m["aliases"].values())) for m in report["manifests"].values()),
              "scope": "Empirical per-workload gates, not formal multiple-comparison guarantees; no SL gain claim from training configuration search."}
    save(f"results/compact_{args.split}_analysis.json", result)
    print(json.dumps({k: result[k] for k in ["complete_menus", "effective_programs", "cells", "confirmed_gains"]}, indent=2))


if __name__ == "__main__":
    main()
