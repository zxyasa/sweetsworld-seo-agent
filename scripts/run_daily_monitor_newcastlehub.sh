#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

exec /bin/bash "${REPO_DIR}/scripts/run_daily_monitor.sh" newcastlehub "$@"
