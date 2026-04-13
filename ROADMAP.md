# SEO Agent — 产品路线图

最后更新：2026-04-01

---

## 已完成

### 多站点支持（2026-04-01）
- `SiteContext` 隔离：每个站点独立的 DB、state file、credentials
- `prompt_config`：每站点在 `site.json` 里手动调整 AI prompt（target_audience / tone_style / extra_instructions 等）
- 跨站点污染修复：`content_brief_engine` + `openai_generator` 不再硬注入 sweetsworld 路径
- `page_type_strategies/*.py`：`or "confectionery"` 改为 `_get_profile().default_category`
- FAQ 模板按站点类型分叉：服务类站点（newcastlehub）得到业务导向问题，糖果类站点保留 halal/vegan/bulk 问题

---

## 待办

### P1 — FAQ 模板数据化（高优先）

**问题：** `page_type_strategies/*.py` 里的 FAQ 问题和答案模板是硬编码在 Python 里的数据，每次改措辞都要改代码。

**目标：** 把模板内容从代码里分离出去，放到配置文件中。

**设计方案：**

```
config/
  faq_templates/
    default.json          ← 所有站点通用 fallback
    product_site.json     ← 糖果/电商类站点默认
    service_site.json     ← 服务类站点默认

sites/
  sweetsworld/
    faq_templates.json    ← sweetsworld 专用覆盖（可选）
  newcastlehub/
    faq_templates.json    ← newcastlehub 专用覆盖（可选）
```

模板格式（支持 `{subject}` / `{cat}` / `{area}` 占位符）：
```json
{
  "faq_page": [
    {"question": "What is {subject}?", "answer": "..."},
    {"question": "How much does {subject} cost in {area}?", "answer": "..."}
  ],
  "landing_page": [...],
  "guide_page":   [...]
}
```

**实施步骤：**
1. 新增 `src/template_loader.py` — 加载逻辑：site 专用 → config/niche 默认 → hardcode fallback
2. 把 `faq_page.py`、`landing_page.py`、`occasion_page.py` 等的模板提取到 JSON 文件
3. 各策略文件改用 `template_loader.load_faq_templates(site_id, page_type)` 获取模板
4. 写 sweetsworld 和 newcastlehub 的初始 `faq_templates.json`
5. 删除策略文件里的硬编码字符串

**收益：**
- 非技术人员可以直接改 JSON 调整措辞
- 新站点只需增加一个 JSON 文件，不碰 Python
- 代码与内容彻底分离

---

### P2 — 剩余硬编码清理（中优先）

#### 2a — `seo_discovery.py` / `seo_planner.py` 的默认 site_description

| 文件 | 位置 | 问题 |
|------|------|------|
| `seo_discovery.py` | L16, L170 | `site_description` 默认值 = "sweetsworld.com.au, an Australian candy..." |
| `seo_planner.py` | L67 | 同上 |

修复：读取 `SiteProfile.brand_name` + `default_focus` 替代硬编码字符串。

---

#### 2b — `content_generator.py` 地理映射 & Newcastle 特例

**问题：**
- `SiteProfile.from_context()` L41–58 有硬编码语言代码 → 国家/地区/形容词映射表
- Newcastle 特例用 `if "newcastle" in audience_lower` 触发，硬编码了专用 FAQ 文案
- `_area_map`、`_locale_map` 只支持 AU/US/UK/NZ，新国家无法添加

```python
# 现状（L41-51）
_area_map   = {"AU": "Australia", "US": "United States", "UK": "United Kingdom", "NZ": "New Zealand"}
_locale_map = {"AU": "Australian", "US": "American", "UK": "British", "NZ": "New Zealand"}
if "newcastle" in audience_lower or "newcastle" in niche_lower:
    locale_adj = "Newcastle"
    area       = "Newcastle, NSW"
    faq_buy_q  = "Where can I find {focus} in Newcastle?"
    faq_buy_a  = "Search for trusted Newcastle businesses..."
```

**修复方案：**
- 把 `_area_map` / `_locale_map` 迁移到 `config/geo_mappings.json`
- Newcastle 特例迁移到 `sites/newcastlehub/site.json` 的 `locale_override` 字段
- `from_context()` 从 `site.json` 读 `locale_override`（如存在）直接用，不再特殊 if/else

**目标配置格式（site.json 新增）：**
```json
"locale_override": {
  "area_served": "Newcastle, NSW",
  "locale_adjective": "Newcastle",
  "faq_buy_question": "Where can I find {focus} in Newcastle?",
  "faq_buy_answer": "Search for trusted Newcastle businesses..."
}
```

---

#### 2c — `content_brief_engine.py` — anchor text & link_kind 关键词列表

**问题：**
- `_link_kind()` L135：商业意图关键词列表硬编码 `["bulk", "wholesale", "gift-box", "buy", "online"]`（零售导向）
- `_anchor_variants()` L144–180：按 link_kind / page_type 分支的 CTA 文字模板全部写死
- `_category_hint_candidates()` L183+：candy/chocolate/japanese/american 分支是 sweetsworld 专用

```python
# 现状 L135
if any(token in cleaned for token in ["bulk", "wholesale", "gift-box", "gift-boxes", "buy", "online"]):
    return "commercial"
```

**修复方案：**
- `_link_kind` 的商业意图关键词迁移到 `config/link_rules.json`（含 `commercial_tokens`、`product_depth` 等）
- `_anchor_variants` 的 CTA 模板迁移到各页面类型的 `config/page_templates/{type}.json`
- `_category_hint_candidates` 依赖 `_get_collection_urls()` 已部分修复，扫描逻辑改为读 collection_urls 键名，不再 hardcode "american"/"japanese" 等

---

#### 2d — `page_type_strategies/` 各策略文件的文案模板

以下 5 个文件的 `build_intro` / `build_sections` / `build_cta` 中存在零售/糖果专用文案模板，目前靠 `prompt_config.extra_instructions` 兜底，但 brief 本身仍有泄漏风险：

| 文件 | 硬编码内容示例 |
|------|---------------|
| `best_of_page.py` build_sections L80–95 | "For gifts: variety packs..."、"For dietary needs: filter by halal/vegan/allergen-free" |
| `best_of_page.py` build_sections L88 | "Flavour accuracy, consistent stock, clear ingredient labelling" |
| `city_landing_page.py` build_sections L75–90 | "Bulk packs and wholesale options"、"Wider range than physical stores" |
| `occasion_page.py` build_sections L65–72 | "Occasion candy decisions"、"Check heat sensitivity and packaging" |
| `occasion_page.py` build_faq_items L82 | "100–150 grams of mixed {cat} per person" — 纯糖果语言 |

**修复方案：** 按 P1（FAQ 模板数据化）的统一方案处理 — 将 sections 文案模板也迁移到 JSON，策略文件只做占位符替换。

---

#### 2e — `openai_generator.py` seasonal_terms 列表

```python
# L137 — 假节日列表全部来自英语零售节点，不适用服务类网站
seasonal_terms = ["valentine", "christmas", "easter", "halloween", "new year", "black friday", "boxing day"]
```

**修复方案：** 迁移到 `site.json` 的 `seasonal_terms` 字段，服务类站点可设置为空列表或商业节日。

---

**总修复优先级：**
1. `content_generator.py` Newcastle 特例 → `locale_override`（高，影响所有城市级站点）
2. `page_type_strategies/` 零售文案泄漏（高，直接影响 brief 质量）
3. `content_brief_engine.py` anchor/link_kind（中，影响内链锚文本）
4. `openai_generator.py` seasonal_terms（低，现有 extra_instructions 可兜底）
5. `seo_discovery.py` / `seo_planner.py` 默认 site_description（低，只影响日志）

---

### P3 — 多站点 prompt 版本管理（低优先）

**问题：** 修改 `site.json` 的 `prompt_config` 没有历史记录，不知道改了什么、改了几次。

**方案：** 在 `site.json` 里增加 `prompt_version` 字段，每次修改手动递增。发布时记录 prompt 版本号到 state file，方便对比不同版本下内容质量的变化。

---

### P4 — Prompt 测试工具（低优先）

**问题：** 改完 `prompt_config` 后要真正发布才能看效果，成本高。

**方案：** 新增 CLI 命令：
```bash
python -m run_mvp --site newcastlehub --dry-run-prompt --slug google-business-profile-newcastle
```
只生成 HTML，不发布到 WordPress，输出到 `/tmp/` 供预览。
