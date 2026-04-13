"""Strategy for category_page — educational range overview pages."""
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


class CategoryPageStrategy(PageTypeStrategy):
    type_id = "category_page"
    display_name = "Category Page (Range Overview)"

    def search_intent(self) -> str:
        return "Commercial category intent"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList"]

    def distribution_channels(self) -> List[str]:
        return ["pinterest", "facebook"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=250,
            required_faq=False,
            required_products=False,
            required_schema_types=["BreadcrumbList"],
        )

    def build_intro(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        return self._trim(
            f"This page explains the {subject} range, the main product formats to compare, and the next collection "
            "or product pages worth opening before you buy.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        subject = self.subject_phrase(ctx)
        cat = ctx.category_hint or "Confectionery"
        support_points = self.product_shortlist(ctx) or [
            f"Cover supporting search demand around {subject}."
        ]
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
                "heading": f"How to shop {cat} more confidently",
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

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        return [
            {
                "question": f"What should I look for when choosing {subject}?",
                "answer": "Focus on suitability for the use case, flavour profile, pack size, and delivery timing rather than assuming every popular candy is the right fit.",
            },
            {
                "question": "What is the best next step after reading this page?",
                "answer": "Use the linked category or product pages to compare live stock, range depth, and practical buying options.",
            },
            {
                "question": f"Can this page help me compare {cat} options?",
                "answer": "Yes. It should clarify which products or collections are the best fit instead of leaving the reader with generic advice.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        return {
            "heading": f"Use this page as a shortlist for {subject}",
            "body": "Review the key options, then move into the linked collection or product pages when you are ready to compare live stock and pricing.",
            "button_text": "Browse Collection",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        return self._trim(
            f"{ctx.title}. Compare stock options, buying factors, and the best next steps for {subject} in Australia.",
            155,
        )
