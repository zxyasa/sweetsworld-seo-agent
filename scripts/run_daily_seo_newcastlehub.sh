#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_DIR}/logs"
LOG_FILE="${LOG_DIR}/newcastlehub-daily.log"
PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
RUNNER="${REPO_DIR}/src/run_mvp.py"

mkdir -p "${LOG_DIR}"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "[$(date -Iseconds)] ERROR: Missing python3 at ${PYTHON_BIN}" >> "${LOG_FILE}"
  exit 1
fi

if [ ! -f "${RUNNER}" ]; then
  echo "[$(date -Iseconds)] ERROR: Missing runner at ${RUNNER}" >> "${LOG_FILE}"
  exit 1
fi

cd "${REPO_DIR}"

status=0
{
  echo "[$(date -Iseconds)] INFO: Starting daily SEO run for newcastlehub"
  if "${PYTHON_BIN}" "${RUNNER}" --site newcastlehub --mode daily --generate-topics "$@"; then
    status=0
  else
    status=$?
  fi
  echo "[$(date -Iseconds)] INFO: Daily SEO run for newcastlehub finished with status ${status}"
} >> "${LOG_FILE}" 2>&1

exit ${status}
