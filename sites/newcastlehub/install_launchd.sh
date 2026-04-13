#!/bin/bash
# Install launchd job for newcastlehub daily SEO publishing.
# Run once: bash sites/newcastlehub/install_launchd.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLIST_SRC="${SCRIPT_DIR}/com.newcastlehub.seo-agent.daily.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.newcastlehub.seo-agent.daily.plist"
LABEL="com.newcastlehub.seo-agent.daily"
RUN_SCRIPT="${REPO_DIR}/scripts/run_daily_seo_newcastlehub.sh"

# Make the run script executable
chmod +x "${RUN_SCRIPT}"

# Unload old job if present
launchctl unload "${PLIST_DST}" 2>/dev/null || true

# Copy plist
cp "${PLIST_SRC}" "${PLIST_DST}"
echo "Installed: ${PLIST_DST}"

# Load job
launchctl load "${PLIST_DST}"
echo "Loaded:    ${LABEL}"
echo ""
echo "Schedule:  daily at 11:00 (offset from sweetsworld at 10:30)"
echo "Logs:      logs/newcastlehub-daily.log"
echo ""
echo "To uninstall:"
echo "  launchctl unload ${PLIST_DST} && rm ${PLIST_DST}"
