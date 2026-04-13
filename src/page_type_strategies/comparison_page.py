"""Strategy for comparison_page — product/brand/option comparison pages.

These pages target 'X vs Y', 'best X brands', 'compare X options' queries.
They serve commercial-investigation intent and are strong AIO citation candidates.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import BriefContext, PageTypeStrategy, QualityGate
try:
    from content_generator import _profile as _get_profile
except ImportError:
    def _get_profile():  # type: ignore
        class _FallbackProfile:
            default_category = "confectionery"
        return _FallbackProfile()


class ComparisonPageStrategy(PageTypeStrategy):
    type_id = "comparison_page"
    display_name = "Comparison Page (X vs Y / Best Brands)"

    def search_intent(self) -> str:
        return "Commercial investigation — compare before buying"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "ItemList", "FAQPage"]

    def distribution_channels(self) -> List[str]:
        return ["pinterest", "facebook", "x"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=500,
            required_faq=True,
            required_products=True,
            min_faq_items=3,
            min_products=3,
            min_comparison_items=3,
            required_schema_types=["BreadcrumbList", "ItemList"],
        )

    def build_intro(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"This page compares the main {focus} options available in Australia — covering ingredients, pack sizes, "
            "pricing, and suitability — so you can make a confident buying decision without visiting multiple product pages.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        cat = ctx.category_hint or _get_profile().default_category
        items = ctx.comparison_items or self.product_shortlist(ctx, max_items=6)
        comparison_bullets = items[:5] if items else [
            f"Brand A — {subject} (standard size)",
            f"Brand B — {subject} (bulk pack)",
            f"Brand C — {subject} (premium range)",
        ]
        return [
            {
                "heading": f"How to compare {focus} options",
                "paragraphs": [
                    f"When comparing {subject} products, focus on flavour match, pack size value, ingredient differences, and whether stock is reliably available in Australia.",
                    "Avoid making a decision on brand name alone — the best option depends on your specific use case.",
                ],
                "bullets": comparison_bullets,
            },
            {
                "heading": f"What makes one {cat} option better than another?",
                "paragraphs": [
                    "The comparison dimensions that matter most are: taste profile match, pack size vs cost efficiency, halal / vegan suitability, and shipping reliability.",
                    "A quick side-by-side of these factors saves more time than reading every product description individually.",
                ],
                "bullets": [
                    "Compare unit price across pack sizes, not just headline price.",
                    "Check ingredient lists if suitability (halal, vegan) matters for your audience.",
                    "Prioritise options with reliable Australian stock over imported alternatives with long lead times.",
                ],
            },
            {
                "heading": "Verdict: which option fits your needs?",
                "paragraphs": [
                    "There is no single best option — the right choice depends on quantity needed, budget, and whether specific dietary requirements apply.",
                    "Use the product links below to check live stock and confirm pricing before making a final decision.",
                ],
                "bullets": [
                    "For small quantities: choose the retail single bag for lowest commitment.",
                    "For events or groups: compare 1kg bags or bulk cartons for better unit pricing.",
                    "For dietary requirements: verify the label directly — don't rely on general brand claims.",
                ],
            },
        ]

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        return [
            {
                "question": f"Which {subject} brand is best in Australia?",
                "answer": f"The best {subject} brand depends on your priorities. Compare flavour, pack size, price per gram, and stock availability rather than defaulting to the most recognisable name.",
            },
            {
                "question": f"What is the key difference between {subject} options?",
                "answer": f"The main differences are usually ingredient formulation (affecting taste and suitability), pack size range, and whether the product is consistently in stock at Australian retailers.",
            },
            {
                "question": f"Can I buy {subject} in bulk for events or wholesale?",
                "answer": f"Yes. Many Australian {cat} stores stock 1kg bags, cartons, or wholesale packs. Compare unit price and minimum order before committing to a bulk purchase.",
            },
            {
                "question": f"Are all {subject} options halal or vegan?",
                "answer": f"Not necessarily. Halal and vegan status varies by brand and formulation. Always check the specific product label for gelatine, dairy, and colouring agents.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        return {
            "heading": f"Ready to choose your {subject}?",
            "body": "Use the product links to compare live stock, exact pricing, and ingredient details before you add to cart.",
            "button_text": "Compare Products",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"{ctx.title}. Compare options, ingredients, pack sizes, and pricing for {focus} available in Australia.",
            155,
        )
