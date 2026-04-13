"""Base class and shared data models for page-type strategies."""
# TODO: Phase 3 — migrate QualityGate to use website-os/shared/quality_gate.py
# from apps.website_os.shared.quality_gate import QualityGate, evaluate_quality
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BriefContext:
    """All inputs needed to build a content brief for any page type."""
    slug: str
    title: str
    primary_keyword: str
    category_hint: str
    cluster: str
    page_type: str
    selected_products: List[Dict[str, Any]] = field(default_factory=list)
    gsc_data: Optional[Dict[str, Any]] = None
    cluster_peer_links: List[str] = field(default_factory=list)
    # Optional enrichment fields for new page types
    comparison_items: List[str] = field(default_factory=list)   # for comparison_page
    city: str = ""                                               # for city_landing_page
    target_audience: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityGate:
    min_words: int = 350
    required_faq: bool = False
    required_products: bool = False
    min_faq_items: int = 3
    min_products: int = 0
    min_comparison_items: int = 0
    required_local_signal: bool = False
    required_schema_types: List[str] = field(default_factory=list)


class PageTypeStrategy(ABC):
    """Abstract base for all page-type strategies.

    Each concrete strategy encapsulates the content generation rules,
    quality gates, schema types, and distribution channels for one page type.
    """

    type_id: str = ""
    display_name: str = ""

    # ------------------------------------------------------------------
    # Abstract methods — must be implemented by each strategy
    # ------------------------------------------------------------------

    @abstractmethod
    def build_intro(self, ctx: BriefContext) -> str:
        """Return the page intro paragraph (≤240 chars)."""

    @abstractmethod
    def build_sections(self, ctx: BriefContext) -> List[Dict[str, Any]]:
        """Return list of {heading, paragraphs, bullets} section dicts."""

    @abstractmethod
    def build_faq_items(self, ctx: BriefContext) -> List[Dict[str, str]]:
        """Return list of {question, answer} FAQ dicts."""

    @abstractmethod
    def build_cta(self, ctx: BriefContext) -> Dict[str, str]:
        """Return {heading, body, button_text} CTA dict."""

    @abstractmethod
    def build_meta_description(self, ctx: BriefContext) -> str:
        """Return meta description (≤155 chars)."""

    @abstractmethod
    def quality_gate(self) -> QualityGate:
        """Return quality gate thresholds for this page type."""

    # ------------------------------------------------------------------
    # Optional overrides — sensible defaults provided
    # ------------------------------------------------------------------

    def schema_types(self) -> List[str]:
        """Return list of Schema.org @type values to emit."""
        return ["BreadcrumbList"]

    def distribution_channels(self) -> List[str]:
        """Return list of social channels to distribute to after publish."""
        return ["facebook", "instagram"]

    def search_intent(self) -> str:
        return "Informational"

    def update_strategy(self) -> str:
        """'create_new', 'update_existing', or 'both'."""
        return "create_new"

    # ------------------------------------------------------------------
    # Shared helpers (available to all strategy subclasses)
    # ------------------------------------------------------------------

    def _clean(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _trim(self, text: str, max_length: int) -> str:
        cleaned = self._clean(text)
        if len(cleaned) <= max_length:
            return cleaned
        shortened = cleaned[: max_length - 1].rsplit(" ", 1)[0].rstrip(",.;:-")
        return f"{shortened}..." if shortened else cleaned[: max_length - 3] + "..."

    def subject_phrase(self, ctx: BriefContext) -> str:
        """Derive a clean subject noun phrase from keyword + title."""
        candidate = self._clean(ctx.primary_keyword or ctx.title)
        if not candidate:
            return "this range"
        candidate = re.sub(r"\baustralia\b", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s+", " ", candidate).strip(" ,:-?")
        return candidate or self._clean(ctx.title) or "this range"

    def product_shortlist(self, ctx: BriefContext, max_items: int = 4) -> List[str]:
        """Return first N product names from selected_products."""
        names = []
        for p in ctx.selected_products[:max_items]:
            if isinstance(p, dict):
                name = self._clean(p.get("product_name") or p.get("name", ""))
                if name:
                    names.append(name)
        return names
