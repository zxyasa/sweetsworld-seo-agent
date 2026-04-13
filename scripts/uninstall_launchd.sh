#!/bin/bash
set -euo pipefail

LABEL="com.sweetsworld.seo-agent.daily"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [ -f "${PLIST_PATH}" ]; then
  launchctl unload "${PLIST_PATH}" || true
  rm -f "${PLIST_PATH}"
  echo "Removed ${PLIST_PATH}"
else
  echo "No launchd plist found at ${PLIST_PATH}"
fi
