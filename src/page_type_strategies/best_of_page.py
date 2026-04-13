"""Strategy for best_of_page — 'Best X in Australia' curated list pages.

These pages target 'best X', 'top X', 'popular X in Australia' queries.
Strong commercial intent with editorial framing.
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


class BestOfPageStrategy(PageTypeStrategy):
    type_id = "best_of_page"
    display_name = "Best-Of Page (Curated Top List)"

    def search_intent(self) -> str:
        return "Commercial investigation — curated recommendations"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "ItemList", "FAQPage"]

    def distribution_channels(self) -> List[str]:
        return ["facebook", "instagram", "pinterest"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=500,
            required_faq=True,
            required_products=True,
            min_faq_items=3,
            min_products=5,
            required_schema_types=["BreadcrumbList", "ItemList"],
        )

    def build_intro(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"This page lists the best {focus} available in Australia right now — curated by popularity, "
            "flavour variety, pack size options, and suitability for different buyers. "
            "Each pick is linked to live stock so you can check availability before ordering.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        cat = ctx.category_hint or _get_profile().default_category
        products = self.product_shortlist(ctx, max_items=8)
        top_picks = products[:5] if products else [
            f"Top pick 1 — {subject} (classic flavour)",
            f"Top pick 2 — {subject} (bulk pack)",
            f"Top pick 3 — {subject} (premium range)",
            f"Top pick 4 — {subject} (novelty / seasonal)",
            f"Top pick 5 — {subject} (budget option)",
        ]
        return [
            {
                "heading": f"The best {focus} in Australia right now",
                "paragraphs": [
                    f"The list below prioritises {cat} options that are reliably available in {_get_profile().area_served}, covering a range of formats and price points for different needs.",
                    "Each option is selected on practical merit, not brand familiarity alone.",
                ],
                "bullets": top_picks,
            },
            {
                "heading": f"How to pick the right {subject} for your needs",
                "paragraphs": [
                    "The best pick depends on three questions: who it is for, how much you need, and whether dietary requirements apply.",
                    "Use these criteria to narrow the list before clicking through to check stock.",
                ],
                "bullets": [
                    "For gifts: choose variety packs or premium single-brand selections.",
                    "For events: compare 1kg bags or wholesale cartons for the best unit price.",
                    "For dietary needs: filter by halal, vegan, or allergen-free options first.",
                ],
            },
            {
                "heading": f"What makes a great {cat} option in Australia?",
                "paragraphs": [
                    "Flavour accuracy, consistent stock, clear ingredient labelling, and fair unit pricing are the practical markers of a well-chosen product.",
                    "Novelty and packaging matter less than whether the product will actually be available when you order.",
                ],
                "bullets": [
                    "Check stock reliability — some imports have long lead times or go out of stock frequently.",
                    "Compare unit price across pack sizes before buying the largest available option.",
                    "Read ingredient labels if suitability for halal, vegan, or allergen requirements matters.",
                ],
            },
        ]

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        return [
            {
                "question": f"What is the best {subject} to buy in Australia?",
                "answer": f"The best {subject} depends on your use case. For everyday snacking, choose a reliable mid-range option with good flavour. For gifts or events, pick a variety pack or a premium selection with strong presentation.",
            },
            {
                "question": f"Where can I buy the best {subject} online in Australia?",
                "answer": f"Trusted {_get_profile().area_served} {cat} providers typically offer the widest range and reliable turnaround. Compare availability and pricing before ordering.",
            },
            {
                "question": f"Are the best {subject} options suitable for dietary requirements?",
                "answer": f"Suitability varies by product and brand. Check each product's ingredient list for gelatine, dairy, nuts, and artificial colourants if halal, vegan, or allergen status matters.",
            },
            {
                "question": f"Can I buy the best {subject} in bulk or wholesale quantities?",
                "answer": f"Yes. Many top-rated {cat} products are available in 1kg bags, cartons, or wholesale packs. Bulk options make sense for events, gifting, or businesses buying at volume.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        return {
            "heading": f"Find your favourite {subject}",
            "body": "Use the product links to check live stock, compare pack sizes, and add your shortlist to cart before they sell out.",
            "button_text": "Shop Best Sellers",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"{ctx.title}. Curated list of the best {focus} available in Australia with buying tips, pack sizes, and live stock links.",
            155,
        )
