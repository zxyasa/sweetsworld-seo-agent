#!/bin/bash
# Install weekly URL health check as a launchd job.
# Runs every Monday at 09:00 AEDT, sends Telegram notification with results.
# Usage: ./scripts/install_url_health_check.sh
set -euo pipefail

LABEL="com.sweetsworld.seo-agent.url-health"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
OUT_LOG="${REPO_DIR}/logs/url_health.stdout.log"
ERR_LOG="${REPO_DIR}/logs/url_health.stderr.log"

mkdir -p "${LAUNCH_AGENTS_DIR}" "${REPO_DIR}/logs"

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
      <string>-c</string>
      <string>cd ${REPO_DIR} &amp;&amp; /opt/homebrew/bin/python3 src/url_health_check.py --notify</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Weekday</key>
      <integer>2</integer>
      <key>Hour</key>
      <integer>9</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${OUT_LOG}</string>
    <key>StandardErrorPath</key>
    <string>${ERR_LOG}</string>
    <key>RunAtLoad</key>
    <false/>
  </dict>
</plist>
EOF

# Unload existing if present
launchctl unload "${PLIST_PATH}" 2>/dev/null || true
launchctl load "${PLIST_PATH}"

echo "✅ Installed: ${LABEL}"
echo "   Schedule: Every Tuesday 09:00 AEDT"
echo "   Logs:     ${OUT_LOG}"
echo "   Plist:    ${PLIST_PATH}"
