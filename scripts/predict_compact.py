"""Static inference and bitcode export, without native timing."""
import argparse
import json
from pathlib import Path

import joblib

from src.benchmarks.compact import MENU, save, sha, verify_manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        p.error("Export already exists")
    m = json.loads(args.manifest.read_text())
    verify_manifest(m, m["split"])
    model_path = Path("models/sl_compact_selector.joblib")
    model = joblib.load(model_path)
    if model.menu != MENU:
        raise ValueError("Model menu differs")
    decision = model.choose(m["features"])
    source = Path(m["artifacts"][decision["configuration"]]["directory"]) / "program.bc"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(source.read_bytes())
    save(args.output.with_suffix(".json"), {"decision": decision, "manifest_sha256": sha(args.manifest),
        "model_sha256": sha(model_path), "bitcode_sha256": sha(args.output), "native_timing": False})
    print(decision["configuration"], sha(args.output))


if __name__ == "__main__":
    main()
