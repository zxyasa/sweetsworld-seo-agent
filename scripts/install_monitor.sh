#!/bin/bash
# Install the daily SEO monitor as a launchd job.
# Usage: ./scripts/install_monitor.sh [HOUR] [MINUTE]
# Default: runs at 10:00 AEDT (00:00 UTC)
set -euo pipefail

HOUR="${1:-10}"
MINUTE="${2:-0}"
LABEL="com.sweetsworld.seo-agent.monitor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
RUN_SCRIPT="${REPO_DIR}/scripts/run_daily_monitor.sh"
OUT_LOG="${REPO_DIR}/logs/monitor.stdout.log"
ERR_LOG="${REPO_DIR}/logs/monitor.stderr.log"

mkdir -p "${LAUNCH_AGENTS_DIR}" "${REPO_DIR}/logs"
chmod +x "${RUN_SCRIPT}"

cat > "${PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${RUN_SCRIPT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>RunAtLoad</key>
    <false/>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>${HOUR}</integer>
      <key>Minute</key>
      <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${OUT_LOG}</string>
    <key>StandardErrorPath</key>
    <string>${ERR_LOG}</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
  </dict>
</plist>
EOF

# Unload if already running, then load fresh
launchctl unload "${PLIST_PATH}" 2>/dev/null || true
launchctl load "${PLIST_PATH}"

echo "Installed: ${LABEL}"
echo "Runs daily at ${HOUR}:$(printf '%02d' ${MINUTE}) local time"
echo "Plist: ${PLIST_PATH}"
echo "Log:   ${REPO_DIR}/logs/daily-monitor.log"
echo ""
echo "To uninstall: launchctl unload '${PLIST_PATH}' && rm '${PLIST_PATH}'"
echo "To test now:  bash '${RUN_SCRIPT}'"
