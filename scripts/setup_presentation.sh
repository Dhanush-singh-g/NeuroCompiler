#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Use x86_64 Linux or WSL2 Ubuntu22.04 on Windows.' >&2
  exit 1
fi
presentation_python=''
if [[ -n "${NEUROCOMPILER_PYTHON:-}" ]]; then
  presentation_candidates=("$NEUROCOMPILER_PYTHON")
else
  presentation_candidates=(/usr/bin/python3 /usr/local/bin/python3 python3.12 python3.11 python3.10 python3)
fi
for candidate in "${presentation_candidates[@]}"; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,12)' 2>/dev/null; then
    presentation_python="$candidate"
    break
  fi
done
if [[ -z "$presentation_python" ]]; then
  echo 'No Python3.10–3.12 found. Use Ubuntu22.04 system Python or set NEUROCOMPILER_PYTHON to a compatible interpreter.' >&2
  exit 1
fi
echo "Using $presentation_python: $("$presentation_python" --version)"
if ! command -v gcc >/dev/null; then
  echo 'First install prerequisites: sudo apt update && sudo apt install -y python3-venv build-essential libtinfo5' >&2
  exit 1
fi
mkdir -p .presentation
if [[ ! -x .presentation/venv/bin/python ]]; then
  "$presentation_python" -m venv .presentation/venv
fi
.presentation/venv/bin/python -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), "Existing app venv uses unsupported Python; rename .presentation/venv and rerun setup."'
.presentation/venv/bin/python -m pip install --disable-pip-version-check -r presentation/requirements.txt
.presentation/venv/bin/python -m pip check
.presentation/venv/bin/python scripts/install_presentation_toolchain.py "$@"
.presentation/venv/bin/python scripts/serve_presentation.py --check
echo 'Setup passed. Start with: bash scripts/start_presentation.sh'
