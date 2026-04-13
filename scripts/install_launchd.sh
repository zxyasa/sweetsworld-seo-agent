#!/bin/bash
set -euo pipefail

HOUR="${1:-9}"
MINUTE="${2:-15}"
LABEL="com.sweetsworld.seo-agent.daily"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
RUN_SCRIPT="${REPO_DIR}/scripts/run_daily_seo.sh"
OUT_LOG="${REPO_DIR}/logs/launchd.stdout.log"
ERR_LOG="${REPO_DIR}/logs/launchd.stderr.log"

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
      <string>${RUN_SCRIPT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
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
  </dict>
</plist>
EOF

if launchctl list | grep -q "${LABEL}"; then
  launchctl unload "${PLIST_PATH}" || true
fi

launchctl load "${PLIST_PATH}"

cat <<MSG
Installed launchd job:
  Label: ${LABEL}
  Plist: ${PLIST_PATH}
  Schedule: daily at $(printf '%02d:%02d' "${HOUR}" "${MINUTE}")
  Runner: ${RUN_SCRIPT}

Useful commands:
  launchctl list | grep ${LABEL}
  tail -f "${REPO_DIR}/logs/daily-seo.log"
MSG
