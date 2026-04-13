# sweetsworld-seo-agent — Claude 行为约束协议

> **全局计划**: `apps/website-os/CLAUDE.md` — 开工前必读，了解当前阶段和跨项目进度
> **本项目当前阶段**: P1 运行中 → P2 待开始（接入 GSC 实时数据、33个质量不达标页面重新生成）

## 项目简介

多站点 SEO 内容自动化系统。支持：
- **sweetsworld.com.au** — 澳洲糖果电商 SEO 内容
- **newcastlehub.info** — 纽卡素本地商业服务 SEO 内容

每个站点有独立配置、数据目录、topics 队列，共享同一套 Python 引擎。

## 项目结构（关键路径）

```
src/
  run_mvp.py              # 主入口，--site 参数选站点
  config.py               # Settings dataclass，读取 .env
  site_context.py         # SiteContext dataclass，读取 site.json
  content_brief_engine.py # Brief 生成（内链、FAQ、产品匹配）
  content_generator.py    # SiteProfile + HTML 内容生成
  openai_generator.py     # OpenAI/LLM API 调用封装
  page_type_strategies/   # 8 种页面类型策略
  page_type_registry.py   # 策略注册表

sites/
  sweetsworld/
    site.json             # 站点配置（prompt_config、collection_paths 等）
    .env                  # WP/API 凭证
    data/topics.db        # SQLite 队列（224 条）
  newcastlehub/
    site.json
    .env
    data/topics.db        # SQLite 队列

apps/
  growth-graph/           # Entity Graph + Command Center（AIO Growth OS）
  wordpress-ai-ops/       # 批量 WP 操作脚本（FAQ注入、内链、提交GSC）
```

## 运行命令

```bash
cd /Users/michaelzhao/agents/agents/sweetsworld-seo-agent

# 发布 sweetsworld（默认站点）
python src/run_mvp.py --site sweetsworld --dry-run    # 预览
python src/run_mvp.py --site sweetsworld               # 实际发布

# 发布 newcastlehub
python src/run_mvp.py --site newcastlehub --dry-run
python src/run_mvp.py --site newcastlehub

# 加载对应站点的 .env
export $(cat sites/newcastlehub/.env | xargs) && python src/run_mvp.py --site newcastlehub
```

## 已激活的 launchd 定时任务

| 任务 | 时间 | 脚本 |
|------|------|------|
| `com.sweetsworld.seo-agent.daily` | 每天 10:30 | sweetsworld 自动发布 |
| `com.sweetsworld.seo-agent.monitor` | 每天 10:00 | pilot_gate + GSC 推送 |
| `com.sweetsworld.seo-agent.url-health` | 每周二 09:00 | 产品 URL 健康检查 |
| `com.sweetsworld.growth-graph.weekly` | 每周一 09:00 | Entity Graph 重建 |

## 关键 .env 变量

```
WP_BASE_URL          # WordPress 站点地址
WP_USERNAME          # WordPress 用户名
WP_APP_PASSWORD      # WordPress 应用密码
OPENAI_API_KEY       # 内容生成（GPT-4o）
ANTHROPIC_API_KEY    # Claude API（备用）
TELEGRAM_BOT_TOKEN   # Telegram 通知
TELEGRAM_CHAT_ID     # Telegram 聊天 ID
USE_AI_GENERATION    # true/false
SEO_STATE_FILE       # 每日配额状态文件路径（多站点时各自独立）
```

## 多站点注意事项

- 每个站点的 `site.json` 包含 `prompt_config`（AI 写作指令）— 禁止在 Python 代码里写站点专用文案
- `sites/<site_id>/data/seo_daily_state.json` 是各站点独立的配额状态
- `os.environ["WP_BASE_URL"]` 在 run_mvp.py 里被动态覆盖，确保所有 helper 使用正确的站点 URL
- 新站点：在 `sites/` 下创建目录 + `site.json` + `.env` + `data/`，无需改 Python 代码

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

## Known Issues (from 2026-04-05 code review)

- [FIXED 2026-04-07] `src/wp_client.py:331` — bridge token hardcoded → now reads `WP_SEO_BRIDGE_TOKEN` env var at call time, returns False with warning if unset
- [FIXED 2026-04-07] `src/wp_client.py:336` — SEO meta passed via GET query params → changed `json=payload` to `data=payload` in `write_seo_meta_via_db` so token+meta go in POST form body (PHP `$_POST`-readable), not URL query string
- [FIXED 2026-04-07] `src/citation_planner.py:284` — `_build_hashtags()` causes test failures → added `safe_keyword = keyword or ""` guard before `.split()` to prevent `AttributeError` on `None` keyword
- [FIXED 2026-04-07] `src/citation_planner.py:334` — platform entity type `"social_asset"` → `"social_platform"` (matches graph_builder.py); `"social_platform"` added to `ENTITY_TYPES` in growth-graph/entity_graph.py
- [FIXED 2026-04-07] `src/wp_client.py:86` — `RequestException` silently swallowed → added `logger.warning` to bare `except RequestException` in `update_item_content` and `update_category_description`
