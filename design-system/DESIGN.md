# SweetsWorld Design System
# Single Source of Truth for AI-generated content on sweetsworld.com.au
#
# AGENT USAGE: This file is injected into every Claude/GPT call as part of the
# system prompt. Read the "Agent Prompt Guide" section at the bottom first.
#
# Version: 1.0 — 2026-04-07
# Skin: loaded from skins/default.md (override with seasonal skins per month)

---

## 1. Brand Intent

**Site**: sweetsworld.com.au — Australia's online candy and confectionery store.
**Mission**: Make buying lollies, chocolate, and sweet treats online easy, fun, and irresistible.
**Positioning**: Friendly specialty retailer, not a discount warehouse. Quality + variety + joy.
**Voice**: Fun, enthusiastic, knowledgeable. Australian English throughout (colour, flavour, organise).
**Target reader**: Australian adults buying for themselves, as gifts, or for events (parties, offices, schools).

Design must feel: **playful but trustworthy**, **colourful but clean**, **enthusiastic but not spammy**.

---

## 2. Visual Atmosphere

- Light, airy backgrounds — white cards on a very pale blue-grey page wash.
- Candy colours used as accents only, not as large blocks of background.
- Product photography is hero — text and UI chrome should never compete with product images.
- Generous whitespace inside cards. Content should breathe.
- Rounded corners on cards and buttons (8px radius minimum).
- Avoid dark or heavy design patterns. The mood is a bright lolly shop, not a tech dashboard.

---

## 3. Color Roles

All colours must reference these semantic roles. Never introduce a colour not defined here.
Actual hex values live in `skins/default.md` and may be overridden by seasonal skins.

| Role Name | Default Hex | Usage |
|-----------|-------------|-------|
| `color_primary` | `#6bb6d9` | Primary interactive colour: links, button borders, section accents |
| `color_primary_dark` | `#7aa9c2` | Hover states, active borders, secondary headings |
| `color_text_primary` | `#3b4b5c` | All body text, H2, H3 |
| `color_text_secondary` | `#4d5d6c` | Subheadings, card titles, intro lines |
| `color_text_muted` | `#666666` | Captions, metadata, timestamps, placeholder text |
| `color_cta_accent` | `#ff6b6b` | CTA buttons, urgency highlights ("Shop Now", "Buy Today") |
| `color_card_bg` | `#ffffff` | Product card backgrounds, info box backgrounds |
| `color_card_border` | `#e7edf3` | Card borders, dividers, table borders |
| `color_gallery_bg` | `#f8fbfd` | Gallery section backgrounds, alternating row tints |
| `color_gallery_border` | `#e5eef5` | Gallery section borders |
| `color_cta_bg` | `#f8f9fa` | CTA block background tint |

**Rules:**
- Text on white must use `color_text_primary` or `color_text_secondary`. Never `#000` pure black.
- `color_cta_accent` is for CTAs only. Do not use it for decorative elements.
- Do not invent new hex values in generated HTML. Use only the roles above.
- If a seasonal skin is active, the hex values will differ — the role names stay constant.

---

## 4. Typography

### Font Stack
```
Primary: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
(Flatsome theme controls the actual font family — do not override in generated HTML)
```

### Size Scale (rem)
| Element | Size | Weight | Line Height | Notes |
|---------|------|--------|-------------|-------|
| H1 | 2.0rem | 700 | 1.2 | Page title, one per page |
| H2 | 1.5rem | 700 | 1.3 | Section headings |
| H3 | 1.2rem | 600 | 1.4 | Card titles, sub-sections |
| H4 | 1.05rem | 600 | 1.4 | Minor headings, FAQ questions |
| Body | 1.0rem | 400 | 1.7 | All paragraph text |
| Small / Caption | 0.875rem | 400 | 1.5 | Metadata, tags, labels |
| CTA Button | 1.0rem | 700 | 1 | Uppercase, letter-spacing: 0.05em |

### Rules
- H1 appears exactly once per page, in the page title area (Flatsome controls this).
- AI-generated content starts from H2. Do not generate H1 tags inside slot content.
- Maximum 3 heading levels in a single slot (H2 → H3 → H4).
- Line length target: 60–80 characters. Use max-width on content blocks.
- Do not use `<b>` or `<i>` — use `<strong>` and `<em>`.

---

## 5. Spacing and Layout

### Spacing Scale
| Token | Value | Use |
|-------|-------|-----|
| `space_xs` | 4px | Inner element padding (badge, tag) |
| `space_sm` | 8px | Icon margins, tight element gaps |
| `space_md` | 16px | Standard paragraph gap, card inner padding |
| `space_lg` | 24px | Between card and next element |
| `space_xl` | 40px | Between page sections |
| `space_2xl` | 64px | Top/bottom section padding |

### Layout Principles
- Page content max-width: 1100px, centred.
- Product grids: 3 columns desktop / 2 columns tablet / 1 column mobile.
- Card inner padding: `space_md` (16px) all sides.
- Section gap (between AI_SLOT blocks): `space_xl` (40px).
- CTA block: full-width tinted background, `space_2xl` top/bottom padding, centred content.

---

## 6. Component Rules

### 6.1 Product Card (`AI_SLOT:PRODUCTS`)

```html
<!-- Canonical product card structure -->
<div class="sweets-product-card" style="
  background: {{color_card_bg}};
  border: 1px solid {{color_card_border}};
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
">
  <img src="{{product_image_url}}" alt="{{product_name}}" loading="lazy"
       style="width:100%; aspect-ratio:1; object-fit:cover; border-radius:6px;">
  <h3 style="color:{{color_text_secondary}}; font-size:1.05rem; margin:0;">{{product_name}}</h3>
  <p style="color:{{color_text_muted}}; font-size:0.875rem; margin:0;">{{product_short_desc}}</p>
  <a href="{{product_url}}" style="
    color: {{color_primary}};
    font-weight: 600;
    text-decoration: none;
    font-size: 0.9rem;
  ">Shop Now →</a>
</div>
```

**Product Card Rules:**
- Always include `loading="lazy"` on product images.
- Product name is H3, never H2 (H2 is for section headings).
- Minimum 3 products, maximum 12 products per PRODUCTS slot.
- Grid layout: use CSS Grid or flexbox wrap, never HTML table.
- Each card must link to the product URL — never link to a category page from a product card.
- Do not add pricing to cards (prices change frequently; linking to the product page is sufficient).

### 6.2 CTA Box (`AI_SLOT:CTA`)

```html
<!-- Canonical CTA block structure -->
<div class="sweets-cta-block" style="
  background: {{color_cta_bg}};
  border-radius: 8px;
  padding: 40px 24px;
  text-align: center;
">
  <h2 style="color:{{color_text_primary}}; margin-bottom:12px;">{{cta_heading}}</h2>
  <p style="color:{{color_text_secondary}}; margin-bottom:24px; max-width:560px; margin-left:auto; margin-right:auto;">{{cta_body}}</p>
  <a href="{{cta_url}}" style="
    background: {{color_cta_accent}};
    color: #ffffff;
    padding: 14px 32px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 1rem;
    text-decoration: none;
    letter-spacing: 0.05em;
    display: inline-block;
  ">{{cta_button_text}}</a>
</div>
```

**CTA Rules:**
- CTA heading: 6–12 words, action-oriented (e.g. "Ready to Fill Your Lolly Jar?").
- CTA body: 1–2 sentences max, 20–40 words. Focus on benefit, not features.
- Button text: 2–5 words. Start with a verb (Shop, Browse, Explore, Order).
- Button colour is always `color_cta_accent`. Never use `color_primary` for CTA buttons.
- CTA block must contain exactly one `<a>` link. Do not add secondary links inside CTA.
- Link must point to a sweetsworld.com.au URL (collection page or product page).

### 6.3 FAQ Block (`AI_SLOT:FAQ`)

```html
<!-- Canonical FAQ structure (schema-eligible) -->
<div class="sweets-faq-block">
  <h2 style="color:{{color_text_primary}};">Frequently Asked Questions</h2>
  <div class="sweets-faq-item">
    <h4 style="color:{{color_text_secondary}}; margin-bottom:8px;">{{question}}</h4>
    <p style="color:{{color_text_primary}}; margin:0;">{{answer}}</p>
  </div>
  <!-- repeat sweets-faq-item for each Q&A -->
</div>
```

**FAQ Rules:**
- Minimum 3 questions, maximum 8 questions per FAQ slot.
- Questions use H4 (not H3 — H3 is for cards and sub-sections).
- Answers: 40–120 words. Concrete, helpful, not sales-y.
- FAQ heading is always "Frequently Asked Questions" (H2). Do not create a custom heading.
- The entire FAQ block must be structured to support FAQPage JSON-LD injection (handled separately by `AI_SLOT:SCHEMA`).

### 6.4 Product Gallery (`AI_SLOT:PRODUCTS` variant for category/landing pages)

- Use a 3-column CSS grid on desktop, 2-column on tablet, 1-column on mobile.
- Gallery background: `color_gallery_bg` with `color_gallery_border` around the section.
- Do not add individual card shadows — the card border is the visual boundary.
- Gallery section heading is H2 (e.g. "Featured {{page_topic}} Products").

---

## 7. Page Composition Rules

### Slot Order by Page Type

| Page Type | Required Slot Order |
|-----------|---------------------|
| `landing_page` | INTRO → PRODUCTS → FAQ (optional) → CTA → SCHEMA |
| `category_page` | INTRO → PRODUCTS (optional) → SCHEMA |
| `guide_page` | INTRO → [body content] → FAQ → CTA (optional) → SCHEMA |
| `best_of_page` | INTRO → PRODUCTS → FAQ → CTA → SCHEMA |
| `occasion_page` | INTRO → PRODUCTS → FAQ → CTA → SCHEMA |
| `faq_page` | INTRO (optional) → FAQ → SCHEMA |
| `comparison_page` | INTRO → COMPARISON_TABLE → FAQ (optional) → SCHEMA |
| `city_landing_page` | INTRO → LOCAL_SIGNAL → PRODUCTS (optional) → FAQ → CTA → SCHEMA |

**Layout Rules:**
- INTRO slot is always first, SCHEMA is always last.
- Never place CTA before PRODUCTS — users need context before conversion ask.
- guide_page body content (between INTRO and FAQ) may use H2/H3 freely; aim for 3–5 sub-sections.
- city_landing_page LOCAL_SIGNAL must appear before PRODUCTS to establish local relevance.

---

## 8. Content Slot Rules

Rules for each AI_SLOT in terms of visual/design constraints (logic rules live in `slot_schema.yaml`).

### AI_SLOT:INTRO
- One `<p>` tag only (no headings inside INTRO).
- 80–250 words. One paragraph.
- Must contain the primary keyword naturally in the first 2 sentences.
- No bullet points or lists in INTRO. Prose only.
- Colour: `color_text_primary`. No inline colour styling on INTRO text.

### AI_SLOT:PRODUCTS
- Always render as CSS Grid (3 cols), not as a flat list.
- Each product card follows the Product Card component spec (section 6.1).
- Section heading (H2) above the grid: "{{page_topic}} to Buy Online in Australia" or similar.
- Minimum 3 products, maximum 12 products. 4–8 is ideal.

### AI_SLOT:FAQ
- See FAQ Block spec (section 6.3).
- Must not contain any promotional language or links inside answers.
- Answers are informational only — links go in INTRO or CTA.

### AI_SLOT:CTA
- See CTA Box spec (section 6.2).
- CTA is the only place `color_cta_accent` appears.
- CTA appears once per page. Do not add a second CTA block.

### AI_SLOT:LOCAL_SIGNAL (city_landing_page only)
- One `<p>` tag, 50–120 words.
- Must mention the city name at least twice.
- Should reference a local context (events, delivery, local businesses).
- Uses `color_text_primary` text. No special visual treatment.

### AI_SLOT:COMPARISON_TABLE
- Use `<table>` with `border-collapse: collapse`.
- Header row: `color_gallery_bg` background, `color_text_secondary` text.
- Alternating rows: white / `color_gallery_bg`.
- Border: `1px solid {{color_card_border}}`.
- Minimum 3 items compared, minimum 3 attributes per item.

### AI_SLOT:SCHEMA
- Contains only a `<script type="application/ld+json">...</script>` block.
- No visible HTML. Zero visual output.
- Do not generate this slot manually — it is filled by `consistency_scan.py` and `wp_ai_ops`.

---

## 9. Responsive Rules

### Breakpoints
| Name | Width | Behaviour |
|------|-------|-----------|
| Mobile | < 768px | 1 column; font sizes drop 10–15%; padding halved |
| Tablet | 768–1024px | 2 columns; standard font sizes |
| Desktop | > 1024px | 3 columns; full layout |

### Mobile Rules
- Product grid: 1 column on mobile (`grid-template-columns: 1fr`).
- H2 font size: 1.3rem on mobile (down from 1.5rem).
- CTA block padding: 24px on mobile (down from 40px).
- Body line-height unchanged (1.7) — readability priority on small screens.
- No horizontal scroll — all content must fit within viewport width.
- CTA button: full width (`width: 100%`) on mobile.

### Implementation Note
- Flatsome handles global responsive behaviour via theme.
- AI-generated HTML in slots should use inline `style` tags with media-query-free defaults (mobile-first base styles).
- For responsive grid: use `flexbox wrap` as fallback when CSS Grid is not supported.

---

## 10. Do's and Don'ts

### DO
- Use Australian English spelling in all generated text (colour, flavour, lolly, confectionery).
- Use `loading="lazy"` on all `<img>` tags.
- Link products to their product page URL (`/product/{{slug}}/`).
- Start CTA button text with an action verb.
- Keep INTRO as a single prose paragraph.
- Use `color_text_primary` for all body text.
- Use semantic HTML (`<strong>`, `<em>`, `<ul>`, `<ol>`).

### DON'T
- Do not introduce hex colours not defined in the Color Roles table.
- Do not generate `<h1>` tags inside slot content (Flatsome controls H1).
- Do not use `<table>` for product grids (use CSS Grid or flexbox).
- Do not add inline `font-family` styles (Flatsome controls fonts globally).
- Do not use American English ("candy bar" is fine; "color", "organize" are not).
- Do not add `target="_blank"` to internal links.
- Do not place pricing text in product cards (prices change; link to product page instead).
- Do not use `<center>` tag (use CSS `text-align: center`).
- Do not generate `<style>` blocks in slot content — inline styles only.
- Do not link outside sweetsworld.com.au in PRODUCTS or CTA slots.
- Do not write more than 12 products in a PRODUCTS slot — it overwhelms the reader.

---

## 11. Agent Prompt Guide

> This section is the injected system prefix for every Claude/GPT call when generating
> slot content. Include this verbatim in the system prompt before the task description.

---

**SYSTEM: SweetsWorld Design Constraints**

You are generating HTML content for sweetsworld.com.au, an Australian candy and confectionery ecommerce store.

**Brand voice**: Fun, friendly, enthusiastic. Australian English (colour, flavour, lolly, confectionery, organise).

**Visual rules you must follow:**
1. Use these CSS colour roles in all inline styles — never invent new hex values:
   - Body text: `#3b4b5c` (primary) or `#4d5d6c` (secondary)
   - Muted/caption text: `#666666`
   - Card backgrounds: `#ffffff`; Card borders: `#e7edf3`
   - Gallery backgrounds: `#f8fbfd`; Gallery borders: `#e5eef5`
   - CTA accent (buttons only): `#ff6b6b`
   - CTA section background: `#f8f9fa`
   - Interactive/link colour: `#6bb6d9`

2. Never generate `<h1>` tags. Start from `<h2>`.

3. Product cards: use flexbox/grid, include `loading="lazy"` on images, link to product URL.

4. CTA button: always `background: #ff6b6b; color: #ffffff`. Start button text with an action verb.

5. FAQ: H4 for questions, `<p>` for answers. Min 3, max 8 Q&As.

6. INTRO slot: single `<p>` tag, 80–250 words, no headings, no lists.

7. Do not add `font-family`, `<style>` blocks, or `target="_blank"` on internal links.

8. Australian English throughout. No US spellings.

**Content goal**: Practical buying guidance. Readers want to know what to buy, why it's good, and where to buy it. Every page ends with a clear path to purchase.

---

---

## 12. Implementation Bridge — 设计规范如何落地

> 说明每一层设计决策通过什么路径实现，以及谁负责操作。

### 实现路径分层

| 设计层 | 改什么 | 实现方式 | 操作者 |
|--------|--------|----------|--------|
| **Flatsome Theme Options**（全局颜色/字体/按钮） | `wp_options` 表写入 | PHP 脚本 / WP CLI | 可自动化脚本 |
| **Custom CSS**（全局追加样式） | WP `custom_css` post | WP REST API `POST /wp-json/wp/v2/custom_css` | 可自动化 |
| **内容区 HTML 样式**（AI 生成内容） | skin_tokens → content_generator.py | 读取 `skins/default.md` 替换硬编码颜色 | 代码自动化 ✅ |
| **Header / Footer 结构** | Flatsome Header/Footer builder 布局 | 只能 WP Admin 手工操作 | 手工 |
| **UX Builder 页面布局**（首页等） | post_meta JSON | 只能 WP Admin 手工操作（REST API 写入会破坏结构）| 手工 |
| **Widget areas** | `wp_options` 序列化数据 | 只能 WP Admin 手工操作 | 手工 |

### 可自动化路径的具体实现

#### 1. Flatsome Theme Options（wp_options 写入）
```python
# 通过 sweetsworld 服务器 PHP bridge 写入
# 键名示例（Flatsome 存储格式）：
wp_options["flatsome_options"] = {
    "primary_color": "#6bb6d9",
    "secondary_color": "#ff6b6b",
    "body_font_size": "16px",
    ...
}
```
> ⚠️ 改 Theme Options 影响全站，必须先快照，建议 dry-run 模式验证。

#### 2. Custom CSS（REST API）
```python
# PATCH /wp-json/wp/v2/custom_css/<id>
# 用于追加 sweetsworld 品牌专属 CSS，不覆盖 Flatsome 自带样式
payload = {
    "content": ".seo-product-card { border-radius: 12px; }"
}
```

#### 3. 内容区 skin_tokens（代码层）
```python
# content_generator.py 加载逻辑（待实现）
skin = load_skin("sites/sweetsworld/design-system/skins/default.md")
PRIMARY_COLOR = skin["colors"]["primary"]  # #6bb6d9
```

### Seasonal Skin 覆盖流程
```
skins/default.md        ← 基础 token
      ↓ override
skins/christmas.md      ← 圣诞季：primary=#c0392b, cta_accent=#27ae60
      ↓
content_generator.py    ← 读取当前激活 skin
      ↓
AI 生成的 HTML 内容      ← 自动使用季节配色
```

激活方式（建议加入 site.json）：
```json
{
  "active_skin": "christmas",
  "skin_valid_from": "2026-12-01",
  "skin_valid_until": "2026-12-31"
}
```

### 多站点复用
每个站点建自己的 `design-system/` 目录，覆盖需要差异化的部分：
```
agents/sweetsworld-seo-agent/design-system/   ← sweetsworld 专属
agents/newcastlehub-seo-agent/design-system/  ← newcastlehub 专属（继承结构，覆盖颜色）
```

---

*End of DESIGN.md — Version 1.1 — sweetsworld.com.au*
