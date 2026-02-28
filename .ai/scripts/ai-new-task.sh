#!/bin/bash
# 快速创建新任务
# 用法: .ai/scripts/ai-new-task.sh <task-name> "<goal>"
set -e

TASK="${1:?用法: ai-new-task.sh <task-name> \"<goal>\"}"
GOAL="${2:?缺少任务目标}"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date -Iseconds)

mkdir -p ".ai/tasks/${TASK}"

# brief.md
cat > ".ai/tasks/${TASK}/brief.md" << INNEREOF
# Task: ${TASK}
Created: ${DATE}
Status: active

## Goal
${GOAL}

## Scope
- (待填写)

## Acceptance Criteria
- [ ] (待填写)
INNEREOF

# plan.md
cat > ".ai/tasks/${TASK}/plan.md" << INNEREOF
# Plan: ${TASK}

## Steps
- [ ] Step 1: (待规划) | Files: TBD | Risk: TBD

## Dependencies
(待填写)

## Estimated Token Budget
Total steps: TBD | High-risk steps: TBD | Recommend: TBD sessions
INNEREOF

# progress.md
cat > ".ai/tasks/${TASK}/progress.md" << INNEREOF
# Progress: ${TASK}
Last updated: ${TIMESTAMP}
Terminal: unknown
Current step: 1 / TBD

## Completed
(none yet)

## Current
- [ ] Step 1: 规划阶段
  - Status: pending
  - Notes: 任务刚创建，等待 AI 读取并制定详细计划

## Remaining
(待规划)

## Recovery Notes
新任务，从 Step 1 开始。AI 需先读取相关源码制定计划。
INNEREOF

# context.md
cat > ".ai/tasks/${TASK}/context.md" << INNEREOF
# Context: ${TASK}
Last updated: ${TIMESTAMP}

## Key Files (ONLY read these on resume)
- (待填写 — AI 首次执行时自动填充)

## Architecture Notes
(待填写)

## Recent Changes Summary
任务刚创建，暂无变更。

## Search Hints
(待填写)
INNEREOF

# 更新 active-task.json
python3 -c "
import json
data = {'task': '${TASK}', 'started': '${TIMESTAMP}', 'terminal': 'unknown', 'step': 1, 'total_steps': 0}
json.dump(data, open('.ai/active-task.json', 'w'), indent=2, ensure_ascii=False)
print('✓ active-task.json updated')
"

echo "✓ 任务 '${TASK}' 已创建"
echo "  .ai/tasks/${TASK}/brief.md"
echo "  .ai/tasks/${TASK}/plan.md"
echo "  .ai/tasks/${TASK}/progress.md"
echo "  .ai/tasks/${TASK}/context.md"
