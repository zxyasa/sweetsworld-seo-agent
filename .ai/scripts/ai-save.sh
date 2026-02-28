#!/bin/bash
# AI 紧急保存 — token 用尽前 / 定时备份
# 用法: .ai/scripts/ai-save.sh [可选备注]
# 定时: watch -n 600 .ai/scripts/ai-save.sh "auto"
set -e

NOTE="${1:-}"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

TASK="unknown"
if [ -f ".ai/active-task.json" ]; then
    TASK=$(python3 -c "import json; print(json.load(open('.ai/active-task.json')).get('task') or 'unknown')" 2>/dev/null || echo "unknown")
fi

if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "没有需要保存的变更。"
    exit 0
fi

git add -A
MSG="[ai:autosave] ${TIMESTAMP} task:${TASK}"
[ -n "$NOTE" ] && MSG="${MSG} — ${NOTE}"
git commit -m "$MSG"
echo "✓ 已保存: $MSG"
