"""Extract fresh static candidate features from existing frozen executable menus."""
import argparse
import json
from pathlib import Path

from src.benchmarks.compact import save, sha, verify_report
from src.features.transform import FEATURE_NAMES, extract_manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", choices=["train", "validation"], required=True)
    args = p.parse_args()
    source = Path(f"results/compact_{args.split}.json")
    output = Path(f"data/processed/transform_{args.split}.json")
    if output.exists():
        p.error("Features exist; preserve this experiment")
    raw = json.loads(source.read_text())
    verify_report(raw)
    report = {"schema": 1, "split": args.split, "source_sha256": sha(source),
              "feature_names": FEATURE_NAMES, "cases": {}}
    for ident, manifest in raw["manifests"].items():
        print("FEATURES", ident, flush=True)
        report["cases"][ident] = extract_manifest(manifest)
    save(output, report)
    print("COMPLETE", len(report["cases"]), "static menus", len(FEATURE_NAMES), "features")


if __name__ == "__main__":
    main()
