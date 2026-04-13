#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_DIR}/logs"
LOG_FILE="${LOG_DIR}/daily-seo.log"
PYTHON_BIN="/opt/homebrew/bin/python3"
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
  echo "[$(date -Iseconds)] INFO: Starting daily SEO run for sweetsworld"
  if "${PYTHON_BIN}" "${RUNNER}" --site sweetsworld --mode daily --generate-topics "$@"; then
    status=0
  else
    status=$?
  fi
  echo "[$(date -Iseconds)] INFO: Daily SEO run for sweetsworld finished with status ${status}"
} >> "${LOG_FILE}" 2>&1

exit ${status}
