# Page Type: landing_page
# Design and composition rules specific to the landing_page type.
# These rules supplement DESIGN.md and are injected alongside it when generating landing_page content.
#
# page_type value in topics.csv: "landing_page"
# WP category: candy-types
# Typical intent: Keyword-targeted informational + transactional hybrid (e.g. "American Candy Australia")
#
# Last updated: 2026-04-07

## Purpose and SEO Intent

Landing pages target high-volume, category-level keywords with buying intent.
They bridge informational (what is X) and transactional (buy X here) in a single page.
Example topics: "American Candy Australia", "Bulk Lollies", "Sour Candy".

**Primary conversion goal**: Get the reader to click through to a collection or product page.
**Secondary goal**: Establish topical authority for the keyword cluster.

---

## Slot Order (mandatory)

```
1. <!-- AI_SLOT:INTRO -->
2. <!-- AI_SLOT:PRODUCTS -->
3. <!-- AI_SLOT:FAQ -->          ← optional but strongly recommended (adds dwell time)
4. <!-- AI_SLOT:CTA -->
5. <!-- AI_SLOT:SCHEMA -->
```

Do not reorder slots. SCHEMA is always last and is filled by `consistency_scan.py`, not the content generator.

---

## INTRO Slot — landing_page specific rules

- **First sentence** must include the primary keyword naturally.
- **Frame**: What this type of candy/lolly is + why Australians love it.
- **Tone**: Enthusiastic discovery. Reader is learning about something fun, not reading a product spec.
- **Forbidden openers**: "Are you looking for...", "In this article...", "Welcome to..."
- **Target length**: 100–180 words (towards the shorter end — PRODUCTS section carries the page).
- **Must include**: At least one reference to sweetsworld.com.au as the shopping destination.

Example first sentence pattern:
> "[Primary keyword] [brief descriptor] — [why it's great for the reader], and SweetsWorld has one of Australia's widest selections."

---

## PRODUCTS Slot — landing_page specific rules

- **Count**: 6–12 products (landing pages are discovery-focused, wider product range).
- **Selection criteria**: Products most relevant to the primary keyword and buyer intent.
  - Prioritise in-stock items.
  - Mix: well-known items + interesting/unexpected finds.
  - Do not list products from unrelated categories.
- **Section heading (H2)**: "Shop [Primary Keyword] at SweetsWorld" or "Top [Keyword] to Buy Online".
- **Grid**: 3 columns desktop (CSS Grid), 2 tablet, 1 mobile.

---

## FAQ Slot — landing_page specific rules

- **Recommended**: Yes. FAQ boosts AIO citation potential and handles long-tail queries.
- **Count**: 4–6 questions.
- **Question types to include**:
  - What is [keyword]? (definitional)
  - Where can I buy [keyword] in Australia?
  - Is [keyword] available for delivery to [city]?
  - What's the best [keyword] for [use case]?
- **Answers**: 40–80 words each. Direct and helpful.
- **Do not** include FAQ if the topic is self-explanatory and the page is short — use the slot for more product focus instead.

---

## CTA Slot — landing_page specific rules

- **CTA heading pattern**: "[Verb] the Best [Keyword] in Australia"
  - Examples: "Shop the Best American Candy in Australia", "Explore Our Bulk Lolly Range"
- **CTA body**: 1 sentence. Reference free/flat-rate shipping as a benefit.
  - Example: "Order online with Australia-wide delivery — flat rate shipping on all orders."
- **CTA button text options**: "Shop Now", "Browse the Range", "Explore [Keyword]"
- **Link target**: Primary collection page for this keyword (e.g. `/candy/american-candy/`).

---

## Visual Weight Distribution

| Slot | Visual Weight | Rationale |
|------|---------------|-----------|
| INTRO | Low | Short intro, reader scrolls quickly to products |
| PRODUCTS | High | Hero section — product grid is the main event |
| FAQ | Medium | Collapsible or stacked; helps SEO without dominating visually |
| CTA | Medium-High | Anchor at bottom; should feel conclusive not pushy |

---

## Word Count Target

| Component | Words |
|-----------|-------|
| INTRO | 100–180 |
| PRODUCTS (caption text total) | 60–120 |
| FAQ (all answers combined) | 200–400 |
| CTA (heading + body) | 20–40 |
| **Total** | **380–740** |

Full page word count including Flatsome template surrounding content: target 1200–1500 words
(remaining content comes from Flatsome page template, product descriptions, category text).

---

## Quality Gate Checks (landing_page specific)

- [ ] Primary keyword appears in INTRO within first 2 sentences.
- [ ] PRODUCTS slot has at minimum 3 products.
- [ ] All product URLs are valid sweetsworld.com.au product URLs.
- [ ] CTA contains exactly one link pointing to sweetsworld.com.au.
- [ ] No `<h1>` tags in generated content.
- [ ] No external links in PRODUCTS or CTA slots.
- [ ] Australian English used throughout (no "color", "organize", "candy store" without "lolly" complement).

---

## Related Files

- `DESIGN.md` — master colour, typography, and component rules
- `skins/default.md` — token values
- `components/product_card.md` — product card HTML specification
- `components/cta_box.md` — CTA block HTML specification
- `slot_schema.yaml` — slot validation constraints (logic layer)
- `src/page_type_strategies/landing_page_strategy.py` — Python strategy class
