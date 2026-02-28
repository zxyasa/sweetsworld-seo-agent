# sweetsworld-seo-agent — Agent Protocol (Codex / All AI Agents)

## Project Overview
SEO automation agent for SweetsWorld

## Commands
```bash
# (fill in project-specific commands)
```

---

# Crash-Safe Protocol

This project uses a file-based task state system in `.ai/` that allows ANY AI agent (Claude Code, Codex, etc.) to resume work after interruption, across any terminal.

## 1. Startup Protocol (MANDATORY — first thing every session)

```
1. Read .ai/active-task.json → get current task name
2. Read .ai/tasks/<task>/progress.md → understand where we left off
3. Read .ai/tasks/<task>/context.md → get minimal file list to read
4. Check .ai/lock.json → is another terminal working?
5. Output a resume plan, wait for user confirmation before doing anything
```

**DO NOT** skip these steps and start scanning the project.
**DO NOT** read project files before reading progress.md.

If `active-task.json` has task=null, ask the user to create a new task.

## 2. Step Protocol

Every step must follow this exact order:

```
1. Announce: "Step N/M: <description>"
2. Make code changes (max 3 files per step)
3. Update .ai/tasks/<task>/progress.md (mark step complete)
4. Update .ai/tasks/<task>/context.md (if key files changed)
5. Suggest git commit: [ai:<task>] step N/M: <description>
6. Wait for user confirmation before next step
```

**Critical: progress.md comes first.** If you can only do one thing, update progress.md.

## 3. File Access Rules

### Allowed
- This file (`AGENTS.md`) and `CLAUDE.md`
- `.ai/active-task.json`
- All files under `.ai/tasks/<current-task>/`
- Files listed in context.md "Key Files" section
- Files found via targeted grep/search (must have specific search target)

### Forbidden
- Reading more than 5 source files at once
- Recursive directory listing of entire project
- Broad "let me understand the project" scanning
- Reading modules unrelated to current task

### To learn about a new module
1. Check context.md "Search Hints" first
2. Use grep to find specific keywords
3. Read only matched files
4. Add newly discovered key files to context.md

## 4. Token Risk Control

| Risk | Condition | Strategy |
|------|-----------|----------|
| LOW | 1-2 files, <50 lines each | Execute directly |
| MEDIUM | 3 files, or >50 lines in one file | Update progress first, then execute |
| HIGH | >3 files, or refactoring | **Must split** into multiple steps |
| CRITICAL | Global rename / large refactor | **Forbidden** in single step, split into sub-tasks |

### Hard Rules
- Max 3 files modified per step
- Max 100 lines changed per file
- No single output exceeding 200 lines of code
- If an operation will consume heavy tokens, warn user and suggest splitting
- When generating test files, one test file per step

## 5. Git Workflow

### Commit message format
```
[ai:<task-name>] step N/M: <short description>

refs: .ai/tasks/<task-name>/progress.md
```

### Helper scripts
```bash
# Standard AI commit
.ai/scripts/ai-commit.sh <task-name> <step> <total> "<message>"

# Emergency save
.ai/scripts/ai-save.sh

# Create new task
.ai/scripts/ai-new-task.sh <task-name> "<goal>"
```

## 6. Multi-Terminal Concurrency

### Terminal IDs
- `windows-vscode`
- `macbook-vscode`
- `iphone-ssh`

### Lock mechanism
- Write `.ai/lock.json` before starting work (terminal ID + timestamp + TTL 30min)
- Lock expires after TTL automatically
- New terminal must update lock before taking over

## 7. Resume Template

When asked to "continue" or "resume":

```
## Resume Report

Task: <task-name>
Last stopped at: Step N/M — <description>
Last terminal: <terminal-id>
Last updated: <timestamp>

### Completed
- Step 1: Done — <description>

### Next
- Step N: Pending — <description>
  - Recovery notes: <from progress.md>

### Files to read
- <from context.md>

### Plan
1. <next action>
2. <action after that>

Waiting for confirmation.
```
