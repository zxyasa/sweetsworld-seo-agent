#!/bin/bash
# AI 标准化小步 commit
# 用法: .ai/scripts/ai-commit.sh <task-name> <step> <total> "<message>"
set -e

TASK="${1:?用法: ai-commit.sh <task-name> <step> <total> \"<message>\"}"
STEP="${2:?缺少 step 编号}"
TOTAL="${3:?缺少 total 步数}"
MSG="${4:?缺少 commit message}"

PROGRESS_FILE=".ai/tasks/${TASK}/progress.md"
if [ -f "$PROGRESS_FILE" ]; then
    if ! git diff --name-only --cached -- "$PROGRESS_FILE" | grep -q . && \
       ! git diff --name-only -- "$PROGRESS_FILE" | grep -q .; then
        echo "⚠️  警告: progress.md 未被修改。请先更新进度再 commit。"
        read -p "是否继续? (y/N) " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
fi

git add -A
git commit -m "[ai:${TASK}] step ${STEP}/${TOTAL}: ${MSG}

refs: .ai/tasks/${TASK}/progress.md"

echo "✓ Committed: [ai:${TASK}] step ${STEP}/${TOTAL}: ${MSG}"
