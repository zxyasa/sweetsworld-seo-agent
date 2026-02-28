# Telegram Bot 智能 SEO 文章创建指南

## 🎯 智能创建流程（推荐）

现在你可以用**自然语言**在 Telegram 里创建 SEO 文章，无需手动填写参数！

---

## 📱 使用方法

### 方式 1：两步式（推荐）- 先看建议再选择

#### 第 1 步：生成建议
在 Telegram 里发送：

```
"帮我规划一篇关于 Australian Chocolate 的文章"
"我想写关于 vegan candy 的内容，给我建议"
"生成 sugar-free lollies 的文章参数"
```

Bot 会返回 **3 个建议**：

```
📋 SEO 文章建议（3个选项）

选项 1：
📝 标题: Ultimate Guide to Australian Chocolate 2026
🔗 Slug: australian-chocolate-guide-2026
🔑 关键词: australian chocolate
📁 分类: Chocolate

选项 2：
📝 标题: Best Australian Chocolate Brands 2026
🔗 Slug: best-australian-chocolate-brands
🔑 关键词: australian chocolate brands
📁 分类: Reviews

选项 3：
📝 标题: Where to Buy Premium Australian Chocolate
🔗 Slug: buy-australian-chocolate-guide
🔑 关键词: buy australian chocolate
📁 分类: Shopping Guide

💡 使用方法：
回复数字 1、2 或 3 来选择一个建议，或者说"全部创建"来创建所有3篇文章。
```

#### 第 2 步：选择并创建
回复：

```
"用选项 1 创建"
"创建第 2 个"
"全部创建"  （会创建所有3篇）
```

Bot 会自动创建文章并发布到 WordPress！

---

### 方式 2：一步式 - 直接创建

如果你想快速创建，可以直接说：

```
"创建一篇关于 Australian Chocolate 的文章"
"写一篇 vegan candy 的 SEO 文章"
```

Bot 会：
1. 自动用 OpenAI 生成最佳参数
2. 直接创建文章（使用第一个建议）
3. 返回文章链接

---

## 🤖 支持的 Actions

| Action | 功能 | 示例 |
|--------|------|------|
| `seo_plan` | 智能规划文章参数（3个建议） | "规划关于巧克力的文章" |
| `seo_create` | 创建单篇文章（支持智能模式） | "创建关于糖果的文章" |
| `seo_batch` | 批量生成 topics.csv 中的文章 | "批量生成所有文章" |
| `seo_status` | 查看配置状态 | "SEO 状态" |
| `seo_logs` | 查看生成日志 | "看看日志" |

---

## 💡 实际使用示例

### 示例 1：探索性写作

```
你: "我想写关于健康糖果的内容，给我一些想法"

Bot 规划:
  1. seo_plan (topic: "healthy candy")

Bot 返回:
📋 SEO 文章建议（3个选项）

选项 1：
📝 标题: Healthy Candy Alternatives Guide 2026
🔗 Slug: healthy-candy-alternatives-australia
🔑 关键词: healthy candy australia
📁 分类: Healthy Options

选项 2：
📝 标题: Best Sugar-Free Candy Brands in Australia
🔗 Slug: sugar-free-candy-brands-australia
🔑 关键词: sugar free candy australia
📁 分类: Reviews

选项 3：
📝 标题: Natural Candy: Complete Buyer's Guide
🔗 Slug: natural-candy-buyers-guide
🔑 关键词: natural candy
📁 分类: Shopping Guide

你: "第 2 个看起来不错，创建它"

Bot 执行:
  1. seo_create (选项 2 的参数)

Bot 返回:
✅ SEO 文章已创建！
📝 标题: Best Sugar-Free Candy Brands in Australia
🔗 链接: https://sweetsworld.com.au/sugar-free-candy-brands-australia
📊 模式: AI-powered
📏 字数: 3245 字符
```

---

### 示例 2：快速创建

```
你: "快速创建一篇关于巧克力礼盒的文章"

Bot 规划:
  1. seo_create (topic: "chocolate gift boxes")

Bot 返回:
✅ SEO 文章已创建！
📝 标题: Chocolate Gift Boxes Australia: Complete Guide 2026
🔗 链接: https://sweetsworld.com.au/chocolate-gift-boxes-australia-guide
📊 模式: AI-powered with GSC data
📏 字数: 2987 字符
```

---

### 示例 3：批量创建

```
你: "批量生成所有待处理的文章"

Bot 规划:
  1. seo_batch

Bot 执行批量生成脚本...

Bot 返回:
🚀 SEO Automation Agent MVP - Starting...

✅ Configuration loaded
   WordPress: https://sweetsworld.com.au
   Username: zxyasa

✅ WordPress connection successful
✅ OpenAI enabled (model: gpt-4o)
✅ Google Search Console enabled

📋 Found 2 topics to process

[1/2] Processing: Wholesale Candy Australia: Supplier Guide (2026)
  📊 Found 8 related keywords from GSC
  ✅ Generated HTML content (3421 characters, AI-powered)
  ✅ Created draft: https://sweetsworld.com.au/?p=12345

[2/2] Processing: Sour Lollies Buying Guide: Flavours, Brands & Bulk
  📊 Found 12 related keywords from GSC
  ✅ Generated HTML content (2998 characters, AI-powered)
  ✅ Created draft: https://sweetsworld.com.au/?p=12346

✅ Done. Created drafts: 2/2
```

---

## 🔄 工作流程图

```
用户说话题
    ↓
Bot 调用 seo_plan
    ↓
OpenAI 生成 3 个建议
    ↓
返回给用户选择
    ↓
用户选择其中一个
    ↓
Bot 调用 seo_create
    ↓
创建文章并发布
    ↓
返回文章链接
```

---

## ⚙️ 技术细节

### seo_plan Action

**参数：**
- `topic` (必需) - 话题描述，例如 "Australian Chocolate"

**返回：**
- 3 个 SEO 文章建议，每个包含：
  - title - 标题
  - slug - URL slug
  - primary_keyword - 主关键词
  - category_hint - 分类提示

**OpenAI Prompt 策略：**
- 针对澳大利亚市场
- 包含年份 2026
- 3 个不同角度（购买指南、品牌对比、健康替代等）
- SEO 友好的标题和 slug

---

### seo_create Action（智能模式）

**两种模式：**

1. **智能模式** - 只提供 `topic`
   ```python
   params = {"topic": "Australian Chocolate"}
   ```
   自动调用 OpenAI 生成参数，使用第一个建议

2. **手动模式** - 提供完整参数
   ```python
   params = {
       "title": "...",
       "slug": "...",
       "primary_keyword": "...",
       "category_hint": "..."
   }
   ```

**OpenAI + GSC 集成：**
- `use_ai=True` - 使用 GPT-4o 生成文章内容
- `use_gsc=True` - 从 Search Console 获取相关关键词

---

## 📊 vs 传统方式对比

| 特性 | 传统方式 | 智能方式 |
|------|---------|---------|
| **输入** | 手动填写 title, slug, keyword, category | 只说话题 "Australian Chocolate" |
| **参数生成** | 人工思考 | OpenAI 自动生成 3 个建议 |
| **选择** | 无选择 | 3 个建议可选 |
| **用时** | 5-10 分钟 | 30 秒 |
| **错误率** | 人工输入易错 | OpenAI 生成准确 |

---

## 🎨 自定义建议数量

如果你想要更多或更少的建议，可以修改 `seo_planner.py`：

```python
# 默认返回 3 个建议
return suggestions[:3]

# 改为 5 个建议
return suggestions[:5]
```

---

## 🚨 注意事项

1. **确认机制**
   - `seo_plan` **无需确认**（只是生成建议）
   - `seo_create` **需要确认**（会实际创建文章）

2. **OpenAI API 配额**
   - `seo_plan` 每次调用消耗约 500-1000 tokens
   - `seo_create` (智能模式) 额外消耗 500-1000 tokens 用于参数生成
   - `seo_create` (AI 生成文章) 消耗约 2000-3000 tokens

3. **话题描述建议**
   - 简洁明了：❌ "我想写一篇很长的关于..."  ✅ "Australian Chocolate"
   - 具体清晰：❌ "糖果"  ✅ "vegan candy for kids"
   - 英文优先：✅ "chocolate gifts"  ⚠️ "巧克力礼物"（也可以，但英文效果更好）

---

## 🛠️ 故障排除

### 问题 1：seo_plan 返回错误

**可能原因：**
- OpenAI API 密钥未配置
- OpenAI API 配额不足

**解决方法：**
```bash
# 检查配置
cd ~/agents/sweetsworld-seo-agent
cat .env | grep OPENAI
```

### 问题 2：建议质量不好

**优化方法：**
- 提供更具体的话题描述
- 在 `seo_planner.py` 中调整 prompt
- 尝试不同的 OpenAI model（默认 gpt-4o）

### 问题 3：创建文章时找不到参数

**解决方法：**
- 确保先调用 `seo_plan` 生成建议
- 或者在 `seo_create` 时提供完整参数
- 或者使用智能模式：只提供 topic

---

## 🎯 最佳实践

1. **探索式写作**
   - 先用 `seo_plan` 看建议
   - 选择最合适的角度
   - 再用 `seo_create` 创建

2. **快速创作**
   - 直接说："创建关于 X 的文章"
   - Bot 自动用最佳参数创建

3. **批量创建**
   - 先手动添加 topics 到 `topics.csv`
   - 用 `seo_batch` 批量生成

---

## 📈 使用统计

你可以在 Telegram 里说：

```
"SEO agent 状态"
```

查看：
- 已创建文章数量
- topics.csv 待处理数量
- 配置状态

---

## 🚀 快速开始

1. 在 Telegram 里试试：
   ```
   "帮我规划一篇关于 vegan candy 的文章"
   ```

2. 选择一个建议：
   ```
   "用第 1 个创建"
   ```

3. 搞定！🎉

---

## 💡 提示

- 话题可以是英文或中文，但英文效果更好（针对澳大利亚市场）
- 建议描述越具体，生成的参数越精准
- 可以先用 `seo_plan` 探索不同角度，再决定创建哪个
- `seo_batch` 适合批量创建已规划好的文章

Happy SEO Writing! 📝✨
