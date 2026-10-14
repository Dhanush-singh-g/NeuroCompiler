"""Preserve experiment artifacts with a verified per-file checksum manifest."""
import hashlib
import json
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / "results/compact_iteration.zip"
    if destination.exists():
        raise ValueError("Snapshot exists; preserve it")
    files = set(root.glob("*.md")) | {root / ".gitignore"}
    for directory in ("src", "scripts", "tests", "configs"):
        files.update((root / directory).rglob("*.py"))
    files.update((root / "models").glob("*.joblib"))
    files.update(p for p in (root / "data").rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for pattern in ("*.json", "*.bc", "*.ll", "compact_*.log"):
        files.update((root / "results").glob(pattern))
    manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in sorted(files):
            archive.write(p, str(p.relative_to(root)))
        archive.writestr("SHA256_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("Snapshot CRC check failed")
        if set(archive.namelist()) != set(manifest) | {"SHA256_MANIFEST.json"}:
            raise ValueError("Snapshot coverage changed")
        for name, expected in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f"Snapshot checksum failed: {name}")
    print(f"Verified {len(manifest)} files; {destination.stat().st_size:,} bytes; {destination}")


if __name__ == "__main__":
    main()
