#!/usr/bin/env bash
# SW Daily Top-5 Phase 2 milestone reminder runner.
# Sends a TG message via chxo_bot, optionally runs a check command, then
# self-unloads + deletes its own plist (true one-shot).
#
# Usage: sw_phase2_milestone_runner.sh <milestone_number 1..7>

set -u

N="${1:-}"
if [[ -z "$N" ]]; then
  echo "Usage: $0 <milestone 1..7>" >&2
  exit 2
fi

TG_TOKEN="$(awk -F= '/^TELEGRAM_BOT_TOKEN=/{sub(/^TELEGRAM_BOT_TOKEN=/,""); print; exit}' /Users/michaelzhao/agents/agents/social-network-create-post-agent/.env)"
CHAT_ID="1573193647"
MC_PY="/Users/michaelzhao/agents/apps/marketing-copilot/.venv/bin/python"
SCRIPTS="/Users/michaelzhao/agents/apps/marketing-copilot/scripts"
LOG="/Users/michaelzhao/agents/agents/sweetsworld-seo-agent/logs/phase2_milestone_${N}.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -u +%FT%TZ)] $*" >> "$LOG"; }

send_tg() {
  local text="$1"
  curl -sS -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${text}" \
    --data-urlencode "disable_web_page_preview=true" \
    >> "$LOG" 2>&1
  echo "" >> "$LOG"
}

TIMEOUT_BIN="$(command -v gtimeout || command -v timeout || echo /opt/homebrew/bin/gtimeout)"

run_check() {
  local label="$1"; shift
  local out
  out="$("$TIMEOUT_BIN" 90 "$@" 2>&1 | head -c 2000)" || out="${out}\n[exit=$?]"
  send_tg "🔍 ${label} output:
\`\`\`
${out}
\`\`\`"
}

case "$N" in
  1)
    send_tg "🔔 今天 5 min 任务：在 Meta Business Suite UI 建 3 个 retargeting Custom Audience（明天 Phase 2 ramp1 启动）。脚本里有逐步 UI 操作说明。"
    run_check "retargeting --show-ui-instructions" "$MC_PY" "$SCRIPTS/sw_retargeting_audiences.py" --show-ui-instructions
    ;;
  2)
    send_tg "🚀 Phase 2 Week 1 ramp1 今天启动。Cron 自动 fire 00:00/08:00/12:30/20:00/21:00。本周配额：3 IG Reel + 2 Carousel + 14 IG Story + 2 FB Reel + 7 FB Story。盯 reach 不能 WoW 掉 >20%。"
    run_check "killswitch --status" "$MC_PY" "$SCRIPTS/sw_publish_killswitch.py" --status
    ;;
  3)
    send_tg "📊 Week 1 ramp1 复盘：3 个 audience 是否 ≥100 users？≥100 → 今晚写 retargeting yaml PAUSED + 周末 ramp1→ramp2；<100 → ramp1 多挂一周。"
    run_check "retargeting --list" "$MC_PY" "$SCRIPTS/sw_retargeting_audiences.py" --list
    ;;
  4)
    send_tg "📈 Week 2 ramp2 末：(a) reach 不掉 >25% WoW；(b) retargeting yaml ready PAUSED；(c) \$5/天预算来源决定：(A) 加在上面 OR (B) 从 cold ASC/LAL 抠。然后手动 toggle ENABLED in Ads Manager。本周末 ramp2→ramp3。"
    ;;
  5)
    send_tg "🎯 Retargeting layer 7-day 首评：warm CR（sw_ig_reel_viewers_75pct + sw_fb_page_engaged_30d + sw_pdp_visit_no_purchase_7d 三套 ad set 合并）vs cold CR（现有 ASC/LAL）。需 ≥3% warm vs ~1.5% cold 才算 lift。ads-ops daily 报告里有。本周末 ramp3→steady。"
    ;;
  6)
    send_tg "⚠️ Week 7 attribution check：GA4 attribution_log + WC HPOS 直查近 30 天，社媒可归因营收朝 \$200/月走？<\$100 → 下周 5 kill criteria 大概率触发，提前预备 halt 决定。"
    ;;
  7)
    send_tg "🔪 Week 8 KILL verdict：<\$200/月 → KILL 全 pipeline（跑 sw_publish_killswitch.py --halt-all + 卸 launchd plists）。\$200-500 → 维持当前 cadence。>\$500 → scale Phase 2.5（加第 6 个 surface 或加视频预算）。Retargeting 单层 <\$50/月 → 单杀该层。"
    ;;
  *)
    send_tg "❓ 未知 milestone N=${N}"
    log "Unknown milestone: $N"
    exit 3
    ;;
esac

log "Milestone $N delivered. Self-cleanup..."

# Self-cleanup: unload + remove own plist
PLIST="$HOME/Library/LaunchAgents/com.sweetsworld.phase2-milestone-${N}.plist"
LABEL="com.sweetsworld.phase2-milestone-${N}"
if [[ -f "$PLIST" ]]; then
  launchctl unload "$PLIST" >> "$LOG" 2>&1
  rm -f "$PLIST"
  log "Removed $PLIST"
  send_tg "🧹 Phase 2 milestone ${N} 提醒已发送，plist 已自删。"
else
  log "Plist not found at $PLIST (may already be removed)"
fi
