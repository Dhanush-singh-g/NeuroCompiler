#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Use x86_64 Linux or WSL2 Ubuntu22.04 on Windows.' >&2
  exit 1
fi
python3 -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), "Use Python3.10–3.12 (Ubuntu22.04 supplies Python3.10)."'
if ! command -v gcc >/dev/null; then
  echo 'First install prerequisites: sudo apt update && sudo apt install -y python3-venv build-essential libtinfo5' >&2
  exit 1
fi
mkdir -p .presentation
if [[ ! -x .presentation/venv/bin/python ]]; then
  python3 -m venv .presentation/venv
fi
.presentation/venv/bin/python -m pip install --disable-pip-version-check -r presentation/requirements.txt
.presentation/venv/bin/python -m pip check
.presentation/venv/bin/python scripts/install_presentation_toolchain.py "$@"
.presentation/venv/bin/python scripts/serve_presentation.py --check
echo 'Setup passed. Start with: bash scripts/start_presentation.sh'
