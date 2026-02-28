# sweetsworld-seo-agent — Claude 行为约束协议

## 项目简介
SEO automation agent for SweetsWorld

## 运行命令
```bash
# (请根据项目实际情况补充)
```

---

# AI 防爆仓协议 (Crash-Safe Protocol)

## 一、启动协议 (MANDATORY — 每次新会话第一步)

```
1. 读取 .ai/active-task.json → 获取当前任务名
2. 读取 .ai/tasks/<task>/progress.md → 了解进度
3. 读取 .ai/tasks/<task>/context.md → 获取最小上下文
4. 检查 .ai/lock.json → 是否有其他终端占用
5. 输出续跑计划，等待用户确认后再动手
```

**禁止**: 跳过上述步骤直接开始工作。
**禁止**: 在没有读取 progress.md 的情况下扫描项目文件。

如果 `.ai/active-task.json` 中 task 为 null，提示用户创建新任务。

## 二、步进执行协议 (Step Protocol)

每个步骤必须严格按以下顺序执行：

```
1. 宣布当前步骤: "Step N/M: <描述>"
2. 执行代码修改（最多 3 个文件）
3. 更新 .ai/tasks/<task>/progress.md（标记当前步骤完成）
4. 更新 .ai/tasks/<task>/context.md（如果关键文件清单变化）
5. 建议 git commit: [ai:<task>] step N/M: <描述>
6. 等待用户确认后再执行下一步
```

**关键原则: progress.md 先于一切。** 如果只能做一件事，就是更新 progress.md。

## 三、禁止全仓扫描规则

### 允许读取的文件
- `CLAUDE.md`（本文件）
- `.ai/active-task.json`
- `.ai/tasks/<当前任务>/` 下的所有文件
- `context.md` 中 "Key Files" 列出的文件
- `Grep` 精确搜索命中的文件（必须有明确搜索目标）

### 禁止
- 禁止一次性读取超过 5 个源码文件
- 禁止递归列目录获取全项目结构
- 禁止 "先了解一下项目" 式的大范围扫描
- 禁止读取与当前任务无关的模块

### 如需了解新模块
1. 先在 context.md 的 Search Hints 中查找线索
2. 用 Grep 精确搜索关键词
3. 只读命中的文件
4. 将新发现的关键文件加入 context.md

## 四、Token 风险控制

| 风险等级 | 条件 | 策略 |
|---------|------|------|
| LOW | 修改 1-2 文件，每文件 < 50 行变更 | 直接执行 |
| MEDIUM | 修改 3 文件，或单文件 > 50 行变更 | 先更新 progress，再执行 |
| HIGH | 修改 > 3 文件，或涉及重构 | **必须拆分**为多个 step |
| CRITICAL | 全局重命名/大规模重构 | **禁止**单步执行，拆分为独立子任务 |

### 强制规则
- 单步修改不超过 3 个文件
- 单个文件修改不超过 100 行
- 禁止一次性输出超过 200 行代码
- 如果预估操作会消耗大量 token，必须提前告知用户并建议拆分
- 生成测试文件时，每个测试文件单独一步

## 五、Git 工作流

### Commit message 格式
```
[ai:<task-name>] step N/M: <简短描述>

refs: .ai/tasks/<task-name>/progress.md
```

### 快捷脚本
```bash
# 标准 AI commit
.ai/scripts/ai-commit.sh <task-name> <step> <total> "<message>"

# 紧急保存（token 即将用尽时）
.ai/scripts/ai-save.sh

# 创建新任务
.ai/scripts/ai-new-task.sh <task-name> "<goal>"
```

### 恢复上下文
```bash
git log --oneline --grep="\[ai:" -20
```

## 六、多终端并发控制

### Terminal ID 规范
- `windows-vscode`
- `macbook-vscode`
- `iphone-ssh`

### 锁机制
- 开始工作前写入 `.ai/lock.json`（含终端 ID + 时间戳 + TTL 30 分钟）
- 锁超过 TTL 自动视为过期
- 新终端接管时必须先更新锁

### 续跑流程
```
1. 读 .ai/lock.json
2. 如果锁存在且未过期 → 提示 "另一终端正在工作，是否强制接管？"
3. 如果锁不存在或已过期 → 获取锁
4. 执行启动协议（见第一节）
```

## 七、续跑模板 (Resume Template)

当被要求"继续"或"续跑"时，输出以下格式：

```markdown
## 续跑报告

**任务**: <task-name>
**上次停在**: Step N/M — <描述>
**上次终端**: <terminal-id>
**上次时间**: <timestamp>

### 已完成
- Step 1: done — <描述>
- Step 2: done — <描述>

### 当前待续
- Step N: pending — <描述>
  - 恢复说明: <从 progress.md 的 Recovery Notes 获取>

### 需要读取的文件
- <从 context.md 获取>

### 续跑计划
1. <下一步要做什么>
2. <再下一步>

等待确认后开始执行。
```

## 八、安全启动模板 (Cold Start Template)

当没有活跃任务时：

```markdown
## 新任务创建

当前没有活跃任务。请提供：
1. **任务名称**: (英文短横线格式，如 add-test-suite)
2. **任务目标**: (一句话)
3. **涉及模块**: (哪些源码目录)

我将创建:
- .ai/tasks/<name>/brief.md
- .ai/tasks/<name>/plan.md
- .ai/tasks/<name>/progress.md
- .ai/tasks/<name>/context.md
并更新 .ai/active-task.json
```
