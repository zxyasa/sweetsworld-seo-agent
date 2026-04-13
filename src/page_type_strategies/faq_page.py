"""Strategy for faq_page — dedicated FAQ / Q&A answer pages.

These pages target question-based queries and are optimised for AI answer engines
(SGE, Perplexity, ChatGPT) as well as Featured Snippets.
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


class FAQPageStrategy(PageTypeStrategy):
    type_id = "faq_page"
    display_name = "FAQ Page (Answer Engine Optimised)"

    def search_intent(self) -> str:
        return "Informational — question answering"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "FAQPage"]

    def distribution_channels(self) -> List[str]:
        return ["facebook", "pinterest"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=300,
            required_faq=True,
            min_faq_items=5,
            required_products=False,
            required_schema_types=["BreadcrumbList", "FAQPage"],
        )

    def build_intro(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"This page answers the most common questions about {focus} clearly and concisely, "
            "so you can compare options, check suitability, and decide your next step without guesswork.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        cat = ctx.category_hint or _get_profile().default_category
        return [
            {
                "heading": f"Quick answers about {focus}",
                "paragraphs": [
                    f"The questions below cover the most common things people want to know about {subject} before buying or comparing options in Australia.",
                    "Each answer is kept short and direct so you can move to the right next step quickly.",
                ],
                "bullets": [
                    f"What {subject} is and how it compares to similar products.",
                    "Suitability for dietary requirements (halal, vegan, allergen).",
                    "Where to buy, pack sizes available, and delivery options.",
                ],
            },
            {
                "heading": f"What to do after reading these {cat} Q&As",
                "paragraphs": [
                    "Once you have the answer you need, use the category and product links to check live stock and pricing.",
                    "The FAQ is a starting point — the product pages give you the detail you need to buy with confidence.",
                ],
                "bullets": [
                    "Browse the full range if you need to compare more options.",
                    "Check pack sizes and delivery before committing to a bulk order.",
                    "Use the internal links to move into related guides or collections.",
                ],
            },
        ]

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        """Generate 5+ FAQ pairs for the topic. These are the core content of this page type."""
        subject = self.subject_phrase(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        profile = _get_profile()
        area = profile.area_served

        # Detect site type from profile: candy/confectionery sites get ingredient FAQs,
        # service/business sites get service-oriented FAQs.
        _is_product_site = any(
            term in (profile.default_category or "").lower()
            for term in ("candy", "confectionery", "food", "snack", "lolly", "chocolate")
        )

        base_faqs = [
            {
                "question": f"What is {subject}?",
                "answer": f"{subject.capitalize()} is a {cat} option available in {area}. It comes in various formats depending on the provider or brand.",
            },
            {
                "question": f"Where can I find {subject} in {area}?",
                "answer": f"Search for trusted {area} {cat} providers that offer {subject}. Compare credentials, reviews, and pricing before committing.",
            },
            {
                "question": f"How do I choose the right {subject}?",
                "answer": f"Start by identifying your specific needs, then compare {cat} providers in {area} on experience, price, and track record.",
            },
            {
                "question": f"Is {subject} available for businesses in {area}?",
                "answer": f"Yes. Many {area} {cat} providers cater to both individuals and businesses. Check whether volume pricing or service packages are available.",
            },
            {
                "question": f"What should I look for in a {subject} provider?",
                "answer": f"Key factors include relevant experience, transparent pricing, local knowledge of {area}, and clear communication throughout the engagement.",
            },
        ]

        if _is_product_site:
            # Add ingredient/dietary FAQs for candy/food sites
            base_faqs += [
                {
                    "question": f"Is {subject} halal?",
                    "answer": f"Halal status for {subject} depends on the exact product and formulation. Check the ingredient list for gelatine and look for certification on the packaging.",
                },
                {
                    "question": f"Is {subject} vegan?",
                    "answer": f"Vegan suitability varies by product. Check for gelatine, milk derivatives, and artificial colourants on the label.",
                },
                {
                    "question": f"Does {subject} come in bulk or wholesale packs?",
                    "answer": f"Many {area} retailers offer {subject} in bulk or wholesale cartons — practical for events or businesses buying at volume.",
                },
            ]

        return base_faqs

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        return {
            "heading": f"Still have questions about {subject}?",
            "body": "Browse the full product range or related guides to find the answer you need and compare live stock before buying.",
            "button_text": "Browse Products",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        return self._trim(
            f"{ctx.title}. Quick answers about ingredients, suitability, where to buy, and alternatives for {focus} in Australia.",
            155,
        )
