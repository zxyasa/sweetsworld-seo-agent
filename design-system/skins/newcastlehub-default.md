# Newcastle Hub — Default Skin Tokens
# This file defines the concrete colour and spacing values for the Newcastle Hub default skin.
# These values map 1:1 to the Color Roles defined in DESIGN.md.
#
# Format: role_name: "hex_value"
# Parsed by: src/content_generator.py → DesignSystem._load_skin()
#
# Palette: neutral professional blues and greys — no candy brand colours.
# All TODO-CONFIRM values should be verified against the live site before activation.
#
# To create a seasonal skin: copy this file, override only the values you want to change.
#
# Last updated: 2026-04-08

skin_id: "newcastlehub-default"
skin_name: "Newcastle Hub Default"
active_months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # year-round, no seasonal overrides yet

# ─── COLOUR REPLACEMENTS ────────────────────────────────────────────────────
# Hardcoded hex values in page/post/ux-block content to replace on skin apply.
# Format: "old_hex": "new_value"  (new_value can be hex or CSS variable)
# apply_skin.py scans all pages, posts, and ux-blocks and replaces these.

color_replacements:
  "#5a49f8": "var(--primary-color)"       # old primary purple → CSS var
  "#ffdd40": "var(--fs-color-secondary)"  # old secondary yellow → CSS var
  "rgb(243, 243, 243)": ""                 # remove hardcoded grey section backgrounds (bg_color attr)

# ─── COLOUR TOKENS ──────────────────────────────────────────────────────────
# TODO-CONFIRM: Verify all colour values against the live newcastlehub.com.au theme
# before activation. Current values are neutral professional defaults.

color_primary: "#2563eb"
# Role: Primary interactive colour — links, button borders, section accent lines
# TODO-CONFIRM: match to theme's primary brand blue

color_primary_dark: "#1d4ed8"
# Role: Hover states, active borders, secondary headings on tinted backgrounds
# TODO-CONFIRM: match to theme's hover/dark variant

color_text_primary: "#1e293b"
# Role: All body text, H2, H3, strong elements
# TODO-CONFIRM: match to site's body text colour

color_text_secondary: "#334155"
# Role: Subheadings, card titles, lead paragraph text
# TODO-CONFIRM: match to site's secondary text colour

color_text_muted: "#64748b"
# Role: Captions, metadata, tags, placeholder text, breadcrumbs
# TODO-CONFIRM: match to site's muted/grey text

color_cta_accent: "#f59e0b"
# Role: CTA buttons and urgency highlights ONLY — do not use decoratively
# TODO-CONFIRM: match to site's CTA/action colour (amber/orange is a neutral choice)

color_card_bg: "#ffffff"
# Role: Product/service card backgrounds, info box backgrounds

color_card_border: "#e2e8f0"
# Role: Card borders, horizontal dividers, table borders

color_gallery_bg: "#f8fafc"
# Role: Gallery section backgrounds, alternating table row tints

color_gallery_border: "#e2e8f0"
# Role: Gallery section borders, subtle separators in multi-column layouts

color_cta_bg: "#f1f5f9"
# Role: CTA block background tint (the panel behind the CTA button)

# ─── TYPOGRAPHY TOKENS ──────────────────────────────────────────────────────
# These values supplement Flatsome's global font settings.
# Only used for inline styles in AI-generated slot HTML.
# TODO-CONFIRM: match font sizes to the live Flatsome theme configuration.

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
# CSS variable definitions — must mirror the default palette values so that
# rolling back from a seasonal skin restores the correct colours everywhere.

```css
/* ── Newcastle Hub Default Skin — CSS Variables ── */
:root {
  --nc-section-bg:     #e8edf5;
  --nc-border-color:   #dfe5ee;
  --nc-text-secondary: #334155;
}

/* ── Accessibility: Colour Contrast Fixes (WCAG AA) ── */

/* Fix 1: All nav menu text on blue primary background → white */
.ux-menu-link__text {
  color: #ffffff !important;
}

/* Fix 2: Topbar contact links (tel/mailto/maps) on blue bg → white */
/* Class-based selector for links not using inline styles */
.header a[href^="tel:"],
.header a[href^="mailto:"],
.header a[href*="maps.google"],
.top-bar a[href^="tel:"],
.top-bar a[href^="mailto:"],
.top-bar a[href*="maps.google"] {
  color: #ffffff !important;
}
/* Inline-style override: targets links using var(--fs-color-secondary) inline */
a[href^="tel:"][style*="color"],
a[href^="mailto:"][style*="color"],
a[href*="maps.google"][style*="color"] {
  color: #ffffff !important;
}

/* Fix 3: Footer policy links — rgba(255,255,255,0.75) → full white */
footer a[href*="privacy"],
footer a[href*="terms"] {
  color: #ffffff !important;
  opacity: 1 !important;
}

/* Fix 4: Secondary button — yellow bg needs dark text, not white */
.button.secondary,
a.button.secondary {
  color: #1a1a1a !important;
}
```

# ─── IMAGE REPLACEMENTS (ROLLBACK) ──────────────────────────────────────────
# Reverse mappings — applying this skin restores original images

# image_replacements cleared 2026-04-09 — current images are Jimeng-generated set
# Previous rollback values: "954":"152" / "943":"405" / "945":"496" / "951":"435"
image_replacements: {}
