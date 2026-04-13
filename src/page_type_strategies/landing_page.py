"""Strategy for landing_page — commercial 'where to buy' pages."""
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


class LandingPageStrategy(PageTypeStrategy):
    type_id = "landing_page"
    display_name = "Landing Page (Where to Buy)"

    def search_intent(self) -> str:
        return "Transactional with commercial intent"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "ItemList"]

    def distribution_channels(self) -> List[str]:
        return ["facebook", "instagram", "gbp", "pinterest"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=350,
            required_faq=False,
            required_products=True,
            min_products=1,
            required_schema_types=["BreadcrumbList", "ItemList"],
        )

    def build_intro(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or "Confectionery").lower()
        return self._trim(
            f"Use this page to compare where to buy {subject} in Australia, what to check before ordering, "
            f"and which {cat} options are the best fit for your basket.",
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
                "heading": f"Where to buy {subject} with less guesswork",
                "paragraphs": [
                    f"Landing pages for {subject} need to show real commercial value quickly, including price context, stock clarity, and relevant product paths.",
                    "The goal is to reduce purchase friction rather than publish a thin page that repeats the keyword.",
                ],
                "bullets": support_points,
            },
            {
                "heading": f"How to compare {cat} options before ordering",
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

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        return [
            {
                "question": f"Where can I buy {subject} online in Australia?",
                "answer": f"Start with Australian stores that show live stock, delivery windows, and product range depth for {subject} before checkout.",
            },
            {
                "question": f"How should I compare {subject} prices?",
                "answer": "Compare unit price, pack size, shipping cost, and bundle options together instead of looking at the headline price only.",
            },
            {
                "question": f"Are there other {cat} options worth comparing?",
                "answer": f"Yes. Nearby collections or substitute products can be useful when {subject} is out of stock or only available in limited pack sizes.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        return {
            "heading": f"Move from {subject} research into a purchase",
            "body": "Compare the shortlist, then click through to the most relevant collection or product page to check live stock and delivery details.",
            "button_text": "Browse Related Collection",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        return self._trim(
            f"{ctx.title}. Compare stock options, buying factors, and the best next steps for {subject} in Australia.",
            155,
        )
