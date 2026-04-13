"""Strategy for occasion_page — gift/event/seasonal use-case pages."""
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


class OccasionPageStrategy(PageTypeStrategy):
    type_id = "occasion_page"
    display_name = "Occasion Page (Gift / Event)"

    def search_intent(self) -> str:
        return "Informational with commercial opportunity"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "ItemList"]

    def distribution_channels(self) -> List[str]:
        return ["facebook", "instagram", "gbp", "pinterest", "x"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=350,
            required_faq=True,
            required_products=True,
            min_products=2,
            min_faq_items=3,
            required_schema_types=["BreadcrumbList"],
        )

    def build_intro(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"This page breaks down {focus} with practical buying guidance, shortlist criteria, and the most useful next "
            "clicks for the occasion.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        support_points = self.product_shortlist(ctx) or [
            f"Cover supporting search demand around {subject}."
        ]
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

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        return [
            {
                "question": f"How much {cat} do I need for a group?",
                "answer": f"A useful rule for group occasions is 100–150 grams of mixed {cat} per person. Adjust up for longer events or younger kids who tend to eat more sweets.",
            },
            {
                "question": f"What makes {subject} a good choice for this occasion?",
                "answer": f"The best {subject} options are easy to share, suit a mixed age group, and come in formats that do not require cutting or portioning before serving.",
            },
            {
                "question": f"Where can I buy {subject} in bulk online in Australia?",
                "answer": f"Trusted {_get_profile().area_served} {cat} providers that offer event or bulk options are the most practical choice — compare pack size and availability before ordering.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        return {
            "heading": f"Ready to buy {subject}?",
            "body": "Pick the format that suits your group size and occasion, then use the product links to check live stock, pack sizes, and delivery timing before you order.",
            "button_text": "Shop Now",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        return self._trim(
            f"{ctx.title}. Compare stock options, buying factors, and the best next steps for {subject} in Australia.",
            155,
        )
