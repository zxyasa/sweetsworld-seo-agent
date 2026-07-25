#!/usr/bin/env bash
# One-shot reminder: GA4 cart→checkout funnel check after view_cart/add_shipping_info/add_payment_info
# events went live in GTM container ver 20 (2026-05-03).
# Sends TG message to chxo_bot, optionally pulls quick GA4 event-count snapshot, then self-deletes.

set -u

TG_TOKEN="$(awk -F= '/^TELEGRAM_BOT_TOKEN=/{sub(/^TELEGRAM_BOT_TOKEN=/,""); print; exit}' /Users/michaelzhao/agents/agents/social-network-create-post-agent/.env)"
CHAT_ID="1573193647"
LOG="/Users/michaelzhao/agents/agents/sweetsworld-seo-agent/logs/ga4_funnel_reminder.log"
mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date -u +%FT%TZ)] $*" >> "$LOG"; }

send_tg() {
  curl -sS -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=$1" \
    --data-urlencode "disable_web_page_preview=true" >> "$LOG" 2>&1
  echo "" >> "$LOG"
}

send_tg "📊 GA4 funnel check — view_cart / add_shipping_info / add_payment_info 已 live 48h+

ATC dropoff 真相终于可量化。今晚跑：
1. GA4 → Reports → Engagement → Events 看 3 个新 event 是否有 count
2. 跑 funnel report 比 5/4 Mon vs 4/27 Mon (DOW match) 的:
   - view_item → add_to_cart rate
   - add_to_cart → view_cart rate
   - view_cart → begin_checkout rate
   - begin_checkout → add_shipping_info rate ← NEW
   - add_shipping_info → add_payment_info rate ← NEW
   - add_payment_info → purchase rate

最关心的: shipping_info → payment_info dropoff (验证 H1 假设：\$11.65 freight 显示太晚是否在 shipping step 流失客户)

数据足够 + 有时间就让我帮跑分析报告。"

log "GA4 funnel reminder delivered. Self-cleanup..."

PLIST="$HOME/Library/LaunchAgents/com.sweetsworld.ga4-funnel-check.plist"
if [[ -f "$PLIST" ]]; then
  launchctl unload "$PLIST" >> "$LOG" 2>&1
  rm -f "$PLIST"
  log "Removed $PLIST"
fi
