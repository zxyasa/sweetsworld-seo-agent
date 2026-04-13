"""Strategy for guide_page — informational guides (suitability, substitute, general)."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .base import BriefContext, PageTypeStrategy, QualityGate


def _guide_flags(keyword: str, title: str) -> Dict[str, bool]:
    haystack = (keyword + " " + title).lower()
    return {
        "alternatives": any(t in haystack for t in ["alternative", "alternatives", "substitute", "replacement"]),
        "availability": any(t in haystack for t in ["where to buy", "availability", "available", "discontinued", "unavailable"]),
        "large_pack": any(t in haystack for t in ["1kg", "2kg", "kg", "bulk", "wholesale", "box", "boxes", "pack", "packs"]),
        "suitability": any(t in haystack for t in ["halal", "vegan", "kosher", "gelatine", "gelatin", "ingredient", "ingredients", "gluten", "allergen"]),
    }


class GuidePageStrategy(PageTypeStrategy):
    type_id = "guide_page"
    display_name = "Guide Page (Informational)"

    def search_intent(self) -> str:
        return "Informational"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "FAQPage"]

    def distribution_channels(self) -> List[str]:
        return ["pinterest", "facebook"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=400,
            required_faq=True,
            required_products=False,
            min_faq_items=3,
            required_schema_types=["BreadcrumbList", "FAQPage"],
        )

    def _is_suitability(self, ctx: BriefContext) -> bool:
        flags = _guide_flags(ctx.primary_keyword, ctx.title)
        return flags["suitability"] and not self._is_substitute(ctx)

    def _is_substitute(self, ctx: BriefContext) -> bool:
        flags = _guide_flags(ctx.primary_keyword, ctx.title)
        return flags["alternatives"] or flags["availability"] or flags["large_pack"]

    def _topic_phrase(self, focus: str, subject: str) -> str:
        lowered = focus.lower()
        if lowered.startswith("are "):
            remainder = focus[4:].strip()
            if remainder.lower().startswith(subject.lower()):
                predicate = remainder[len(subject):].strip()
                return f"whether {subject} are {predicate}".strip()
            return f"whether {remainder}".strip()
        if lowered.startswith("is "):
            remainder = focus[3:].strip()
            if remainder.lower().startswith(subject.lower()):
                predicate = remainder[len(subject):].strip()
                return f"whether {subject} is {predicate}".strip()
            return f"whether {remainder}".strip()
        return focus

    def build_intro(self, ctx: BriefContext) -> str:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        if self._is_suitability(ctx):
            return self._trim(
                f"Use this guide to check ingredients, gelatine, and product labelling around {subject}, "
                "then compare the most relevant retail options only if you still need a practical next step.",
                240,
            )
        if self._is_substitute(ctx):
            return self._trim(
                f"Use this guide if you are trying to find {subject}, compare the closest in-stock alternatives, "
                "or work out whether a small retail bag or a larger bulk pack makes more sense.",
                240,
            )
        topic_phrase = self._topic_phrase(focus, subject)
        return self._trim(
            f"Use this guide to understand {topic_phrase}, the key factors to check, and the most sensible next step "
            "if you need to compare live products or collections.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)
        cat = ctx.category_hint or "Confectionery"
        support_points = self.product_shortlist(ctx) or [
            f"Cover supporting search demand around {focus}."
        ]

        if self._is_suitability(ctx):
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
                        f"That lets the page help shoppers use the {cat} collection honestly instead of turning a buying guide into a false certification page.",
                    ],
                    "bullets": [
                        "Prefer smaller retail SKUs first so ingredient labels are easier to verify.",
                        "Use the American Candy collection for nearby alternatives rather than treating one SKU as definitive proof.",
                        "Keep live stock links separate from any claim about religious suitability.",
                    ],
                },
            ]

        if self._is_substitute(ctx):
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

        topic_phrase = self._topic_phrase(focus, subject)
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

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        focus = self._clean(ctx.primary_keyword or ctx.title)
        subject = self.subject_phrase(ctx)

        if self._is_suitability(ctx):
            return [
                {
                    "question": f"Do all {subject} products use the same ingredients?",
                    "answer": "Not always. Ingredients and suitability guidance can vary by flavour, format, supplier, or market, so the exact pack matters more than a generic brand answer.",
                },
                {
                    "question": f"Why does gelatine matter when checking whether {subject} are halal?",
                    "answer": "Gelatine source can change the halal assessment, so it is one of the first things to verify on the label or through the manufacturer.",
                },
                {
                    "question": f"Can I still browse {subject} products if the halal status is unclear?",
                    "answer": "Yes. Use the collection and product links as shopping references, but treat them separately from any religious-suitability claim until the exact label is verified.",
                },
            ]

        if self._is_substitute(ctx):
            return [
                {
                    "question": f"Are {subject} still easy to find in Australia?",
                    "answer": f"Availability can change quickly, so the practical approach is to check live stock first and then compare the closest alternatives if {subject} are missing.",
                },
                {
                    "question": f"What is the closest alternative to {subject}?",
                    "answer": "Start with products that match the same chewy, chocolate-coated caramel profile, then compare size, price, and stock depth.",
                },
                {
                    "question": f"Can I buy {subject}-style lollies in 1kg or bulk packs?",
                    "answer": "Usually yes through substitute or lookalike products, but larger packs only make sense if you actually need the volume or lower unit cost.",
                },
            ]

        topic_phrase = self._topic_phrase(focus, subject)
        return [
            {
                "question": f"What should I check first about {topic_phrase}?",
                "answer": "Start with the ingredient, suitability, or comparison point behind the query before jumping to assumptions based on brand familiarity alone.",
            },
            {
                "question": f"Can I still buy alternatives to {subject} if the original is unavailable?",
                "answer": "Yes. Use nearby category and product links to compare substitutes, live stock, and similar formats.",
            },
            {
                "question": f"Does this guide help me evaluate {subject} more practically?",
                "answer": "That is the goal. The page should turn the question into a checklist you can actually use before buying or dismissing the product.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        focus = self._clean(ctx.primary_keyword or ctx.title)
        if self._is_suitability(ctx):
            return {
                "heading": "Check the label, then compare the closest retail options",
                "body": "Use the guide as a checklist first, then open the American Candy collection or a retail SKU if you want to inspect live stock and packaging details.",
                "button_text": "Browse Collection",
            }
        if self._is_substitute(ctx):
            return {
                "heading": "Compare close alternatives and pack sizes",
                "body": "Start with the closest substitute, then decide whether a retail bag or larger pack is the better fit before you click through.",
                "button_text": "Compare Options",
            }
        return {
            "heading": f"Use this guide to decide your next step on {subject}",
            "body": "Review the key checks, then move into the most relevant collection or substitute product pages if you need live buying options.",
            "button_text": "Explore Related Products",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        if self._is_suitability(ctx):
            return self._trim(
                f"{ctx.title}. Check ingredients, gelatine, and label details before deciding whether {subject} is suitable, then compare the closest retail options in Australia.",
                155,
            )
        if self._is_substitute(ctx):
            return self._trim(
                f"{ctx.title}. Compare live alternatives, retail versus bulk pack sizes, and the most relevant in-stock options for {subject} in Australia.",
                155,
            )
        return self._trim(
            f"{ctx.title}. Compare stock options, buying factors, and the best next steps for {subject} in Australia.",
            155,
        )
