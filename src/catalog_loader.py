"""CatalogLoader — site-agnostic product/service catalog abstraction.

Normalises products.json and services.json into a uniform CatalogItem list
so the rest of the engine never needs to branch on catalog_type.

Supported catalog_type values (from site.json):
  "products"  — sweetsworld-style products.json
  "services"  — newcastlehub-style services.json

Usage:
    from catalog_loader import load_catalog, CatalogItem
    items = load_catalog(ctx)          # list[CatalogItem]
    in_stock = [i for i in items if i.is_available]
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from site_context import SiteContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CatalogItem:
    """Normalised representation of one product or service.

    Engine code should use only these fields.
    Site-specific raw fields are preserved in `extra` for edge cases.
    """
    name:         str
    category:     str             # primary category
    categories:   tuple[str, ...]  # all categories (immutable for frozen dataclass)
    tags:         tuple[str, ...]
    url:          str
    slug:         str
    image_url:    str | None
    is_available: bool            # in_stock (products) | is_active (services)
    description:  str
    price:        str             # raw string from source; "" if not applicable
    extra:        dict[str, Any] = field(default_factory=dict, compare=False)

    def matches_keyword(self, keyword: str) -> bool:
        """True if keyword appears in name, tags, or categories (case-insensitive)."""
        kw = keyword.lower()
        return (
            kw in self.name.lower()
            or any(kw in t.lower() for t in self.tags)
            or any(kw in c.lower() for c in self.categories)
        )

    def matches_any(self, keywords: list[str]) -> bool:
        return any(self.matches_keyword(kw) for kw in keywords)


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_products(path: Path) -> list[CatalogItem]:
    """Parse sweetsworld-style products.json."""
    data = json.loads(path.read_text())
    raw: list[dict] = data.get("products", data) if isinstance(data, dict) else data

    items: list[CatalogItem] = []
    for r in raw:
        try:
            items.append(CatalogItem(
                name         = str(r.get("product_name") or r.get("name") or "").strip(),
                category     = str(r.get("category") or "").strip(),
                categories   = tuple(r.get("categories") or [r.get("category", "")]),
                tags         = tuple(r.get("tags") or []),
                url          = str(r.get("url") or "").strip(),
                slug         = str(r.get("slug") or "").strip(),
                image_url    = r.get("image_url") or None,
                is_available = bool(r.get("is_in_stock", True)),
                description  = str(r.get("description") or "").strip()[:500],
                price        = str(r.get("price") or "").strip(),
                extra        = r,
            ))
        except Exception as exc:
            logger.warning("Skipping malformed product record: %s — %s", r.get("slug"), exc)

    logger.info("Loaded %d products from %s", len(items), path.name)
    return items


def _load_services(path: Path) -> list[CatalogItem]:
    """Parse newcastlehub-style services.json.

    Expected format:
    {
      "services": [
        {
          "service_name": "...",
          "category": "...",
          "tags": [...],
          "url": "...",
          "slug": "...",
          "image_url": "...",
          "is_active": true,
          "description": "...",
          "categories": [...]
        }
      ]
    }
    """
    data = json.loads(path.read_text())
    raw: list[dict] = data.get("services", data) if isinstance(data, dict) else data

    items: list[CatalogItem] = []
    for r in raw:
        try:
            items.append(CatalogItem(
                name         = str(r.get("service_name") or r.get("name") or "").strip(),
                category     = str(r.get("category") or "").strip(),
                categories   = tuple(r.get("categories") or [r.get("category", "")]),
                tags         = tuple(r.get("tags") or []),
                url          = str(r.get("url") or "").strip(),
                slug         = str(r.get("slug") or "").strip(),
                image_url    = r.get("image_url") or None,
                is_available = bool(r.get("is_active", True)),
                description  = str(r.get("description") or "").strip()[:500],
                price        = "",   # services don't have a price field
                extra        = r,
            ))
        except Exception as exc:
            logger.warning("Skipping malformed service record: %s — %s", r.get("slug"), exc)

    logger.info("Loaded %d services from %s", len(items), path.name)
    return items


# ── Public API ────────────────────────────────────────────────────────────────

_LOADERS = {
    "products": _load_products,
    "services": _load_services,
}


def load_catalog(ctx: "SiteContext") -> list[CatalogItem]:
    """Load and normalise the catalog for a given site.

    Returns an empty list (with a warning) if the catalog file is missing,
    so the engine can degrade gracefully rather than crash.
    """
    if not ctx.catalog_path.exists():
        logger.warning(
            "[%s] Catalog file missing: %s — returning empty catalog",
            ctx.site_id, ctx.catalog_path,
        )
        return []

    loader = _LOADERS.get(ctx.catalog_type)
    if loader is None:
        raise ValueError(
            f"[{ctx.site_id}] Unknown catalog_type: {ctx.catalog_type!r}. "
            f"Supported: {list(_LOADERS)}"
        )

    return loader(ctx.catalog_path)


def filter_available(items: list[CatalogItem]) -> list[CatalogItem]:
    """Return only items that are currently in stock / active."""
    return [i for i in items if i.is_available]


def filter_by_category(items: list[CatalogItem], category: str) -> list[CatalogItem]:
    """Case-insensitive category filter (matches any of item.categories)."""
    cat = category.lower()
    return [i for i in items if any(cat in c.lower() for c in i.categories)]


def filter_by_keyword(items: list[CatalogItem], keyword: str) -> list[CatalogItem]:
    """Return items whose name/tags/categories contain the keyword."""
    return [i for i in items if i.matches_keyword(keyword)]


def select_for_topic(
    items: list[CatalogItem],
    keywords: list[str],
    *,
    available_only: bool = True,
    limit: int = 8,
) -> list[CatalogItem]:
    """Pick the most relevant catalog items for a topic.

    Scoring: items matching more keywords rank higher.
    Falls back to first `limit` available items if no matches.
    """
    pool = filter_available(items) if available_only else items
    if not pool:
        return []

    if not keywords:
        return pool[:limit]

    scored: list[tuple[int, CatalogItem]] = []
    for item in pool:
        score = sum(1 for kw in keywords if item.matches_keyword(kw))
        if score > 0:
            scored.append((score, item))

    if scored:
        scored.sort(key=lambda t: t[0], reverse=True)
        return [item for _, item in scored[:limit]]

    # No keyword matches — return first N available items as fallback
    logger.debug("No keyword matches for %s — using first %d available items", keywords, limit)
    return pool[:limit]
