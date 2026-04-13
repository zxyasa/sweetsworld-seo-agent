from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Site-specific collection URLs override (set by run_mvp.py for multi-site)
# When set, these replace the sweetsworld-specific fallback URLs in helpers
# like _default_link_candidates and _category_hint_candidates.
# ---------------------------------------------------------------------------
_SITE_COLLECTION_URLS: "dict[str, str] | None" = None


def set_site_collection_urls(collection_urls: "dict[str, str] | None") -> None:
    """Override the default collection URL fallbacks for the current site."""
    global _SITE_COLLECTION_URLS
    _SITE_COLLECTION_URLS = collection_urls or None


def _get_collection_urls() -> "dict[str, str]":
    """Return active collection URLs: site-specific if set, else sweetsworld defaults."""
    if _SITE_COLLECTION_URLS is not None:
        return _SITE_COLLECTION_URLS
    try:
        from config import get_settings, get_site_collection_urls
        return get_site_collection_urls(get_settings().wp_base_url)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Page-type strategy registry integration
# ---------------------------------------------------------------------------
try:
    from page_type_registry import build_brief_from_strategy, is_valid_page_type
    _STRATEGY_REGISTRY_AVAILABLE = True
except ImportError:
    _STRATEGY_REGISTRY_AVAILABLE = False
    logger.debug("page_type_registry not available — using built-in brief templates")


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _trim_text(text: str, max_length: int) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= max_length:
        return cleaned
    shortened = cleaned[: max_length - 1].rsplit(" ", 1)[0].rstrip(",.;:-")
    return f"{shortened}..." if shortened else cleaned[: max_length - 3] + "..."


def _dedupe_strings(items: List[str], limit: int) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for item in items:
        cleaned = _clean_text(item)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


def _extract_related_keywords(gsc_data: Optional[Dict[str, Any]]) -> List[str]:
    keywords: List[str] = []
    if not gsc_data:
        return keywords

    keywords.extend(gsc_data.get("related_keywords", []) or [])
    for row in gsc_data.get("top_queries", []) or []:
        if isinstance(row, dict):
            keywords.append(row.get("query", ""))
    return _dedupe_strings(keywords, 6)


def _slug_to_label(value: str) -> str:
    words = [part for part in re.split(r"[-_]+", value) if part]
    return " ".join(word.capitalize() for word in words[:6]).strip()


def _link_label(url: str, index: int) -> str:
    cleaned = _clean_text(url)
    path = cleaned.split("//", 1)[-1].split("/", 1)[-1].strip("/")
    if not path:
        return f"Related Resource {index}"

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return f"Related Resource {index}"

    if len(segments) >= 3:
        return _slug_to_label(segments[-1]) or _slug_to_label(segments[-2]) or f"Related Resource {index}"
    if len(segments) == 2:
        return _slug_to_label(segments[-1]) or _slug_to_label(segments[0]) or f"Related Resource {index}"
    return _slug_to_label(segments[0]) or f"Related Resource {index}"


def _split_url(url: str) -> tuple[str, List[str]]:
    cleaned = _clean_text(url)
    if not cleaned:
        return "", []
    if "//" in cleaned:
        scheme, rest = cleaned.split("//", 1)
        host, _, path = rest.partition("/")
        origin = f"{scheme}//{host}"
    else:
        origin = ""
        path = cleaned.strip("/")
    segments = [segment for segment in path.split("/") if segment]
    return origin.rstrip("/"), segments


def _join_url(origin: str, segments: List[str]) -> str:
    if not origin or not segments:
        return ""
    return f"{origin}/{'/'.join(segments)}/"


def _link_kind(url: str) -> str:
    cleaned = _clean_text(url).lower()
    path = cleaned.split("//", 1)[-1].split("/", 1)[-1].strip("/")
    segments = [segment for segment in path.split("/") if segment]

    if any(token in cleaned for token in ["bulk", "wholesale", "gift-box", "gift-boxes", "buy", "online"]):
        return "commercial"
    if len(segments) >= 3:
        return "product"
    if len(segments) == 1:
        return "category"
    return "collection"


def _anchor_variants(label: str, page_type: str, link_kind: str) -> List[str]:
    base = _clean_text(label) or "this page"
    if link_kind == "product":
        candidates = [
            f"View {base}",
            f"Compare {base}",
            f"See {base}",
        ]
    elif link_kind == "commercial" or page_type == "landing_page":
        candidates = [
            f"Shop {base}",
            f"Browse {base}",
            f"Compare {base}",
        ]
    elif page_type == "guide_page":
        candidates = [
            f"See {base}",
            f"Compare {base} options",
            f"Browse {base}",
        ]
    else:
        candidates = [
            f"Explore {base}",
            f"Browse {base}",
            f"See {base}",
        ]

    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        cleaned = _clean_text(candidate)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped or [base]


def _category_hint_candidates(category_hint: str) -> List[str]:
    hint = _clean_text(category_hint).lower()
    if not hint:
        return []

    _u = _get_collection_urls()

    # These keys are sweetsworld-specific — skip them for non-candy sites
    urls: List[str] = []
    if "american" in hint and "candy" in hint:
        urls.append(_u.get("american_candy", ""))
    if "japanese" in hint and "candy" in hint:
        urls.append(_u.get("japanese_candy", ""))
    if "chocolate" in hint:
        urls.append(_u.get("chocolate", ""))
    if "candy" in hint or "lollies" in hint:
        urls.append(_u.get("candy", ""))
    if "sour" in hint:
        urls.append(_u.get("sour_lollies", ""))
    return _dedupe_strings([u for u in urls if u], 3)


def _product_link_candidates(selected_products: List[Dict[str, Any]], page_type: str) -> List[str]:
    def sort_key(product: Dict[str, Any], index: int) -> tuple[int, int, int, int]:
        category = _clean_text(product.get("category", "")).lower()
        selection_reason = _clean_text(product.get("selection_reason", "")).lower()
        is_wholesale = 1 if "wholesale" in category else 0
        is_direct = 0 if selection_reason == "direct_match" else 1
        if page_type == "guide_page":
            return (is_direct, is_wholesale, index, 0)
        if page_type == "landing_page":
            return (is_direct, is_wholesale, index, 0)
        return (is_wholesale, is_direct, index, 0)

    ordered_products = [product for product in selected_products[:3] if isinstance(product, dict)]
    ordered_products = [
        product for _, product in sorted(
            enumerate(ordered_products),
            key=lambda pair: sort_key(pair[1], pair[0]),
        )
    ]

    urls: List[str] = []
    for product in ordered_products:
        url = _clean_text(product.get("url", ""))
        if not url:
            continue
        origin, segments = _split_url(url)
        if len(segments) >= 2:
            urls.append(_join_url(origin, segments[:2]))
        if len(segments) >= 1:
            urls.append(_join_url(origin, segments[:1]))
        urls.append(url)
    return _dedupe_strings(urls, 6)


def _gsc_link_candidates(gsc_data: Optional[Dict[str, Any]]) -> List[str]:
    urls: List[str] = []
    if gsc_data:
        urls.extend(gsc_data.get("internal_link_urls", []) or [])
        for row in gsc_data.get("top_pages", []) or []:
            if isinstance(row, dict):
                urls.append(row.get("url", ""))
    return _dedupe_strings(urls, 6)


def _default_link_candidates(page_type: str) -> List[str]:
    _u = _get_collection_urls()

    # Sweetsworld-specific keys — present for sweetsworld, absent for other sites
    candy = _u.get("candy", "")
    chocolate = _u.get("chocolate", "")
    wholesale = _u.get("wholesale", "")
    sour = _u.get("sour_lollies", "")

    if candy or chocolate:
        # Sweetsworld-style site: use candy/chocolate/wholesale paths
        if page_type == "landing_page":
            return [u for u in [candy, chocolate, wholesale] if u]
        if page_type == "guide_page":
            return [u for u in [candy, chocolate, sour] if u]
        return [u for u in [candy, chocolate, wholesale] if u]

    # Non-sweetsworld site: use whatever collection URLs are defined (e.g. /services/)
    urls = list(_u.values())
    return [u for u in urls if u][:3]


def _build_internal_links(
    topic_dict: Dict[str, Any],
    gsc_data: Optional[Dict[str, Any]],
    page_type: str,
    selected_products: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    candidate_urls: List[str] = []
    # 同 cluster 已发布页面优先排入（由 run_mvp.py 注入）
    cluster_peers = topic_dict.get("cluster_peer_links") or []
    candidate_urls.extend(str(u) for u in cluster_peers if u)
    candidate_urls.extend(_category_hint_candidates(topic_dict.get("category_hint", "")))
    candidate_urls.extend(_product_link_candidates(selected_products, page_type))
    candidate_urls.extend(_gsc_link_candidates(gsc_data))
    candidate_urls.extend(_default_link_candidates(page_type))
    candidate_urls = _dedupe_strings(candidate_urls, 10)

    candidates: List[Dict[str, str]] = []
    for index, url in enumerate(candidate_urls, 1):
        label = _link_label(url, index)
        link_kind = _link_kind(url)
        variants = _anchor_variants(label, page_type, link_kind)
        anchor_text = variants[(index - 1) % len(variants)]
        candidates.append({"url": url, "label": label, "anchor_text": anchor_text, "link_kind": link_kind})

    selected_links: List[Dict[str, str]] = []
    used_urls = set()
    used_kinds = set()
    for candidate in candidates:
        if candidate["url"] in used_urls or candidate["link_kind"] in used_kinds:
            continue
        used_urls.add(candidate["url"])
        used_kinds.add(candidate["link_kind"])
        selected_links.append(candidate)
        if len(selected_links) >= 3:
            return selected_links

    for candidate in candidates:
        if candidate["url"] in used_urls:
            continue
        used_urls.add(candidate["url"])
        selected_links.append(candidate)
        if len(selected_links) >= 3:
            break
    return selected_links


def _search_intent(page_type: str) -> str:
    mapping = {
        "landing_page": "Transactional with commercial intent",
        "category_page": "Commercial category intent",
        "occasion_page": "Informational with commercial opportunity",
        "guide_page": "Informational",
    }
    return mapping.get(page_type, "Informational")


def _subject_phrase(focus: str, title: str, page_type: str) -> str:
    candidate = _clean_text(focus or title)
    if not candidate:
        return "this range"

    if page_type == "landing_page":
        candidate = re.sub(r"\bwhere to buy\b", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\b(buy|cheap|bulk|online)\b", "", candidate, flags=re.IGNORECASE)
    elif page_type == "guide_page":
        candidate = re.sub(r"^(are|is|can|do|does|what|why|when|which|how)\s+", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\b(halal|vegan|kosher|gluten[- ]free)\b", "", candidate, flags=re.IGNORECASE)

    candidate = re.sub(r"\baustralia\b", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ,:-?")
    return candidate or _clean_text(title) or _clean_text(focus) or "this range"


def _guide_topic_phrase(focus: str, subject: str) -> str:
    cleaned_focus = _clean_text(focus)
    cleaned_subject = _clean_text(subject)
    lowered = cleaned_focus.lower()
    subject_lower = cleaned_subject.lower()

    if lowered.startswith("are ") and cleaned_subject:
        remainder = _clean_text(cleaned_focus[4:])
        if remainder.lower().startswith(subject_lower):
            predicate = _clean_text(remainder[len(cleaned_subject):])
            return f"whether {cleaned_subject} are {predicate}".strip()
        return f"whether {remainder}".strip()

    if lowered.startswith("is ") and cleaned_subject:
        remainder = _clean_text(cleaned_focus[3:])
        if remainder.lower().startswith(subject_lower):
            predicate = _clean_text(remainder[len(cleaned_subject):])
            return f"whether {cleaned_subject} is {predicate}".strip()
        return f"whether {remainder}".strip()

    return cleaned_focus


def _guide_flags(focus: str, title: str) -> Dict[str, bool]:
    haystack = _clean_text(f"{focus} {title}").lower()
    return {
        "alternatives": any(token in haystack for token in ["alternative", "alternatives", "substitute", "replacement"]),
        "availability": any(token in haystack for token in ["where to buy", "availability", "available", "discontinued", "unavailable"]),
        "large_pack": any(token in haystack for token in ["1kg", "2kg", "kg", "bulk", "wholesale", "box", "boxes", "pack", "packs"]),
        "suitability": any(token in haystack for token in ["halal", "vegan", "kosher", "gelatine", "gelatin", "ingredient", "ingredients", "gluten", "allergen"]),
    }


def _is_substitute_guide(page_type: str, focus: str, title: str) -> bool:
    if page_type != "guide_page":
        return False
    flags = _guide_flags(focus, title)
    return flags["alternatives"] or flags["availability"] or flags["large_pack"]


def _is_suitability_guide(page_type: str, focus: str, title: str) -> bool:
    if page_type != "guide_page":
        return False
    flags = _guide_flags(focus, title)
    return flags["suitability"] and not _is_substitute_guide(page_type, focus, title)


def _build_intro(page_type: str, focus: str, subject: str, category: str, title: str = "") -> str:
    if page_type == "landing_page":
        return (
            f"Use this page to compare where to buy {subject} in Australia, what to check before ordering, "
            f"and which {category.lower()} options are the best fit for your basket."
        )
    if page_type == "category_page":
        return (
            f"This page explains the {subject} range, the main product formats to compare, and the next collection "
            f"or product pages worth opening before you buy."
        )
    if page_type == "guide_page":
        if _is_suitability_guide(page_type, focus, title):
            return (
                f"Use this guide to check ingredients, gelatine, and product labelling around {subject}, "
                "then compare the most relevant retail options only if you still need a practical next step."
            )
        if _is_substitute_guide(page_type, focus, title):
            return (
                f"Use this guide if you are trying to find {subject}, compare the closest in-stock alternatives, "
                "or work out whether a small retail bag or a larger bulk pack makes more sense."
            )
        topic_phrase = _guide_topic_phrase(focus, subject)
        return (
            f"Use this guide to understand {topic_phrase}, the key factors to check, and the most sensible next step "
            f"if you need to compare live products or collections."
        )
    return (
        f"This page breaks down {focus} with practical buying guidance, shortlist criteria, and the most useful next "
        f"clicks for the occasion."
    )


def _build_sections(
    page_type: str,
    focus: str,
    subject: str,
    category: str,
    selected_products: List[Dict[str, Any]],
    related_keywords: List[str],
    title: str = "",
) -> List[Dict[str, Any]]:
    shortlist = [
        _clean_text(product.get("product_name") or product.get("name"))
        for product in selected_products[:4]
        if isinstance(product, dict) and _clean_text(product.get("product_name") or product.get("name"))
    ]
    support_points = shortlist or [
        f"Cover supporting search demand around {keyword}." for keyword in related_keywords[:3]
    ] or [f"Clarify how shoppers should compare {subject} before they click through."]

    if page_type == "landing_page":
        return [
            {
                "heading": f"Where to buy {subject} with less guesswork",
                "paragraphs": [
                    f"Landing pages for {subject} need to show real commercial value quickly, including price context, stock clarity, and relevant product paths.",
                    "The goal is to reduce purchase friction rather than publish a thin page that repeats the keyword.",
                ],
                "bullets": support_points,
            },
            {
                "heading": f"How to compare {category} options before ordering",
                "paragraphs": [
                    "A stronger landing page explains the trade-offs between pack size, flavour range, stock depth, and delivery timing.",
                    "That gives the page a conversion job as well as a ranking job.",
                ],
                "bullets": [
                    "Compare unit price instead of headline price alone.",
                    "Check stock, bundle size, and delivery timing together.",
                    "Keep the call to action aligned with the buying task.",
                ],
            },
        ]

    if page_type == "category_page":
        return [
            {
                "heading": f"What defines the {subject} range",
                "paragraphs": [
                    f"A category page for {subject} should explain flavour profile, product format, and the most recognisable options in the range.",
                    "That helps search engines and shoppers understand the scope of the page before they move deeper into the catalogue.",
                ],
                "bullets": support_points,
            },
            {
                "heading": f"How to shop {category} more confidently",
                "paragraphs": [
                    "Category pages should guide users through format, suitability, and value instead of listing products without context.",
                    "This is the section that turns a collection page into a useful SEO landing surface.",
                ],
                "bullets": [
                    "Show best sellers before long-tail variants.",
                    "Explain when bundles make more sense than single items.",
                    "Link into adjacent collections and product pages.",
                ],
            },
        ]

    if page_type == "guide_page":
        if _is_suitability_guide(page_type, focus, title):
            return [
                {
                    "heading": f"What to check before calling {subject} halal",
                    "paragraphs": [
                        f"Queries like '{focus}' need a cautious checklist: ingredient panel, gelatine source, manufacturer labelling, and whether formulas vary by flavour, pack, or market.",
                        "That keeps the page helpful without pretending the guide itself is a certification source.",
                    ],
                    "bullets": [
                        "Check the exact ingredient list for gelatine or other suitability-sensitive additives.",
                        "Verify that the guidance applies to the exact product and market you can buy in Australia.",
                        "Treat old forum answers and generic brand summaries as a starting point, not proof.",
                    ],
                },
                {
                    "heading": f"How to compare in-stock {subject} options without overstating the halal claim",
                    "paragraphs": [
                        "If the halal status is unclear, the safest next step is to compare retail SKUs, review the label details you can actually verify, and keep bulk packs secondary.",
                        f"That lets the page help shoppers use the {category} collection honestly instead of turning a buying guide into a false certification page.",
                    ],
                    "bullets": [
                        "Prefer smaller retail SKUs first so ingredient labels are easier to verify.",
                        "Use the American Candy collection for nearby alternatives rather than treating one SKU as definitive proof.",
                        "Keep live stock links separate from any claim about religious suitability.",
                    ],
                },
            ]
        if _is_substitute_guide(page_type, focus, title):
            return [
                {
                    "heading": f"If you are struggling to find {subject}, start with the closest alternatives",
                    "paragraphs": [
                        f"Searches around {subject} are usually about three practical jobs: checking availability, finding the nearest substitute, and deciding which pack size is worth buying.",
                        "This guide should answer those questions directly instead of padding the page with generic candy-guide copy.",
                    ],
                    "bullets": support_points,
                },
                {
                    "heading": "How to compare close alternatives and pack sizes",
                    "paragraphs": [
                        "Once the substitute path is clear, compare chewiness, chocolate profile, bag size, and whether a wholesale pack is actually justified for the use case.",
                        "That keeps the page useful for both casual buyers and larger orders without mixing it up with a generic category or landing page.",
                    ],
                    "bullets": [
                        "Lead with the closest-match alternatives first.",
                        "Separate small retail bags from 1kg-plus or wholesale options.",
                        "Link to one relevant collection and one representative in-stock product.",
                    ],
                },
            ]
        topic_phrase = _guide_topic_phrase(focus, subject)
        return [
            {
                "heading": f"What to know about {topic_phrase}",
                "paragraphs": [
                    f"Guide pages should frame {topic_phrase} clearly and explain the practical decision points behind the query.",
                    "The page should create enough structure that the next click feels obvious rather than forced.",
                ],
                "bullets": support_points,
            },
            {
                "heading": f"How to evaluate {subject} more confidently",
                "paragraphs": [
                    "Translate the topic into concrete evaluation points such as ingredients, flavour, format, suitability, or buying alternatives.",
                    "Then route readers to the most relevant collection or product pages if they need live stock or substitutes.",
                ],
                "bullets": [
                    "Lead with the comparison dimensions early.",
                    "Surface the best-fit collection or substitute paths.",
                    "Keep FAQs focused on practical next steps.",
                ],
            },
        ]

    # occasion_page — 专属模板：推荐列表 → 选购标准 → 实用提示
    return [
        {
            "heading": f"Top picks for {focus}",
            "paragraphs": [
                f"The best {focus} options balance taste variety, portion size, and suitability for the audience — not just brand recognition.",
                "Lead with products that fit the moment rather than defaulting to generic best-sellers.",
            ],
            "bullets": support_points,
        },
        {
            "heading": f"What to consider when choosing {subject}",
            "paragraphs": [
                "Occasion candy decisions come down to three practical factors: who it is for, how it will be shared, and whether it needs to travel or store well.",
                "Getting these right makes the page more useful than a generic top-ten list.",
            ],
            "bullets": [
                "Match flavour profile and format to the audience (kids, adults, mixed groups).",
                "Choose share-friendly pack sizes over large single-serve bags for group settings.",
                "Check heat sensitivity and packaging if the candy needs to travel or sit out.",
            ],
        },
    ]


def _build_faq_items(page_type: str, focus: str, subject: str, category: str, title: str = "") -> List[Dict[str, str]]:
    if page_type == "landing_page":
        rows = [
            (
                f"Where can I buy {subject} online in Australia?",
                f"Start with Australian stores that show live stock, delivery windows, and product range depth for {subject} before checkout.",
            ),
            (
                f"How should I compare {subject} prices?",
                "Compare unit price, pack size, shipping cost, and bundle options together instead of looking at the headline price only.",
            ),
            (
                f"Are there other {category.lower()} options worth comparing?",
                f"Yes. Nearby collections or substitute products can be useful when {subject} is out of stock or only available in limited pack sizes.",
            ),
        ]
    elif page_type == "guide_page":
        if _is_suitability_guide(page_type, focus, title):
            rows = [
                (
                    f"Do all {subject} products use the same ingredients?",
                    "Not always. Ingredients and suitability guidance can vary by flavour, format, supplier, or market, so the exact pack matters more than a generic brand answer.",
                ),
                (
                    f"Why does gelatine matter when checking whether {subject} are halal?",
                    "Gelatine source can change the halal assessment, so it is one of the first things to verify on the label or through the manufacturer.",
                ),
                (
                    f"Can I still browse {subject} products if the halal status is unclear?",
                    "Yes. Use the collection and product links as shopping references, but treat them separately from any religious-suitability claim until the exact label is verified.",
                ),
            ]
        elif _is_substitute_guide(page_type, focus, title):
            rows = [
                (
                    f"Are {subject} still easy to find in Australia?",
                    f"Availability can change quickly, so the practical approach is to check live stock first and then compare the closest alternatives if {subject} are missing.",
                ),
                (
                    f"What is the closest alternative to {subject}?",
                    "Start with products that match the same chewy, chocolate-coated caramel profile, then compare size, price, and stock depth.",
                ),
                (
                    f"Can I buy {subject}-style lollies in 1kg or bulk packs?",
                    "Usually yes through substitute or lookalike products, but larger packs only make sense if you actually need the volume or lower unit cost.",
                ),
            ]
        else:
            topic_phrase = _guide_topic_phrase(focus, subject)
            rows = [
                (
                    f"What should I check first about {topic_phrase}?",
                    "Start with the ingredient, suitability, or comparison point behind the query before jumping to assumptions based on brand familiarity alone.",
                ),
                (
                    f"Can I still buy alternatives to {subject} if the original is unavailable?",
                    "Yes. Use nearby category and product links to compare substitutes, live stock, and similar formats.",
                ),
                (
                    f"Does this guide help me evaluate {subject} more practically?",
                    "That is the goal. The page should turn the question into a checklist you can actually use before buying or dismissing the product.",
                ),
            ]
    elif page_type == "occasion_page":
        rows = [
            (
                f"How much {category.lower()} do I need for a group?",
                f"A useful rule for group occasions is 100–150 grams of mixed {category.lower()} per person. Adjust up for longer events or younger kids who tend to eat more sweets.",
            ),
            (
                f"What makes {subject} a good choice for this occasion?",
                f"The best {subject} options are easy to share, suit a mixed age group, and come in formats that do not require cutting or portioning before serving.",
            ),
            (
                f"Where can I buy {subject} in bulk online in Australia?",
                f"Australian confectionery stores that stock {category.lower()} in event or bulk packs are the most practical option — compare pack size and delivery timing before ordering.",
            ),
        ]
    else:
        rows = [
            (
                f"What should I look for when choosing {subject}?",
                "Focus on suitability for the use case, flavour profile, pack size, and delivery timing rather than assuming every popular candy is the right fit.",
            ),
            (
                "What is the best next step after reading this page?",
                "Use the linked category or product pages to compare live stock, range depth, and practical buying options.",
            ),
            (
                f"Can this page help me compare {category.lower()} options?",
                "Yes. It should clarify which products or collections are the best fit instead of leaving the reader with generic advice.",
            ),
        ]
    return [{"question": question, "answer": answer} for question, answer in rows]


def _build_cta(page_type: str, focus: str, subject: str, title: str = "") -> Dict[str, str]:
    if page_type == "landing_page":
        return {
            "heading": f"Move from {subject} research into a purchase",
            "body": "Compare the shortlist, then click through to the most relevant collection or product page to check live stock and delivery details.",
        }
    if page_type == "guide_page":
        if _is_suitability_guide(page_type, focus, title):
            return {
                "heading": "Check the label, then compare the closest retail options",
                "body": "Use the guide as a checklist first, then open the American Candy collection or a retail SKU if you want to inspect live stock and packaging details.",
            }
        if _is_substitute_guide(page_type, focus, title):
            return {
                "heading": "Compare close alternatives and pack sizes",
                "body": "Start with the closest substitute, then decide whether a retail bag or larger pack is the better fit before you click through.",
            }
        return {
            "heading": f"Use this guide to decide your next step on {subject}",
            "body": "Review the key checks, then move into the most relevant collection or substitute product pages if you need live buying options.",
        }
    if page_type == "occasion_page":
        return {
            "heading": f"Ready to buy {subject}?",
            "body": f"Pick the format that suits your group size and occasion, then use the product links to check live stock, pack sizes, and delivery timing before you order.",
        }
    return {
        "heading": f"Use this page as a shortlist for {subject}",
        "body": "Review the key options, then move into the linked collection or product pages when you are ready to compare live stock and pricing.",
    }


def build_content_brief(topic_dict: Dict[str, Any], gsc_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    slug = _clean_text(topic_dict.get("slug", "untitled")) or "untitled"
    title = _clean_text(topic_dict.get("title", slug.replace("-", " ").title()))
    focus = _clean_text(topic_dict.get("primary_keyword", title)) or title
    category = _clean_text(topic_dict.get("category_hint", "Confectionery")) or "Confectionery"
    page_type = _clean_text(topic_dict.get("page_type", "occasion_page")) or "occasion_page"
    subject = _subject_phrase(focus, title, page_type)
    selected_products = topic_dict.get("selected_products")
    if not isinstance(selected_products, list):
        selected_products = []

    related_keywords = _extract_related_keywords(gsc_data)

    # ---------------------------------------------------------------------------
    # Delegate to PageTypeStrategy when available (preferred path)
    # Falls back to legacy if/elif templates for existing page types.
    # ---------------------------------------------------------------------------
    if _STRATEGY_REGISTRY_AVAILABLE:
        try:
            strategy_fields = build_brief_from_strategy(topic_dict, gsc_data)
            sections = strategy_fields["sections"]
            faq_items = strategy_fields["faq_items"]
            meta_description = _trim_text(strategy_fields["meta_description"], 155)
            intro = _trim_text(strategy_fields["intro"], 240)
            search_intent = strategy_fields["search_intent"]
            cta = strategy_fields["cta"]
            distribution_channels = strategy_fields.get("distribution_channels", [])
            schema_types = strategy_fields.get("schema_types", [])
        except Exception as exc:
            logger.warning(f"Strategy registry failed for '{page_type}', falling back to templates: {exc}")
            sections, faq_items, meta_description, intro, search_intent, cta, distribution_channels, schema_types = _legacy_brief_fields(
                page_type, focus, subject, category, selected_products, related_keywords, title
            )
    else:
        sections, faq_items, meta_description, intro, search_intent, cta, distribution_channels, schema_types = _legacy_brief_fields(
            page_type, focus, subject, category, selected_products, related_keywords, title
        )

    brief = {
        "brief_id": f"{slug}-brief-v1",
        "slug": slug,
        "keyword": focus,
        "search_intent": search_intent,
        "page_type": page_type,
        "title": title,
        "meta_description": meta_description,
        "intro": intro,
        "outline": [section.get("heading", "") for section in sections if section.get("heading")],
        "sections": sections,
        "faq_items": faq_items,
        "faq_questions": [item["question"] for item in faq_items],
        "internal_links": _build_internal_links(topic_dict, gsc_data, page_type, selected_products),
        "selected_products": selected_products,
        "related_keywords": related_keywords,
        "cta": cta,
    }
    # Attach distribution/schema metadata so downstream consumers can read them
    if distribution_channels:
        brief["distribution_channels"] = distribution_channels
    if schema_types:
        brief["schema_types"] = schema_types
    return brief


def _legacy_brief_fields(
    page_type: str,
    focus: str,
    subject: str,
    category: str,
    selected_products: List[Dict[str, Any]],
    related_keywords: List[str],
    title: str,
) -> tuple:
    """Return (sections, faq_items, meta_description, intro, search_intent, cta, distribution_channels, schema_types)
    using the original if/elif template logic — preserved as the fallback path.
    """
    sections = _build_sections(page_type, focus, subject, category, selected_products, related_keywords, title=title)
    faq_items = _build_faq_items(page_type, focus, subject, category, title=title)
    if _is_suitability_guide(page_type, focus, title):
        meta_description = _trim_text(
            f"{title}. Check ingredients, gelatine, and label details before deciding whether {subject} is suitable, then compare the closest retail options in Australia.",
            155,
        )
    elif _is_substitute_guide(page_type, focus, title):
        meta_description = _trim_text(
            f"{title}. Compare live alternatives, retail versus bulk pack sizes, and the most relevant in-stock options for {subject} in Australia.",
            155,
        )
    else:
        meta_description = _trim_text(
            f"{title}. Compare stock options, buying factors, and the best next steps for {subject} in Australia.",
            155,
        )
    intro = _trim_text(_build_intro(page_type, focus, subject, category, title=title), 240)
    search_intent = _search_intent(page_type)
    cta = _build_cta(page_type, focus, subject, title=title)
    distribution_channels: List[str] = []
    schema_types: List[str] = []
    return sections, faq_items, meta_description, intro, search_intent, cta, distribution_channels, schema_types


def save_content_brief(output_dir: Path, brief: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = _clean_text(brief.get("slug", "untitled")) or "untitled"
    path = output_dir / f"{slug}_brief.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(brief, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)
    return path
