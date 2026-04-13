"""Page type registry — maps type IDs to strategy instances.

Usage:
    from page_type_registry import get_strategy, PAGE_TYPE_REGISTRY

    strategy = get_strategy("guide_page")
    intro = strategy.build_intro(ctx)
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from page_type_strategies.base import BriefContext, PageTypeStrategy, QualityGate
from page_type_strategies.landing_page import LandingPageStrategy
from page_type_strategies.category_page import CategoryPageStrategy
from page_type_strategies.occasion_page import OccasionPageStrategy
from page_type_strategies.guide_page import GuidePageStrategy
from page_type_strategies.faq_page import FAQPageStrategy
from page_type_strategies.comparison_page import ComparisonPageStrategy
from page_type_strategies.best_of_page import BestOfPageStrategy
from page_type_strategies.city_landing_page import CityLandingPageStrategy

logger = logging.getLogger(__name__)

# Single source of truth: all registered page type strategies
PAGE_TYPE_REGISTRY: Dict[str, PageTypeStrategy] = {
    "landing_page":      LandingPageStrategy(),
    "category_page":     CategoryPageStrategy(),
    "occasion_page":     OccasionPageStrategy(),
    "guide_page":        GuidePageStrategy(),
    "faq_page":          FAQPageStrategy(),
    "comparison_page":   ComparisonPageStrategy(),
    "best_of_page":      BestOfPageStrategy(),
    "city_landing_page": CityLandingPageStrategy(),
}

_FALLBACK_STRATEGY = OccasionPageStrategy()


def get_strategy(page_type: str) -> PageTypeStrategy:
    """Return the strategy for a page type. Falls back to occasion_page with a warning."""
    strategy = PAGE_TYPE_REGISTRY.get(page_type)
    if strategy is None:
        logger.warning(f"Unknown page_type '{page_type}' — using fallback strategy (occasion_page)")
        return _FALLBACK_STRATEGY
    return strategy


def list_page_types() -> list[str]:
    return list(PAGE_TYPE_REGISTRY.keys())


def is_valid_page_type(page_type: str) -> bool:
    return page_type in PAGE_TYPE_REGISTRY


def get_quality_gate(page_type: str) -> QualityGate:
    return get_strategy(page_type).quality_gate()


def get_distribution_channels(page_type: str) -> list[str]:
    return get_strategy(page_type).distribution_channels()


def get_schema_types(page_type: str) -> list[str]:
    return get_strategy(page_type).schema_types()


def build_brief_from_strategy(
    topic_dict: dict,
    gsc_data: Optional[dict] = None,
) -> dict:
    """Build a content brief dict using the registered strategy for the topic's page_type.

    This is the main integration point. content_brief_engine.build_content_brief()
    delegates to this function for all page-type-specific content.

    Returns a dict with strategy-derived fields that can be merged into the brief.
    """
    page_type = str(topic_dict.get("page_type", "occasion_page")).strip() or "occasion_page"
    strategy = get_strategy(page_type)

    ctx = BriefContext(
        slug=str(topic_dict.get("slug", "")).strip(),
        title=str(topic_dict.get("title", "")).strip(),
        primary_keyword=str(topic_dict.get("primary_keyword", "")).strip(),
        category_hint=str(topic_dict.get("category_hint", "")).strip(),
        cluster=str(topic_dict.get("cluster", "")).strip(),
        page_type=page_type,
        selected_products=topic_dict.get("selected_products") or [],
        gsc_data=gsc_data,
        cluster_peer_links=topic_dict.get("cluster_peer_links") or [],
        comparison_items=topic_dict.get("comparison_items") or [],
        city=str(topic_dict.get("city", "")).strip(),
        target_audience=str(topic_dict.get("target_audience", "")).strip(),
        extra=topic_dict.get("extra") or {},
    )

    return {
        "search_intent":      strategy.search_intent(),
        "intro":              strategy.build_intro(ctx),
        "sections":           strategy.build_sections(ctx),
        "faq_items":          strategy.build_faq_items(ctx),
        "cta":                strategy.build_cta(ctx),
        "meta_description":   strategy.build_meta_description(ctx),
        "schema_types":       strategy.schema_types(),
        "distribution_channels": strategy.distribution_channels(),
        "quality_gate":       {
            "min_words":              strategy.quality_gate().min_words,
            "required_faq":           strategy.quality_gate().required_faq,
            "required_products":      strategy.quality_gate().required_products,
            "min_faq_items":          strategy.quality_gate().min_faq_items,
            "min_products":           strategy.quality_gate().min_products,
            "required_local_signal":  strategy.quality_gate().required_local_signal,
        },
    }
