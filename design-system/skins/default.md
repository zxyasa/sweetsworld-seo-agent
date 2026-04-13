# SweetsWorld — Default Skin Tokens
# This file defines the concrete colour and spacing values for the default (year-round) skin.
# These values map 1:1 to the Color Roles defined in DESIGN.md.
#
# Format: role_name: "hex_value"
# Parsed by: src/content_generator.py → DesignSystem._load_skin()
#
# To create a seasonal skin: copy this file, override only the values you want to change.
# Season loader: run_mvp.py reads month → selects skin → dict.update(seasonal) over default.
#
# Last updated: 2026-04-07

skin_id: "default"
skin_name: "SweetsWorld Default"
active_months: [1, 2, 5, 6, 7, 8, 9, 10, 11]  # months not covered by seasonal skins

# ─── COLOUR TOKENS ──────────────────────────────────────────────────────────

color_primary: "#6bb6d9"
# Role: Primary interactive colour — links, button borders, section accent lines
# Source: Extracted from content_generator.py (hardcoded → now skin-managed)

color_primary_dark: "#7aa9c2"
# Role: Hover states, active borders, secondary headings on tinted backgrounds
# Source: Extracted from content_generator.py

color_text_primary: "#3b4b5c"
# Role: All body text, H2, H3, strong elements
# Source: Extracted from content_generator.py

color_text_secondary: "#4d5d6c"
# Role: Subheadings, card titles, lead paragraph text
# Source: Extracted from content_generator.py

color_text_muted: "#666666"
# Role: Captions, metadata, tags, placeholder text, breadcrumbs
# Source: Extracted from content_generator.py (original: #666)

color_cta_accent: "#ff6b6b"
# Role: CTA buttons and urgency highlights ONLY — do not use decoratively
# Source: Extracted from content_generator.py

color_card_bg: "#ffffff"
# Role: Product card backgrounds, info box backgrounds
# Source: Extracted from content_generator.py

color_card_border: "#e7edf3"
# Role: Card borders, horizontal dividers, table borders
# Source: Extracted from content_generator.py

color_gallery_bg: "#f8fbfd"
# Role: Gallery section backgrounds, alternating table row tints
# Source: Extracted from content_generator.py

color_gallery_border: "#e5eef5"
# Role: Gallery section borders, subtle separators in multi-column layouts
# Source: Extracted from content_generator.py

color_cta_bg: "#f8f9fa"
# Role: CTA block background tint (the panel behind the CTA button)
# Source: Extracted from content_generator.py

# ─── TYPOGRAPHY TOKENS ──────────────────────────────────────────────────────
# These values supplement Flatsome's global font settings.
# Only used for inline styles in AI-generated slot HTML.

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
