"""Content generation module for creating SEO-optimized article HTML."""
from __future__ import annotations

from datetime import datetime
import html
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skin token loader — reads design-system/skins/<active_skin>.md and exposes
# colour/spacing tokens so hardcoded hex values can be replaced at module load.
# Silently degrades to {} if the skin file is missing.
# ---------------------------------------------------------------------------

def _load_skin(site_dir: Optional[str] = None) -> dict:
    """Load skin tokens from design-system/skins/<active_skin>.md.

    Token keys in the skin file are stored as ``color_primary``, etc.
    The ``color_`` prefix is stripped so callers use ``_SKIN.get("primary")``.
    """
    try:
        if site_dir is None:
            site_dir = str(Path(__file__).parent.parent / "sites" / "sweetsworld")

        # Determine active_skin from site.json
        site_json = Path(site_dir) / "site.json"
        active_skin = "default"
        if site_json.exists():
            with open(site_json) as _f:
                _data = json.load(_f)
            active_skin = _data.get("active_skin", "default")

            # Seasonal override: if today falls within skin_valid_from..skin_valid_until, use active_skin;
            # otherwise fall back to "default".
            _valid_from = _data.get("skin_valid_from")
            _valid_until = _data.get("skin_valid_until")
            if _valid_from and _valid_until:
                from datetime import date
                _today = date.today().isoformat()
                if not (_valid_from <= _today <= _valid_until):
                    active_skin = "default"

        # Resolve skin file — check site-specific override first, then project root
        _project_root = Path(__file__).parent.parent
        skin_file = Path(site_dir) / "design-system" / "skins" / f"{active_skin}.md"
        if not skin_file.exists():
            skin_file = _project_root / "design-system" / "skins" / f"{active_skin}.md"
        if not skin_file.exists():
            skin_file = _project_root / "design-system" / "skins" / "default.md"
        if not skin_file.exists():
            return {}

        # Parse ``key: "value"`` lines; strip leading ``color_`` from keys.
        tokens: dict = {}
        with open(skin_file) as _f:
            for line in _f:
                m = re.match(r'\s*(\w+)\s*:\s*"([^"]+)"', line)
                if m:
                    key = m.group(1)
                    # Strip common prefixes so callers use short names like "primary"
                    for _prefix in ("color_", "font_", "font_size_", "font_weight_",
                                    "line_height_", "space_", "card_", "cta_",
                                    "section_", "gallery_"):
                        if key.startswith(_prefix):
                            key = key[len(_prefix):]
                            break
                    tokens[key] = m.group(2)
        return tokens
    except Exception:
        return {}


_SKIN: dict = _load_skin()

# ---------------------------------------------------------------------------
# SiteProfile — injects site-specific strings into template generation.
# Set once per run via set_site_profile(). Sub-functions read via _profile().
# ---------------------------------------------------------------------------
from dataclasses import dataclass, field as _field

@dataclass
class SiteProfile:
    brand_name:              str  = "SweetsWorld"
    area_served:             str  = "Australia"
    locale_adjective:        str  = "Australian"
    default_category:        str  = "confectionery"
    default_focus:           str  = "Australian confectionery"
    default_collection_url:  str  = "/candy/"
    default_collection_keys: list = _field(default_factory=lambda: ["candy", "wholesale", "sour_lollies"])
    faq_buy_q:   str = "Where can I buy {focus} in {area}?"
    faq_buy_a:   str = "Start with trusted {locale} {category} stores that list stock availability, shipping windows, and ingredient details for {focus}."
    faq_bulk_a:  str = "Yes. Many {locale} stores offer carton, event, or wholesale bundles, which makes bulk buying practical for {category}."
    catalog_type: str = "products"   # "products" | "services"
    intro_cta:   str = "most relevant {brand} collection or product pages"

    @classmethod
    def from_context(cls, ctx: Any) -> "SiteProfile":
        """Build a SiteProfile from a SiteContext object."""
        collection_keys = list(ctx.collection_urls.keys()) if ctx.collection_urls else ["services"]
        default_url = next(iter(ctx.collection_urls.values()), "/services/") if ctx.collection_urls else "/services/"

        # Derive country/locale from language tag (e.g. "en-AU" → Australia / Australian)
        _lang_tag = (ctx.language or "en-AU").split("-")[-1].upper()
        _area_map   = {"AU": "Australia", "US": "United States", "UK": "United Kingdom", "NZ": "New Zealand"}
        _locale_map = {"AU": "Australian", "US": "American",     "UK": "British",        "NZ": "New Zealand"}
        area        = _area_map.get(_lang_tag, "Australia")
        locale_adj  = _locale_map.get(_lang_tag, "Australian")

        # Override for hyper-local sites (city / suburb level)
        audience_lower = (ctx.audience or "").lower()
        niche_lower    = (ctx.niche or "").lower()
        if "newcastle" in audience_lower or "newcastle" in niche_lower:
            locale_adj = "Newcastle"
            area       = "Newcastle, NSW"
            faq_buy_q  = "Where can I find {focus} in Newcastle?"
            faq_buy_a  = "Search for trusted Newcastle businesses that specialise in {focus}. Check reviews, credentials, and local case studies before engaging."
            faq_bulk_a = "Yes. Many Newcastle {category} providers offer package deals or ongoing service agreements to suit different budgets."
        else:
            faq_buy_q  = "Where can I buy {focus} in {area}?"
            faq_buy_a  = "Start with trusted {locale} {category} stores that list stock availability, shipping windows, and ingredient details for {focus}."
            faq_bulk_a = "Yes. Many {locale} stores offer carton, event, or wholesale bundles, which makes bulk buying practical for {category}."

        default_cat = ctx.niche.replace("_", " ") if ctx.catalog_type == "services" else "confectionery"
        catalog_word = "service" if ctx.catalog_type == "services" else "collection"
        return cls(
            brand_name              = ctx.display_name,
            area_served             = area,
            locale_adjective        = locale_adj,
            default_category        = default_cat,
            default_focus           = f"{locale_adj} {default_cat}",
            default_collection_url  = default_url,
            default_collection_keys = collection_keys,
            faq_buy_q               = faq_buy_q,
            faq_buy_a               = faq_buy_a,
            faq_bulk_a              = faq_bulk_a,
            catalog_type            = ctx.catalog_type,
            intro_cta               = f"most relevant {ctx.display_name} {catalog_word} pages",
        )


_CURRENT_PROFILE: "SiteProfile | None" = None


def set_site_profile(profile: "SiteProfile | None") -> None:
    """Call once before the topic processing loop when --site is active."""
    global _CURRENT_PROFILE
    _CURRENT_PROFILE = profile


def _profile() -> SiteProfile:
    return _CURRENT_PROFILE or SiteProfile()


# ---------------------------------------------------------------------------
# Page-type registry integration — provides quality gate thresholds per type
# ---------------------------------------------------------------------------
try:
    from page_type_registry import get_quality_gate, get_schema_types, list_page_types
    _REGISTRY_AVAILABLE = True
except ImportError:
    _REGISTRY_AVAILABLE = False


def generate_article_html(
    topic_dict: Dict[str, Any],
    use_ai: bool = False,
    openai_generator: Optional[object] = None,
    gsc_data: Optional[Dict[str, Any]] = None,
    content_brief: Optional[Dict[str, Any]] = None,
    page_url: str = "",
) -> str:
    """Generate SEO-optimized HTML article content."""
    if use_ai and openai_generator:
        try:
            ai_html = openai_generator.generate_article_html(topic_dict, gsc_data, content_brief=content_brief)
            # AI 路径没有 Schema JSON-LD — 追加确保质量门通过
            schema_block = _build_schema_json_ld(topic_dict, content_brief, page_url=page_url)
            if schema_block and schema_block not in ai_html:
                return ai_html + "\n" + schema_block
            return ai_html
        except Exception as exc:
            logger.warning(f"AI generation failed, falling back to template: {exc}")

    return generate_template_html(topic_dict, gsc_data, content_brief=content_brief, page_url=page_url)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _escape_text(value: Any) -> str:
    return html.escape(_clean_text(value))


def _trim_text(text: str, max_length: int) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= max_length:
        return cleaned
    shortened = cleaned[: max_length - 1].rsplit(" ", 1)[0].rstrip(",.;:-")
    return f"{shortened}..." if shortened else cleaned[: max_length - 3] + "..."


def _extract_related_keywords(gsc_data: Optional[Dict[str, Any]]) -> List[str]:
    keywords: List[str] = []
    if gsc_data:
        for keyword in gsc_data.get("related_keywords", []) or []:
            cleaned = _clean_text(keyword)
            if cleaned:
                keywords.append(cleaned)
        for row in gsc_data.get("top_queries", []) or []:
            query = row.get("query") if isinstance(row, dict) else None
            cleaned = _clean_text(query)
            if cleaned:
                keywords.append(cleaned)

    deduped: List[str] = []
    seen = set()
    for keyword in keywords:
        lowered = keyword.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(keyword)
    return deduped[:8]


def _pick_internal_links(gsc_data: Optional[Dict[str, Any]]) -> List[str]:
    links: List[str] = []
    if gsc_data:
        for url in gsc_data.get("internal_link_urls", []) or []:
            cleaned = _clean_text(url)
            if cleaned:
                links.append(cleaned)
        for row in gsc_data.get("top_pages", []) or []:
            url = row.get("url") if isinstance(row, dict) else None
            cleaned = _clean_text(url)
            if cleaned:
                links.append(cleaned)

    if not links:
        try:
            from config import get_settings, get_site_collection_urls
            _urls = get_site_collection_urls(get_settings().wp_base_url)
            _keys = _profile().default_collection_keys
            links = [_urls[k] for k in _keys if k in _urls]
        except Exception:
            links = []

    deduped: List[str] = []
    seen = set()
    for url in links:
        lowered = url.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(url)
    return deduped[:3]


def _link_label(url: str, index: int) -> str:
    cleaned = _clean_text(url)
    if not cleaned:
        return f"Related Resource {index}"

    path = cleaned.split("//", 1)[-1].split("/", 1)[-1].strip("/")
    if not path:
        return f"{_profile().brand_name} Home"

    words = [part for part in re.split(r"[-_/]+", path) if part]
    if not words:
        return f"Related Resource {index}"
    return " ".join(word.capitalize() for word in words[:4])


def _intro_focus_phrase(focus: str) -> str:
    normalized = _clean_text(focus)
    p = _profile()
    if not normalized:
        return p.default_focus
    if p.locale_adjective.lower() in normalized.lower() or p.area_served.lower() in normalized.lower():
        return normalized
    return f"{normalized} in {p.area_served}"


def generate_post_excerpt(
    topic_dict: Dict[str, Any],
    gsc_data: Optional[Dict[str, Any]] = None,
    max_length: int = 155,
    content_brief: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a concise SEO-friendly excerpt for WordPress."""
    if content_brief:
        brief_meta = _clean_text(content_brief.get("meta_description", ""))
        if brief_meta:
            return _trim_text(brief_meta, max_length)

    title = _clean_text(topic_dict.get("title", ""))
    keyword = _clean_text(topic_dict.get("primary_keyword", ""))
    p = _profile()
    category = _clean_text(topic_dict.get("category_hint", "")) or p.default_category
    focus = keyword or title or category or p.default_focus
    related = _extract_related_keywords(gsc_data)

    base = f"{p.locale_adjective} guide to {focus}: tips, options, and smart alternatives for {p.area_served} customers."
    if related:
        addition = f" Covers {related[0]}."
        if len(base) + len(addition) <= max_length:
            base += addition
    return _trim_text(base, max_length)


def _format_price(value: Any) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith("$") else f"${cleaned}"


def _product_section_heading(topic_dict: Dict[str, Any], focus: str) -> str:
    page_type = _clean_text(topic_dict.get("page_type", "")).lower()
    category_hint = _clean_text(topic_dict.get("category_hint", ""))
    if page_type == "guide_page":
        return "Relevant Products to Inspect"
    if page_type == "landing_page" and category_hint:
        return f"Recommended {category_hint}"
    return f"Recommended Products for {_escape_text(focus)}"


def build_product_image_gallery(
    selected_products: List[Dict[str, Any]],
    heading: str = "",
) -> str:
    """Build a recommendation gallery.

    For ``catalog_type == "products"``: product cards with image, name, price.
    For ``catalog_type == "services"``: service CTA cards with title, description, link button.
    """
    p = _profile()
    if p.catalog_type == "services":
        return _build_service_cta_gallery(selected_products, heading)
    return _build_product_card_gallery(selected_products, heading)


def _build_service_cta_gallery(
    selected_services: List[Dict[str, Any]],
    heading: str = "",
) -> str:
    """Build a service CTA gallery for non-ecommerce sites."""
    cards: List[str] = []
    for service in selected_services[:3]:
        if not isinstance(service, dict):
            continue
        name = _escape_text(service.get("product_name") or service.get("name") or service.get("service_name") or "")
        url = _clean_text(service.get("url", ""))
        if not name or not url:
            continue

        description = _trim_text(service.get("description", ""), 120)
        _card_bg = _SKIN.get("card_bg", "#ffffff")
        _card_border = _SKIN.get("card_border", "#e7edf3")
        _text_primary = _SKIN.get("text_primary", "#3b4b5c")
        _primary = _SKIN.get("primary", "#6bb6d9")
        desc_html = (
            f'<span style="display: block; font-size: 0.88rem; line-height: 1.45; color: {_text_primary}; margin: 8px 0 12px;">'
            f'{_escape_text(description)}</span>'
            if description else ""
        )
        cards.append((
            f'            <li class="seo-service-card" style="background: {_card_bg}; border: 1px solid {_card_border}; '
            'border-radius: 16px; padding: 18px; box-shadow: 0 1px 2px rgba(31, 52, 73, 0.04);">'
            f'<span style="display: block; font-size: 1rem; font-weight: 600; line-height: 1.4; color: {_text_primary};">{name}</span>'
            f'{desc_html}'
            f'<a href="{html.escape(url, quote=True)}" style="display: inline-block; margin-top: 4px; padding: 8px 16px; '
            f'background: {_primary}; color: #ffffff; text-decoration: none; border-radius: 8px; font-size: 0.9rem;">Learn More</a>'
            '</li>'
        ))

    if not cards:
        return ""

    _gallery_bg = _SKIN.get("gallery_bg", "#f8fbfd")
    _gallery_border = _SKIN.get("gallery_border", "#e5eef5")
    _primary_dark = _SKIN.get("primary_dark", "#7aa9c2")
    _text_secondary = _SKIN.get("text_secondary", "#4d5d6c")
    heading_html = (
        f'        <p style="margin: 0 0 14px; font-size: 1rem; line-height: 1.45; color: {_text_secondary};">{_escape_text(heading)}</p>\n'
        if _clean_text(heading)
        else ""
    )
    return (
        f'\n    <aside class="seo-product-gallery" style="margin: 36px 0; padding: 18px; '
        f'background: {_gallery_bg}; border: 1px solid {_gallery_border}; border-radius: 20px;">\n'
        f'        <p style="margin: 0 0 10px; font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; '
        f'font-weight: 700; color: {_primary_dark};">Related Services</p>\n'
        + heading_html
        + '        <ul style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; list-style: none; padding: 0; margin: 0;">\n'
        + "\n".join(cards)
        + "\n        </ul>\n    </aside>\n"
    )


def _build_product_card_gallery(
    selected_products: List[Dict[str, Any]],
    heading: str = "",
) -> str:
    """Build a product card gallery for ecommerce sites."""
    cards: List[str] = []
    for product in selected_products[:3]:
        if not isinstance(product, dict):
            continue
        name = _escape_text(product.get("product_name") or product.get("name") or "")
        url = _clean_text(product.get("url", ""))
        image_url = _clean_text(product.get("image_url", ""))
        if not name or not url or not image_url:
            continue

        price = _format_price(product.get("price", ""))
        price_html = (
            f'<span style="display: block; margin-top: 8px; font-weight: 600; font-size: 0.95rem; color: {_SKIN.get("primary", "#6bb6d9")};">{_escape_text(price)}</span>'
            if price
            else ""
        )
        _card_bg = _SKIN.get("card_bg", "#ffffff")
        _card_border = _SKIN.get("card_border", "#e7edf3")
        _text_primary = _SKIN.get("text_primary", "#3b4b5c")
        cards.append((
            f'            <li class="seo-product-card" style="background: {_card_bg}; border: 1px solid {_card_border}; '
            'border-radius: 16px; padding: 14px; box-shadow: 0 1px 2px rgba(31, 52, 73, 0.04);">'
            f'<a href="{html.escape(url, quote=True)}" style="text-decoration: none; color: inherit; display: block;">'
            f'<img src="{html.escape(image_url, quote=True)}" alt="{name}" loading="lazy" style="width: 100%; max-width: 180px; '
            'aspect-ratio: 1 / 1; object-fit: contain; display: block; margin: 0 auto 12px;" />'
            f'<span style="display: block; font-size: 0.98rem; line-height: 1.4; margin: 0; color: {_text_primary};">{name}</span>'
            f'{price_html}'
            '</a>'
            '</li>'
        ))

    if not cards:
        return ""

    _text_secondary = _SKIN.get("text_secondary", "#4d5d6c")
    _gallery_bg = _SKIN.get("gallery_bg", "#f8fbfd")
    _gallery_border = _SKIN.get("gallery_border", "#e5eef5")
    _primary_dark = _SKIN.get("primary_dark", "#7aa9c2")
    heading_html = (
        f'        <p style="margin: 0 0 14px; font-size: 1rem; line-height: 1.45; color: {_text_secondary};">{_escape_text(heading)}</p>\n'
        if _clean_text(heading)
        else ""
    )
    return (
        f'\n    <aside class="seo-product-gallery" style="margin: 36px 0; padding: 18px; '
        f'background: {_gallery_bg}; border: 1px solid {_gallery_border}; border-radius: 20px;">\n'
        f'        <p style="margin: 0 0 10px; font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; '
        f'font-weight: 700; color: {_primary_dark};">You may also want to buy</p>\n'
        + heading_html
        + '        <ul style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; list-style: none; padding: 0; margin: 0;">\n'
        + "\n".join(cards)
        + "\n        </ul>\n    </aside>\n"
    )


def _build_product_section(topic_dict: Dict[str, Any], focus: str, content_brief: Optional[Dict[str, Any]] = None) -> str:
    """Build the in-content recommendation section.

    Delegates to product-style or service-style layout based on ``catalog_type``.
    """
    selected_products = []
    if content_brief and isinstance(content_brief.get("selected_products"), list):
        selected_products = content_brief.get("selected_products", [])
    elif isinstance(topic_dict.get("selected_products"), list):
        selected_products = topic_dict.get("selected_products", [])

    p = _profile()
    if p.catalog_type == "services":
        return _build_service_recommendation_section(selected_products, topic_dict, focus)
    return _build_product_recommendation_section(selected_products, topic_dict, focus)


def _build_service_recommendation_section(
    selected_services: List[Dict[str, Any]],
    topic_dict: Dict[str, Any],
    focus: str,
) -> str:
    """Service-oriented recommendation section for non-ecommerce sites."""
    items = []
    for service in selected_services[:4]:
        if not isinstance(service, dict):
            continue
        name = _escape_text(service.get("product_name") or service.get("name") or service.get("service_name") or "")
        url = _clean_text(service.get("url", ""))
        if not name or not url:
            continue

        description = _trim_text(service.get("description", ""), 140)
        description_html = f"<p>{_escape_text(description)}</p>" if description else ""
        items.append(
            "        <li>"
            f"<h3><a href=\"{html.escape(url, quote=True)}\">{name}</a></h3>"
            f"{description_html}"
            "</li>"
        )

    if not items:
        return ""

    p = _profile()
    heading = f"Related {p.brand_name} Services"
    return (
        "\n    <section>\n"
        f"        <h2>{heading}</h2>\n"
        f"        <p>Explore these {p.brand_name} services that relate to {_escape_text(focus)}.</p>\n"
        "        <ul class=\"recommended-services\">\n"
        + "\n".join(items)
        + "\n        </ul>\n    </section>\n"
    )


def _build_product_recommendation_section(
    selected_products: List[Dict[str, Any]],
    topic_dict: Dict[str, Any],
    focus: str,
) -> str:
    """Product-oriented recommendation section for ecommerce sites."""
    items = []
    for product in selected_products[:4]:
        if not isinstance(product, dict):
            continue
        name = _escape_text(product.get("product_name") or product.get("name") or "")
        url = _clean_text(product.get("url", ""))
        image_url = _clean_text(product.get("image_url", ""))
        if not name or not url:
            continue

        description = _trim_text(product.get("description", ""), 140)
        category = _escape_text(product.get("category", ""))
        price = _format_price(product.get("price", ""))
        matched_tokens = product.get("matched_tokens") or []
        matched_text = ", ".join(_escape_text(token) for token in matched_tokens[:3] if _clean_text(token))
        meta_parts = [part for part in [category, price, matched_text] if part]
        meta_html = f"<p><small>{' | '.join(meta_parts)}</small></p>" if meta_parts else ""
        description_html = f"<p>{_escape_text(description)}</p>" if description else ""
        image_html = (
            f'<p><a href="{html.escape(url, quote=True)}">'
            f'<img src="{html.escape(image_url, quote=True)}" alt="{name}" loading="lazy" '
            'style="width: 100%; max-width: 220px; aspect-ratio: 1 / 1; object-fit: contain; '
            'display: block; margin: 0 0 12px;" /></a></p>'
            if image_url
            else ""
        )
        items.append(
            "        <li>"
            f"{image_html}"
            f"<h3><a href=\"{html.escape(url, quote=True)}\">{name}</a></h3>"
            f"{meta_html}"
            f"{description_html}"
            "</li>"
        )

    if not items:
        return ""

    return (
        "\n    <section>\n"
        f"        <h2>{_product_section_heading(topic_dict, focus)}</h2>\n"
        "        <p>These recommendations are matched using the current pilot product rules, so the page only shows relevant catalogue items when there is a clear category fit.</p>\n"
        "        <ul class=\"recommended-products\">\n"
        + "\n".join(items)
        + "\n        </ul>\n    </section>\n"
    )


def _default_sections(page_type: str, focus: str, category: str) -> List[Dict[str, Any]]:
    if page_type == "landing_page":
        return [
            {
                "heading": f"Why shoppers buy {focus} online",
                "paragraphs": [
                    f"Visitors searching for {focus} usually want stock clarity, price context, and a fast path to the right products.",
                    "The page should reduce purchase friction instead of acting like a thin SEO placeholder.",
                ],
                "bullets": [
                    "Compare price, pack size, and range depth together.",
                    "Highlight delivery timing and stock expectations.",
                    "Keep the call to action aligned with the keyword intent.",
                ],
            },
            {
                "heading": f"How to compare {category} options before ordering",
                "paragraphs": [
                    "Strong landing pages explain the trade-offs between convenience, range, and value.",
                    "That gives the page both ranking value and conversion value.",
                ],
                "bullets": [
                    "Surface the best-fit collection pages first.",
                    "Make bulk and bundle options easy to compare.",
                    "Use FAQs to answer purchase objections clearly.",
                ],
            },
        ]

    if page_type == "category_page":
        return [
            {
                "heading": f"What defines the {focus} category",
                "paragraphs": [
                    f"A useful {focus} page should explain flavour profile, format, and the recognisable products shoppers expect in the range.",
                    "That gives the page clear scope instead of leaving it as a thin product archive.",
                ],
                "bullets": [
                    "Explain the core flavour or format signals.",
                    "Point shoppers toward best sellers early.",
                    "Link into adjacent collections and products.",
                ],
            },
            {
                "heading": f"How to shop {category} with more confidence",
                "paragraphs": [
                    "Category pages should help readers compare formats, value, and suitability before they click deeper.",
                    "This is where the page supports both rankings and conversion.",
                ],
                "bullets": [
                    "Separate single treats from bundles or giftable options.",
                    "Call out who the range best suits.",
                    "Use internal links to support neighbouring categories.",
                ],
            },
        ]

    return [
        {
            "heading": f"Why {focus} works for this use case",
            "paragraphs": [
                f"Pages targeting {focus} should explain why the products fit the moment instead of repeating the keyword mechanically.",
                "The page should translate the query into practical buying guidance.",
            ],
            "bullets": [
                "Match products to audience, flavour, and format.",
                "Separate novelty picks from reliable crowd-pleasers.",
                "Keep shipping and storage practicality in mind.",
            ],
        },
        {
            "heading": "How to choose the right shortlist",
            "paragraphs": [
                "Good content pages help readers compare taste, shareability, portion size, and buying format before they click through.",
                "That is the difference between a useful page and a filler page.",
            ],
            "bullets": [
                "Turn the query into clear comparison points.",
                "Keep the next click obvious.",
                "Use FAQs to handle common objections or edge cases.",
            ],
        },
    ]


def _default_faq_items(focus: str, category: str) -> List[Tuple[str, str]]:
    p = _profile()
    nf = _clean_text(focus) or _clean_text(category) or "this"
    nc = _clean_text(category) or p.default_category
    _fmt = lambda t, **kw: t.format(focus=nf, category=nc.lower(), area=p.area_served, locale=p.locale_adjective, **kw)
    return [
        (
            _fmt(p.faq_buy_q),
            _fmt(p.faq_buy_a),
        ),
        (
            f"How do I compare {nf} options?",
            f"Compare quality, pricing, credentials, and delivery or availability details before choosing the best {nf} for your needs.",
        ),
        (
            f"Are there package or bulk options for {nc.lower()}?",
            _fmt(p.faq_bulk_a),
        ),
    ]


def _normalise_sections(content_brief: Optional[Dict[str, Any]], page_type: str, focus: str, category: str) -> List[Dict[str, Any]]:
    if content_brief and isinstance(content_brief.get("sections"), list) and content_brief.get("sections"):
        return content_brief.get("sections", [])
    return _default_sections(page_type, focus, category)


def _render_sections(content_brief: Optional[Dict[str, Any]], page_type: str, focus: str, category: str) -> str:
    sections = _normalise_sections(content_brief, page_type, focus, category)
    blocks: List[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        heading = _escape_text(section.get("heading", ""))
        paragraphs = section.get("paragraphs", []) if isinstance(section.get("paragraphs"), list) else []
        bullets = section.get("bullets", []) if isinstance(section.get("bullets"), list) else []

        parts: List[str] = []
        if heading:
            parts.append(f"        <h2>{heading}</h2>")
        for paragraph in paragraphs:
            cleaned = _clean_text(paragraph)
            if cleaned:
                parts.append(f"        <p>{_escape_text(cleaned)}</p>")
        if bullets:
            bullet_html = "\n".join(
                f"            <li>{_escape_text(item)}</li>" for item in bullets if _clean_text(item)
            )
            if bullet_html:
                parts.append("        <ul>\n" + bullet_html + "\n        </ul>")
        if parts:
            blocks.append("    <section>\n" + "\n".join(parts) + "\n    </section>")
    return "\n".join(blocks)


def _normalise_internal_links(content_brief: Optional[Dict[str, Any]], gsc_data: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    links = content_brief.get("internal_links", []) if content_brief else []
    normalised: List[Dict[str, str]] = []
    if isinstance(links, list):
        for index, row in enumerate(links, 1):
            if isinstance(row, dict):
                url = _clean_text(row.get("url", ""))
                label = _clean_text(row.get("label", "")) or _link_label(url, index)
                anchor_text = _clean_text(row.get("anchor_text", "")) or label
            else:
                url = _clean_text(row)
                label = _link_label(url, index)
                anchor_text = label
            if url:
                normalised.append({"url": url, "label": label, "anchor_text": anchor_text})
    if normalised:
        return normalised[:3]

    fallback: List[Dict[str, str]] = []
    for index, url in enumerate(_pick_internal_links(gsc_data), 1):
        label = _link_label(url, index)
        fallback.append({"url": url, "label": label, "anchor_text": label})
    return fallback


def _render_brief_links(content_brief: Optional[Dict[str, Any]], gsc_data: Optional[Dict[str, Any]]) -> str:
    items = []
    for link in _normalise_internal_links(content_brief, gsc_data):
        url = html.escape(link["url"], quote=True)
        anchor_text = _escape_text(link.get("anchor_text", ""))
        label = _escape_text(link.get("label", ""))
        items.append(
            "        <li>"
            f"<a href=\"{url}\">{anchor_text}</a>"
            f"<span> - {label}</span>"
            "</li>"
        )
    return "\n".join(items)


def _normalise_faq_items(content_brief: Optional[Dict[str, Any]], focus: str, category: str) -> List[Tuple[str, str]]:
    items = content_brief.get("faq_items", []) if content_brief else []
    normalised: List[Tuple[str, str]] = []
    if isinstance(items, list):
        for row in items:
            if not isinstance(row, dict):
                continue
            question = _clean_text(row.get("question", ""))
            answer = _clean_text(row.get("answer", ""))
            if question and answer:
                normalised.append((question, answer))
    if normalised:
        return normalised[:5]
    return _default_faq_items(focus, category)


def _render_brief_faq(content_brief: Optional[Dict[str, Any]], focus: str, category: str) -> str:
    blocks = []
    for question, answer in _normalise_faq_items(content_brief, focus, category):
        blocks.append(
            f"    <h3>{_escape_text(question)}</h3>\n"
            f"    <p>{_escape_text(answer)}</p>"
        )
    return "\n".join(blocks)


def _render_brief_cta(content_brief: Optional[Dict[str, Any]], focus: str, gsc_data: Optional[Dict[str, Any]]) -> str:
    cta = content_brief.get("cta", {}) if content_brief and isinstance(content_brief.get("cta"), dict) else {}
    heading = _clean_text(cta.get("heading", "")) or f"Use this page to move from {focus} research into a purchase"
    body = _clean_text(cta.get("body", "")) or "Compare the shortlist, then move into the most relevant collection or product page to check live stock and delivery details."
    links = _normalise_internal_links(content_brief, gsc_data)
    primary_url = links[0]["url"] if links else _profile().default_collection_url
    button_text = _clean_text(cta.get("button_text", "")) or "Browse Related Collection"
    return (
        f"\n    <section class=\"cta-box\" style=\"background: {_SKIN.get('cta_bg', '#f8f9fa')}; padding: 24px; margin: 32px 0; border-left: 4px solid {_SKIN.get('cta_accent', '#ff6b6b')}; border-radius: 4px;\">\n"
        f"        <h2>{_escape_text(heading)}</h2>\n"
        f"        <p>{_escape_text(body)}</p>\n"
        f"        <p><a href=\"{html.escape(primary_url, quote=True)}\" style=\"color: {_SKIN.get('cta_accent', '#ff6b6b')}; font-weight: bold;\">{_escape_text(button_text)}</a></p>\n"
        "    </section>\n"
    )


def _build_schema_json_ld(
    topic_dict: Dict[str, Any],
    content_brief: Optional[Dict[str, Any]],
    page_url: str = "",
) -> str:
    """Build a <script type='application/ld+json'> block with Schema.org markup.

    Emits:
      - BreadcrumbList (all pages, when page_url is known)
      - FAQPage        (guide_page with faq_items)
      - ItemList       (landing_page with products)
    """
    brief = content_brief or {}
    page_type = _clean_text(topic_dict.get("page_type", ""))
    title = _clean_text(brief.get("title") or topic_dict.get("title", ""))
    category_hint = _clean_text(topic_dict.get("category_hint", "Products"))

    schemas: List[Dict[str, Any]] = []

    # --- BreadcrumbList ---
    if page_url:
        # Try to derive category URL from first internal link tagged as category
        cat_url = ""
        cat_name = category_hint
        for link in brief.get("internal_links", []):
            if isinstance(link, dict) and link.get("link_type") == "category":
                cat_url = link.get("url", "")
                cat_name = link.get("label", category_hint) or category_hint
                break

        items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": _base_url(page_url)}]
        if cat_url:
            items.append({"@type": "ListItem", "position": 2, "name": cat_name, "item": cat_url})
        items.append({"@type": "ListItem", "position": len(items) + 1, "name": title, "item": page_url})

        schemas.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})

    # Determine which schema types to emit — prefer registry, fall back to hardcoded rules
    if _REGISTRY_AVAILABLE:
        schema_type_list = get_schema_types(page_type)
        # Also check if brief has schema_types set by strategy
        schema_type_list = brief.get("schema_types", schema_type_list)
    else:
        schema_type_list = ["BreadcrumbList", "FAQPage"] if page_type == "guide_page" else \
                           ["BreadcrumbList", "ItemList"] if page_type in ("landing_page", "occasion_page", "best_of_page", "comparison_page") else \
                           ["BreadcrumbList"]

    # --- FAQPage ---
    if "FAQPage" in schema_type_list:
        faq_pairs = _normalise_faq_items(brief, title, category_hint)
        if faq_pairs:
            faq_entities = [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                }
                for q, a in faq_pairs
            ]
            schemas.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_entities})

    # --- ItemList (landing/occasion/best_of/comparison pages) ---
    if "ItemList" in schema_type_list:
        products = topic_dict.get("selected_products", [])
        if not products and brief:
            products = brief.get("selected_products", [])
        if products:
            list_items = [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "url": p.get("url", ""),
                    "name": p.get("product_name") or p.get("name", ""),
                }
                for i, p in enumerate(products)
                if (p.get("url") and (p.get("product_name") or p.get("name")))
            ]
            if list_items:
                schemas.append(
                    {
                        "@context": "https://schema.org",
                        "@type": "ItemList",
                        "name": title,
                        "itemListElement": list_items,
                    }
                )

    # --- LocalBusiness (city_landing_page) ---
    if "LocalBusiness" in schema_type_list:
        try:
            from config import get_settings
            settings = get_settings()
            base_url = settings.wp_base_url.rstrip("/")
        except Exception:
            base_url = _base_url(page_url) if page_url else ""
        p = _profile()
        schemas.append({
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": p.brand_name,
            "description": title,
            "url": base_url,
            "areaServed": p.area_served,
            "priceRange": "$$",
        })

    if not schemas:
        return ""

    blocks = "\n".join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas
    )
    return "\n" + blocks


def _base_url(url: str) -> str:
    """Extract scheme+host from a full URL, e.g. https://sweetsworld.com.au."""
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return url


def generate_template_html(
    topic_dict: Dict[str, Any],
    gsc_data: Optional[Dict[str, Any]] = None,
    content_brief: Optional[Dict[str, Any]] = None,
    page_url: str = "",
) -> str:
    """Generate SEO-optimized HTML using a structured template."""
    raw_title = _clean_text(topic_dict.get("title", "Untitled"))
    raw_keyword = _clean_text(topic_dict.get("primary_keyword", ""))
    raw_category = _clean_text(topic_dict.get("category_hint", "Products"))
    page_type = _clean_text(topic_dict.get("page_type", "occasion_page")) or "occasion_page"
    p = _profile()
    focus = raw_keyword or raw_title or raw_category or p.default_focus

    title = _escape_text((content_brief or {}).get("title") or raw_title or "Untitled")
    intro_focus = _escape_text(_intro_focus_phrase(raw_keyword or focus))
    related_keywords = _extract_related_keywords(gsc_data)
    related_keywords_text = ", ".join(_escape_text(term) for term in related_keywords[:5])
    intro_text = _escape_text(
        (content_brief or {}).get("intro")
        or f"Looking for the best {intro_focus}? This page is structured to answer the real questions behind the keyword, then guide you toward the {p.intro_cta}."
    )
    search_intent = _escape_text((content_brief or {}).get("search_intent") or "Informational")

    related_keywords_block = ""
    if related_keywords_text:
        related_keywords_block = (
            "\n    <p class=\"seo-supporting-keywords\">"
            f"Supporting search terms to cover naturally: {related_keywords_text}."
            "</p>\n"
        )

    product_section_html = _build_product_section(topic_dict, focus, content_brief=content_brief)
    sections_html = _render_sections(content_brief, page_type, focus, raw_category)
    resource_links = _render_brief_links(content_brief, gsc_data)
    faq_html = _render_brief_faq(content_brief, focus, raw_category)
    cta_html = _render_brief_cta(content_brief, focus, gsc_data)
    schema_block = _build_schema_json_ld(topic_dict, content_brief, page_url=page_url)
    last_updated = datetime.now().strftime("%d %B %Y")

    html_output = f"""
<article class=\"seo-content seo-{html.escape(page_type)}\">
    <p class=\"seo-intent\" style=\"font-size: 0.95em; color: {_SKIN.get('text_muted', '#666666')}; margin-bottom: 12px;\">
        <strong>Search intent:</strong> {search_intent}
    </p>

    <p class=\"intro\">{intro_text}</p>{related_keywords_block}{product_section_html}{sections_html}

    <section>
        <h2>Internal Resources to Strengthen the Page</h2>
        <p>
            Link readers toward closely related category, collection, and product pages so this content supports discovery,
            crawl depth, and conversion instead of acting as an isolated SEO page.
        </p>
        <ul>
{resource_links}
        </ul>
    </section>{cta_html}

    <section class=\"faq-section\">
        <h2>Frequently Asked Questions</h2>
{faq_html}
    </section>

    <p class=\"last-updated\" style=\"font-size: 0.9em; color: {_SKIN.get('text_muted', '#666666')}; margin-top: 48px;\">
        <em>Last updated: {html.escape(last_updated)}</em>
    </p>
</article>
<!-- AI_SLOT:SCHEMA -->
{schema_block}"""
    return html_output.strip()


# ---------------------------------------------------------------------------
# Content quality gate
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\[PLACEHOLDER\]|TODO|FIXME|lorem ipsum", re.IGNORECASE)
_WORD_RE = re.compile(r"\w+")
_H1_RE = re.compile(r"<h1[\s>]", re.IGNORECASE)


# Minimum word counts by page type — extended with new page types.
# Registry values are preferred at runtime; this dict is the compile-time fallback.
_MIN_WORDS_BY_PAGE_TYPE: Dict[str, int] = {
    "guide_page":        400,
    "landing_page":      350,
    "occasion_page":     350,
    "category_page":     250,
    "faq_page":          300,
    "comparison_page":   500,
    "best_of_page":      500,
    "city_landing_page": 400,
}
_MIN_WORDS_DEFAULT = 350


def _registry_min_words(page_type: str) -> int:
    """Get min word count from registry if available, else use local dict."""
    if _REGISTRY_AVAILABLE:
        try:
            gate = get_quality_gate(page_type)
            return gate.min_words
        except Exception:
            pass
    return _MIN_WORDS_BY_PAGE_TYPE.get(page_type, _MIN_WORDS_DEFAULT)

_SCHEMA_SCRIPT_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def validate_content_quality(
    html_content: str,
    topic: Dict[str, Any],
    min_words: Optional[int] = None,
    title: str = "",
    excerpt: str = "",
) -> Tuple[bool, List[str]]:
    """Check minimum quality thresholds before publishing.

    Args:
        html_content: The generated HTML body.
        topic: Topic dict (used for page_type and primary_keyword).
        min_words: Override word-count minimum. If None, uses page-type defaults.
        title: Post title (for length check). Pass empty string to skip.
        excerpt: Post excerpt / meta description (for length check). Pass empty string to skip.

    Returns:
        (ok, reasons) — ok is True when all checks pass.
    """
    reasons: List[str] = []

    page_type = str(topic.get("page_type", "")).strip().lower()
    effective_min_words = (
        min_words
        if min_words is not None
        else _registry_min_words(page_type)
    )

    # Strip tags to get plain text for word count / keyword check
    plain_text = re.sub(r"<[^>]+>", " ", html_content)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()

    # 1. Minimum word count (page-type aware)
    word_count = len(_WORD_RE.findall(plain_text))
    if word_count < effective_min_words:
        reasons.append(
            f"word count too low: {word_count} words (minimum {effective_min_words} for {page_type or 'this page type'})"
        )

    # 2. H1 check skipped intentionally — WP theme renders H1 from the post title
    # outside the content body. Template-generated content starts at H2 level.
    h1_count = len(_H1_RE.findall(html_content))
    if h1_count > 1:
        reasons.append(f"too many H1 tags in content body: found {h1_count} (should be 0 or 1)")

    # 3. Target keyword appears at least twice in plain text
    topic_title = _clean_text(topic.get("title", ""))
    keyword = _clean_text(topic.get("primary_keyword", "")) or topic_title
    if keyword:
        tokens = [t for t in re.split(r"\W+", keyword.lower()) if len(t) > 3]
        if tokens:
            core_token = tokens[0]
            occurrences = len(re.findall(re.escape(core_token), plain_text, re.IGNORECASE))
            if occurrences < 2:
                reasons.append(
                    f"keyword '{core_token}' appears only {occurrences} time(s) in content"
                )

    # 4. No leftover template placeholders
    if _PLACEHOLDER_RE.search(plain_text):
        reasons.append("content contains placeholder text (TODO / PLACEHOLDER / lorem ipsum)")

    # 5. WP post title length (10–70 chars)
    # 注意：WP post title ≠ SEO meta title；Yoast/RankMath 会单独设置 meta title。
    # 70 字符是 Google 的实际截断点；超过 70 才算真正有风险，这里只做 WARNING 级别记录，不拦截。
    clean_title = _clean_text(title)
    if clean_title:
        title_len = len(clean_title)
        if title_len < 10:
            reasons.append(f"meta title too short: {title_len} chars (minimum 10)")
        # 超过 70 chars 仅记录日志，不加入 reasons（不拦截发布）
        elif title_len > 70:
            logger.warning(
                f"Post title is {title_len} chars (>70), may be truncated in SERPs: {clean_title[:80]}"
            )

    # 6. Meta description / excerpt length (50–160 chars)
    clean_excerpt = re.sub(r"<[^>]+>", "", excerpt).strip()
    if clean_excerpt:
        exc_len = len(clean_excerpt)
        if exc_len < 50:
            reasons.append(f"meta description too short: {exc_len} chars (minimum 50)")
        elif exc_len > 160:
            reasons.append(f"meta description too long: {exc_len} chars (maximum 160, will be truncated)")

    # 7. Schema JSON-LD must be present and parseable
    schema_blocks = _SCHEMA_SCRIPT_RE.findall(html_content)
    if not schema_blocks:
        reasons.append("no schema JSON-LD block found in content")
    else:
        for i, block in enumerate(schema_blocks):
            try:
                json.loads(block.strip())
            except (json.JSONDecodeError, ValueError) as exc:
                reasons.append(f"schema JSON-LD block {i + 1} is invalid JSON: {exc}")

    ok = len(reasons) == 0
    return ok, reasons
