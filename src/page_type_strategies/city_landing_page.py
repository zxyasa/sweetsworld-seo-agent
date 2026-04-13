"""Strategy for city_landing_page — local 'buy X in [City]' pages.

Targets local commercial queries. Strong GBP signal. Includes LocalBusiness schema.
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


class CityLandingPageStrategy(PageTypeStrategy):
    type_id = "city_landing_page"
    display_name = "City Landing Page (Local Commercial)"

    def search_intent(self) -> str:
        return "Local transactional — buy near me / in [city]"

    def schema_types(self) -> List[str]:
        return ["BreadcrumbList", "LocalBusiness"]

    def distribution_channels(self) -> List[str]:
        return ["gbp", "facebook"]

    def quality_gate(self) -> QualityGate:
        return QualityGate(
            min_words=400,
            required_faq=True,
            required_products=False,
            min_faq_items=3,
            required_local_signal=True,
            required_schema_types=["BreadcrumbList", "LocalBusiness"],
        )

    def _city(self, ctx: BriefContext) -> str:
        if ctx.city:
            return ctx.city
        # Try to extract from keyword or title
        for text in [ctx.primary_keyword, ctx.title]:
            import re
            m = re.search(r'\b(Sydney|Melbourne|Brisbane|Perth|Adelaide|Canberra|Darwin|Hobart|Newcastle|Gold Coast|Wollongong|Geelong)\b', text, re.IGNORECASE)
            if m:
                return m.group(1)
        return "your city"

    def build_intro(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        city = self._city(ctx)
        return self._trim(
            f"This page covers {subject} in {city} — availability, delivery options, "
            f"and which {(ctx.category_hint or _get_profile().default_category).lower()} options are reliably available for {city} residents.",
            240,
        )

    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        subject = self.subject_phrase(ctx)
        city = self._city(ctx)
        cat = ctx.category_hint or _get_profile().default_category
        products = self.product_shortlist(ctx, max_items=4)
        return [
            {
                "heading": f"Where to buy {subject} in {city}",
                "paragraphs": [
                    f"People in {city} can access {subject} from {_get_profile().area_served} {cat} providers with reliable service coverage.",
                    "Most orders are dispatched from Australian warehouses, which means shorter lead times compared to international shipping.",
                ],
                "bullets": products or [
                    f"Compare same-day or next-day delivery options available to {city}.",
                    "Check minimum order values for free shipping to your postcode.",
                    "Bulk packs and wholesale options are often available without surcharges.",
                ],
            },
            {
                "heading": f"Why {city} shoppers choose Australian online stores for {cat}",
                "paragraphs": [
                    f"Online {cat} stores serving {city} typically offer a wider range than local retailers, with better stock depth and competitive unit pricing across pack sizes.",
                    "That makes them practical for both individual buyers and anyone ordering for an event, party, or business.",
                ],
                "bullets": [
                    f"Wider range than physical stores in {city}.",
                    "Compare unit price across pack sizes before committing to a bulk order.",
                    "Check delivery timing — most orders reach {city} within 2–5 business days.".replace("{city}", city),
                ],
            },
            {
                "heading": f"What to check before ordering {subject} to {city}",
                "paragraphs": [
                    "Before placing an order, confirm the retailer ships to your exact postcode, check whether a minimum order applies, and compare delivery windows if timing matters.",
                    "Some specialty or imported items may have longer lead times or lower stock depth — it is worth checking availability before finalising.",
                ],
                "bullets": [
                    "Confirm postcode eligibility before selecting delivery options.",
                    "Compare pack sizes and unit price if you are buying for an event.",
                    "Check ingredient labels if dietary requirements apply to your order.",
                ],
            },
        ]

    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        subject = self.subject_phrase(ctx)
        city = self._city(ctx)
        cat = (ctx.category_hint or _get_profile().default_category).lower()
        return [
            {
                "question": f"Can I get {subject} delivered to {city}?",
                "answer": f"Yes. {_get_profile().area_served} {cat} providers typically service {city} and surrounding areas. Check availability and lead times before committing.",
            },
            {
                "question": f"How long does {subject} delivery take to {city}?",
                "answer": f"Most Australian orders reach {city} within 2–5 business days. Express options may be available — check the retailer's shipping page for current lead times.",
            },
            {
                "question": f"Where can I buy {subject} in bulk in {city}?",
                "answer": f"Online stores serving {city} usually stock {subject} in 1kg bags, cartons, and wholesale quantities. Compare unit price and delivery cost before ordering large quantities.",
            },
            {
                "question": f"Do online stores in Australia ship {cat} to {city} for free?",
                "answer": f"Many stores offer free delivery to {city} above a minimum order threshold. Compare options — the free shipping minimum is often lower than a physical retail trip's full cost.",
            },
        ]

    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        subject = self.subject_phrase(ctx)
        city = self._city(ctx)
        return {
            "heading": f"Order {subject} to {city}",
            "body": "Browse the product range, compare pack sizes and delivery options, then order with confidence from an Australian store.",
            "button_text": f"Shop & Deliver to {city}",
        }

    def build_meta_description(self, ctx: BriefContext) -> str:
        subject = self.subject_phrase(ctx)
        city = self._city(ctx)
        cat = (
            (ctx.extra or {}).get("category")
            or ctx.category_hint
            or _get_profile().default_category
        ).lower()
        return self._trim(
            f"{ctx.title}. Find {subject} in {city}. Compare options, pricing, and availability from trusted {_get_profile().area_served} {cat} providers.",
            155,
        )
