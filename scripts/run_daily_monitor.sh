#!/bin/bash
# Daily SEO monitoring: regenerate dashboard + evaluate pilot gate + notify Telegram.
# Runs independently of the daily publishing job (run_daily_seo.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SITE_ID="${1:-}"
LOG_DIR="${REPO_DIR}/logs"
LOG_FILE="${LOG_DIR}/daily-monitor.log"
PYTHON_BIN="${REPO_DIR}/.venv/bin/python"

if [ -n "${SITE_ID}" ]; then
  LOG_FILE="${LOG_DIR}/${SITE_ID}-monitor.log"
fi

mkdir -p "${LOG_DIR}"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "[$(date -Iseconds)] ERROR: Missing virtualenv at ${PYTHON_BIN}" >> "${LOG_FILE}"
  exit 1
fi

cd "${REPO_DIR}"

{
  if [ -n "${SITE_ID}" ]; then
    echo "[$(date -Iseconds)] INFO: Starting daily monitor for ${SITE_ID}"

    "${PYTHON_BIN}" src/analytics_engine.py \
      --site "${SITE_ID}" \
      --days 7

    "${PYTHON_BIN}" src/pilot_gate.py \
      --site "${SITE_ID}" \
      --days 7 \
      --notify

    echo "[$(date -Iseconds)] INFO: Daily monitor complete for ${SITE_ID}"
  else
    echo "[$(date -Iseconds)] INFO: Starting daily monitor"

    "${PYTHON_BIN}" src/analytics_engine.py \
      --days 7 \
      --output reports/seo_dashboard.md

    "${PYTHON_BIN}" src/pilot_gate.py \
      --days 7 \
      --json-output reports/pilot_gate.json \
      --md-output reports/pilot_gate.md \
      --notify

    echo "[$(date -Iseconds)] INFO: Daily monitor complete"
  fi
} >> "${LOG_FILE}" 2>&1
