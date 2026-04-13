# SweetsWorld SEO Agent — 改进计划

Created: 2026-03-17
Updated: 2026-03-18
Status: 🟢 运行中 — 每天 10:30 自动发布 20 篇，已发布 15 篇，206 个 topics 待生成

---

## Phase A — HOLD 期间执行（不影响发布）

### A1: GSC 自动监控 + Telegram 通知 ✅
**优先级**: 🔴 最高
**复杂度**: medium
**目标**: 每天自动跑 pilot_gate，一旦 impressions > 0 立即推送 Telegram

- [x] `telegram_notify.py` — 新增 `notify_pilot_gate()` 函数，三种消息头样式
- [x] `pilot_gate.py` — 加 `--notify` flag，impression 首次出现时推送；输出原子写入
- [x] `scripts/run_daily_monitor.sh` — 调用 analytics + pilot_gate --notify
- [x] `scripts/install_monitor.sh` — launchd plist 每天 10:00 AEDT 触发，已安装激活

**验收标准**: launchd job 存在，`launchctl list | grep seo-monitor` 有输出，mock 测试推送成功

---

### A2: 内容质量检查（发布前 guard）✅
**优先级**: 🔴 高
**复杂度**: low
**目标**: 在 publish 前拦截字数不足、meta 过长的页面

- [x] `content_generator.py` — `validate_content_quality()` 扩展：按页面类型动态字数阈值（guide=800, landing=600, category=400），meta title/description 长度检查，schema JSON-LD 解析验证
- [x] `run_mvp.py` — publish 前调用质量检查，不通过写入 `quality_blocked` 状态
- [x] GSC query rowLimit `ranking_monitor.py` 从 5 → 50，每页展示 top 10 queries

**验收标准**: 生成一个字数 < 600 的 brief，`run_mvp.py` 拒绝发布并在 registry 写入 `blocking_reason`

---

## Phase B — GSC 出现信号后执行（扩量前）

### B1: Topic 语义去重 ✅
**优先级**: 🟡 中
**复杂度**: low
**目标**: 防止 `are-jolly-ranchers-halal` 和 `jolly-ranchers-halal-australia` 被当两个 topic

- [x] `topic_generator.py` — `_normalise_keyword()`：lowercase、去标点、去 stop words、token 排序
- [x] `_is_near_duplicate()` — SequenceMatcher ratio ≥ 0.85 判定为近重复，零新依赖
- [x] `_dedupe_topics()` 扩展为语义去重，写入前自动过滤

**验收标准**: `are jolly ranchers halal` 和 `jolly ranchers halal australia` 被判定为 near-duplicate，只保留一个

---

### B2: 双向内链检查 ✅
**优先级**: 🟡 中
**复杂度**: medium
**目标**: 每次发布新页面后，提示哪些已发布页面应该补一条内链指向新页面

- [x] `internal_link_engine.py` — `build_backlink_suggestions()` 检测 A→B 存在但 B→A 缺失的情况
- [x] `data/internal_links.json` — export 附加 `missing_backlinks` 字段，原子写入
- [x] `pilot_gate.py` markdown — 底部展示 "## Missing Backlinks" 区块

**验收标准**: 运行 `internal_link_engine.py`，输出包含 `missing_backlinks` 且格式正确

---

### B3: 发布回滚 ✅
**优先级**: 🟡 中
**复杂度**: low
**目标**: `run_mvp.py --slug <slug> --revert-to-draft` 把线上页面改回 draft

- [x] `wp_client.py` — `revert_to_draft(post_id)` 方法，同样走 retry 逻辑
- [x] `run_mvp.py` — `--revert-to-draft` flag，找 registry `published_post_id`，回滚后改 status 为 `approved`
- [x] `--yes` flag 跳过确认提示

**验收标准**: 对一个 dry_run 环境执行回滚，registry status 变回 `approved`，不影响其他记录

---

## Phase C — 架构 / 长期

### C1: tg_agent → subprocess 解耦 ✅
**优先级**: 🟢 低
**复杂度**: high（实际用 subprocess CLI 简化，无需 HTTP server）
**目标**: 消灭 `tg_agent/executor.py` 的直接 import

- [x] `sweetsworld-seo-agent/src/seo_cli.py` — CLI 桥接脚本（discover/plan/generate），JSON in/out
- [x] `tg_agent/executor.py` — 新增 `_seo_cli()` helper，`seo_discover`/`seo_plan`/`seo_create` 全部改走 subprocess
- [x] 智能模式保留：只传 topic 时，先 plan 取第一个建议，再调 generate

**验收标准**: `tg_agent` 不再 import `sweetsworld-seo-agent` 任何模块，全部走 HTTP

---

### C2: Registry 完整性校验 ✅
**优先级**: 🟢 低
**复杂度**: low
**目标**: 检测 WP 里被手动删除但 registry 仍标记 published 的孤儿记录

- [x] `run_mvp.py` — `--verify-registry` 遍历 published 记录，查不到则标记 `orphaned`
- [x] `pilot_gate.py` — `checks` 加 `no_orphaned_records`，blocking reason 包含孤儿数量

**验收标准**: mock WP 返回 404，`--verify-registry` 把该记录标记为 `orphaned`

---

## Decisions Log

| 决定 | 原因 | 排除的方案 |
|------|------|-----------|
| A1 用 launchd 而非 cron | 项目已有 launchd 基础设施（`scripts/run_daily_seo.sh`） | cron 需要额外配置 |
| A2 字数用 word_count 而非 char_count | 更符合 SEO 行业标准 | char_count 对中英文混排不准确 |
| B1 用 SequenceMatcher 而非外部库 | 零依赖，够用 | rapidfuzz 更准但增加依赖 |
| B2 只生成建议不自动补链 | MVP 阶段人工控制更安全 | 自动补链风险太高 |
| C1 排到 Phase C | 功能不受影响，解耦不产生新价值只减少风险 | 立即做但收益不明显 |

---

## 额外完成（超出原计划）

- **WP 重试机制** — `wp_client.py` `_request_with_retry()`，指数退避，覆盖 429/5xx
- **原子写入** — 9 个文件统一用 `.tmp` + `os.replace()`，防崩溃数据损坏
- **O(1) Registry 索引** — `run_mvp.py` 加载时构建 `_index` dict，查找从 O(n) 降至 O(1)
- **URL 集中管理** — `config.get_site_collection_urls()` 消除 5 个文件中的 sweetsworld.com.au 硬编码
- **Sitemap 重试** — `ranking_monitor.py` 独立 session + urllib3 Retry，避免 503 误报页面缺失

## Phase D — 2026-03-18 新增功能（已完成）✅

### D1: 产品 URL 健康检查 ✅
- [x] `src/url_health_check.py` — 检查所有 published WC 产品 URL，诊断 404/重定向/跳首页等问题
- [x] `--notify` flag — 发现问题自动推送 Telegram 报告
- [x] `scripts/install_url_health_check.sh` — launchd 每周二 09:00 自动运行
- [x] 首次全量检查：2599 个产品 URL，0 问题

### D2: 内容批量发布 ✅
- [x] 15 篇 drafted 页面全部 approved + published
- [x] `japanese-candy-australia` 修复产品选择器（加入 japan/kracie/meiji token）后发布
- [x] 所有 15 篇提交 Google Indexing API

### D3: 每日自动发布 20 篇 ✅
- [x] `.env` — `DAILY_LIMIT=20`，`PUBLISH_MODE=live`
- [x] `scripts/run_daily_seo.sh` — python bin 路径修正为系统 python3
- [x] launchd `com.sweetsworld.seo-agent.daily` — 每天 10:30 自动运行
- [x] 206 个 topics 已准备好，约 10 天发完

### D4: Topics 大扩充 ✅
- [x] 从 15 个扩充至 206 个，覆盖：
  - 季节（圣诞、万圣、复活节、情人节、母亲节、父亲节）
  - 场合（婚礼、生日、订婚、baby shower、毕业、谢师礼）
  - 国家（英、荷、德、土耳其、比利时、意大利、墨西哥、瑞典、加拿大、韩国）
  - 品牌（Haribo、Reese's、Skittles、M&Ms、Kit Kat、Lindt、Ferrero、Takis 等 35+）
  - 口味（草莓、西瓜、薄荷巧克力、焦糖、花生酱等 20 种）
  - 形态（棒棒糖、软糖、甘草糖、棉花糖、Rocky Road、棉花糖等）
  - 健康（Gluten Free、Dairy Free、无人工色素、无坚果、Keto、无明胶）
  - 购买意图（自选糖果、订阅盒子、盲盒、批发、企业礼品）
  - 历史经典（Allen's Red Frogs、Jaffas、Minties、Musk Sticks、Werther's 等）

---

## Phase E — 待办（GSC 数据来了之后）

### E1: WooCommerce 产品数据同步
**优先级**: 🟡 中
**目标**: 用 WooCommerce 2599 个 published 产品替换现有 1503 条旧 products.json
- [ ] `src/sync_woocommerce_products.py` — 分页拉取全量 WC published 产品，保存为 products.json 格式
- [ ] launchd 每周同步一次

### E2: GSC 数据驱动 Topic 优化
**优先级**: 🟡 中
**目标**: GSC 有数据后，根据实际 impressions/clicks 补充高潜力 topics
- [ ] 分析哪类页面 CTR 最高 → 多发同类
- [ ] 用 `seo_discovery.py` 的 GSC 模式自动发现新关键词
- [ ] 低表现页面考虑内容优化或下架

### E3: 内容质量升级（AI 生成）
**优先级**: ⏰ 推迟至 2026-05-01 后评估
**决定日期**: 2026-03-18
**触发条件**（满足其中一条再做）:
- GSC 有 impressions 但 CTR < 1%（内容吸引力不足）
- 高价值 topic 排名卡在第 5–10 名无法突破
- 竞争对手同关键词内容质量明显更好

**方案**（届时选一个）:
- 接入 `anthropic` SDK（已有基础设施，成本低）
- 安装 `openai` 包（$0.02–0.05/页，约 $15–30/月）
- 只对 priority=1 的 topic 用 AI，其余继续模板

⚠️ **提醒**：4-6 周后（约 2026-05-01）查看 GSC 数据后再决定是否启动

### E4: Topics 持续补充
**优先级**: 🟢 低
**目标**: 206 个 topics 发完后继续补充
- [ ] 从新产品数据中挖掘更多品牌 topic
- [ ] 根据 GSC 搜索词发现长尾 topic
- [ ] 季节性 topic 提前 6 周入队（如圣诞节 topic 11 月初开始发）

---

## 额外完成（超出原计划）

- **WP 重试机制** — `wp_client.py` `_request_with_retry()`，指数退避，覆盖 429/5xx
- **原子写入** — 9 个文件统一用 `.tmp` + `os.replace()`，防崩溃数据损坏
- **O(1) Registry 索引** — `run_mvp.py` 加载时构建 `_index` dict，查找从 O(n) 降至 O(1)
- **URL 集中管理** — `config.get_site_collection_urls()` 消除 5 个文件中的 sweetsworld.com.au 硬编码
- **Sitemap 重试** — `ranking_monitor.py` 独立 session + urllib3 Retry，避免 503 误报页面缺失
- **产品选择器修复** — japanese token 扩展支持 japan/kracie/meiji/pocky
- **Registry 去重** — 删除 american-candy-australia 重复的 category_page 记录

## Review（完成：2026-03-18）

- 系统已从 HOLD 转为全自动运行，每天 10:30 发 20 篇
- 206 个 topics 覆盖品牌、季节、场合、国家、口味等多个维度
- URL 健康检查每周二自动运行，2599 个产品 URL 当前全部健康
- 15 篇页面已发布并提交 Google Indexing API
- 下一个关键节点：约 2 周后 GSC 开始出现 impressions → 触发 Telegram 通知
