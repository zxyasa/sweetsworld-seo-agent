#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="${0:A:h:h}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"
PROVIDERS="${AIO_PROVIDERS:-openai,google}"
REPLICATES="${AIO_REPLICATES:-2}"

cd "$PROJECT_ROOT"
"$PYTHON_BIN" scripts/aio_probe.py --live --trigger launchd --providers "$PROVIDERS" --replicates "$REPLICATES"
"$PYTHON_BIN" scripts/aio_report.py
