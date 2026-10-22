#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .presentation/venv/bin/python ]]; then
  echo 'Run bash scripts/setup_presentation.sh first. See PRESENTATION.md.' >&2
  exit 1
fi
exec .presentation/venv/bin/python scripts/serve_presentation.py "$@"
