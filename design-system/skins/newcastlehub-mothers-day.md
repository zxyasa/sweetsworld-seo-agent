# Newcastle Hub — Mother's Day Skin
# Seasonal skin for Mother's Day (second Sunday of May, Australia)
#
# Palette: warm rose & blush — professional enough for a B2B services site,
# festive enough to acknowledge the occasion.
#
# Flatsome key mapping (confirmed 2026-04-08):
#   color_primary      → color_primary       (links, buttons, accent lines)
#   color_cta_accent   → color_alert         (CTA buttons, highlights)
#   color_text_primary → type_nav_color      (nav text colour)
#   color_primary_dark → type_nav_color_hover
#   color_card_bg      → nav_position_bg     (header nav background)
#   color_gallery_bg   → header_shop_bg_color (header accent band)
#   color_card_border  → footer_2_bg_color   (footer background)
#
# Active period: May only
# To revert: python scripts/apply_skin.py --site newcastlehub --rollback --live

skin_id: "newcastlehub-mothers-day"
skin_name: "Newcastle Hub — Mother's Day"
active_months: [5]

# ─── IMAGE PROMPTS ──────────────────────────────────────────────────────────
# Seasonal brief for each image slot (defined in sites/newcastlehub/image_slots.json)
# generate_featured_images.py combines these with the slot's business context.

image_prompt_about_illustration: "Mother's Day, flat vector illustration of two professional women working together at a desktop computer, warm rose pink and blush tones, floral accents, clean modern design, soft pastel palette, celebrating mothers in business"

image_prompt_hero: "Mother's Day, professional mother running her Newcastle small business, warm roses on desk, natural window light, rose gold and blush tones, wide banner"
image_prompt_section_bg: "Mother's Day, warm flowers and greenery, professional Newcastle business woman, bright natural light, blush pink tones, works well under white overlay"
image_prompt_section_dark: "Very soft light blush pink gradient background, barely visible scattered pale rose petals, extremely subtle and muted, almost white with a faint warm pink tint, clean airy professional look, works as a non-distracting backdrop behind image thumbnails and portfolio content, Mother's Day inspired"

# ─── IMAGE REPLACEMENTS ─────────────────────────────────────────────────────
# Generated 2026-04-08 via generate_featured_images.py + Jimeng T2I

image_replacements:
  "152": "954"   # about_illustration (about2.png → mothers-day illustration, URL-based)
  "405": "943"   # hero (banner-bg.jpg → mothers-day hero, URL-based replacement)
  "496": "945"   # section_bg (services-bg.jpg → mothers-day section bg, shortcode-based)
  "435": "951"   # section_dark (blury-bg.jpg → mothers-day light blush bg, URL-based replacement)

# ─── COLOUR REPLACEMENTS ────────────────────────────────────────────────────
color_replacements:
  "#5a49f8": "var(--primary-color)"       # old primary purple → CSS var
  "#ffdd40": "var(--fs-color-secondary)"  # secondary yellow → CSS var
  "#3e0020": "var(--primary-color)"       # footer dark plum → follows primary
  "#e8edf5": "var(--nc-section-bg)"       # section bg blue-grey → skin variable
  "#dfe5ee": "var(--nc-border-color)"     # border/divider blue-grey → skin variable
  "#f6f8fb": "var(--nc-section-bg)"       # page bg very light blue → skin variable
  "#f3f3f3": "var(--nc-section-bg)"       # neutral grey bg → skin variable
  "#334155": "var(--nc-text-secondary)"   # text secondary dark slate → skin variable
  "rgb(243, 243, 243)": ""                 # remove hardcoded grey section backgrounds (bg_color attr)

# ─── COLOUR TOKENS ──────────────────────────────────────────────────────────

color_primary: "#c2185b"
# Deep rose — replaces the default purple for all links and primary accents

color_primary_dark: "#880e4f"
# Darker rose — nav hover states, active elements

color_text_primary: "#3b0a25"
# Very dark plum — nav text, strong readability against light backgrounds

color_text_secondary: "#6d1b4e"
# Mid plum — subheadings and secondary text in content

color_text_muted: "#9c4070"
# Muted rose — captions, metadata, breadcrumbs

color_cta_accent: "#e91e63"
# Vibrant rose-pink — CTA buttons ("Get Your Free Audit") and urgency highlights

color_card_bg: "#ffffff"
# Nav background — keep white for clean header

color_card_border: "#3e0020"
# Dark plum — footer background colour

color_gallery_bg: "#fce4ec"
# Soft blush pink — header accent band (the strip above/below logo area)

color_gallery_border: "#f8bbd9"
# Light pink — card borders and table dividers

color_cta_bg: "#fce4ec"
# Blush tint — CTA block background panel

# ─── TYPOGRAPHY TOKENS ──────────────────────────────────────────────────────

font_size_h2: "1.5rem"
font_size_h3: "1.2rem"
font_size_h4: "1.05rem"
font_size_body: "1.0rem"
font_size_small: "0.875rem"
font_size_cta_button: "1.0rem"

font_weight_heading: "700"
font_weight_subheading: "600"
font_weight_body: "400"
font_weight_cta: "700"

line_height_heading: "1.2"
line_height_subheading: "1.4"
line_height_body: "1.7"

# ─── SPACING TOKENS ─────────────────────────────────────────────────────────

space_xs: "4px"
space_sm: "8px"
space_md: "16px"
space_lg: "24px"
space_xl: "40px"
space_2xl: "64px"

card_padding: "16px"
card_border_radius: "8px"
cta_padding_vertical: "40px"
cta_padding_horizontal: "24px"
section_gap: "40px"

# ─── CUSTOM CSS ─────────────────────────────────────────────────────────────
# Injected via WP Additional CSS (wp-json/wp/v2/settings → custom_css)

```css
/* ── Newcastle Hub · Mother's Day 2026 ── */

/* Skin CSS variables — section backgrounds, borders, secondary text */
:root {
  --nc-section-bg:     #fce4ec;
  --nc-border-color:   #f8bbd9;
  --nc-text-secondary: #6d1b4e;
}

/* Subtle top ribbon */
body::before {
  content: '💐 Happy Mothers Day from Newcastle Hub';
  display: block;
  background: #c2185b;
  color: #fff;
  text-align: center;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 7px 16px;
}

/* Rose tint on filled buttons only — exclude is-link (transparent/text buttons) */
.button:not(.is-link):not(.plain),
.ux-button:not(.is-link):not(.plain),
a.button:not(.is-link):not(.plain) {
  background-color: #c2185b !important;
  border-color: #c2185b !important;
}
.button:not(.is-link):not(.plain):hover,
.ux-button:not(.is-link):not(.plain):hover,
a.button:not(.is-link):not(.plain):hover {
  background-color: #880e4f !important;
  border-color: #880e4f !important;
}

/* CTA accent stays vibrant — filled buttons only */
.button.primary:not(.is-link):not(.plain),
.ux-button.primary:not(.is-link):not(.plain) {
  background-color: #e91e63 !important;
  border-color: #e91e63 !important;
}

/* Contact icons — shift purple circles to rose/pink
   Target by structure (lazy-load replaces src with base64 placeholder) */
.featured-box .icon-inner img {
  filter: hue-rotate(50deg) saturate(1.2);
}
```
