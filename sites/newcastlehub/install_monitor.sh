#!/bin/bash
# Install launchd job for newcastlehub daily monitoring.
# Run once: bash sites/newcastlehub/install_monitor.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLIST_SRC="${SCRIPT_DIR}/com.newcastlehub.seo-agent.monitor.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.newcastlehub.seo-agent.monitor.plist"
LABEL="com.newcastlehub.seo-agent.monitor"
RUN_SCRIPT="${REPO_DIR}/scripts/run_daily_monitor_newcastlehub.sh"

chmod +x "${RUN_SCRIPT}"

launchctl unload "${PLIST_DST}" 2>/dev/null || true

cp "${PLIST_SRC}" "${PLIST_DST}"
echo "Installed: ${PLIST_DST}"

launchctl load "${PLIST_DST}"
echo "Loaded:    ${LABEL}"
echo ""
echo "Schedule:  daily at 10:30 (30 minutes before newcastlehub publishing)"
echo "Logs:      logs/newcastlehub-monitor.log"
echo ""
echo "To uninstall:"
echo "  launchctl unload ${PLIST_DST} && rm ${PLIST_DST}"
