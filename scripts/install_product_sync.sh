#!/bin/bash
# Install weekly WooCommerce product catalog sync as a launchd job.
# Runs every Monday at 08:00 AEDT.
# Usage: ./scripts/install_product_sync.sh
set -euo pipefail

LABEL="com.sweetsworld.seo-agent.product-sync"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
OUT_LOG="${REPO_DIR}/logs/product_sync.stdout.log"
ERR_LOG="${REPO_DIR}/logs/product_sync.stderr.log"

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
      <string>cd ${REPO_DIR} &amp;&amp; /opt/homebrew/bin/python3 src/sync_product_catalog.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Weekday</key>
      <integer>1</integer>
      <key>Hour</key>
      <integer>8</integer>
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

launchctl unload "${PLIST_PATH}" 2>/dev/null || true
launchctl load "${PLIST_PATH}"

echo "✅ Installed: ${LABEL}"
echo "   Schedule: Every Monday 08:00 AEDT"
echo "   Logs:     ${OUT_LOG}"
echo "   Plist:    ${PLIST_PATH}"
