"""Citation Planner — systematic offsite citation building.

Models the citation channels (social platforms, directories, syndication)
and tracks which pages have been distributed to which channels.

Purpose: Move from "fire-and-forget social posts" to a systematic
brand entity / citation network that helps AI answer engines identify
SweetsWorld as a trusted source.

Channel types:
  - social_post:    GBP, Pinterest, Facebook, Instagram, X
  - syndication:    Medium, Substack (with canonical)
  - directory:      Yelp, Yellow Pages, True Local
  - qa_platform:    Reddit, Quora (semi-manual)

Usage:
    from citation_planner import CitationPlanner, get_planner
    planner = get_planner()
    channels = planner.get_channels_for_page_type("guide_page")
    brief = planner.build_citation_brief(page_url, page_type, title, excerpt)
    planner.log_citation(page_url, "pinterest", citation_url)
    coverage = planner.get_citation_coverage(page_url)
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Citation Channel definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CitationChannel:
    channel_id: str
    channel_type: str    # "social_post" | "syndication" | "directory" | "qa_platform"
    display_name: str
    domain_authority: int   # 0–100
    indexable: bool          # Does Google index posts on this platform?
    entity_signal: bool      # Does this strengthen brand entity recognition?
    automation_level: str    # "full" | "assisted" | "manual_template"
    avg_citation_value: int  # 0–100 estimated value per citation


# All supported citation channels
ALL_CHANNELS: Dict[str, CitationChannel] = {
    "gbp_post": CitationChannel(
        "gbp_post", "social_post", "Google Business Profile",
        domain_authority=95, indexable=True, entity_signal=True,
        automation_level="full", avg_citation_value=90,
    ),
    "pinterest": CitationChannel(
        "pinterest", "social_post", "Pinterest",
        domain_authority=94, indexable=True, entity_signal=True,
        automation_level="full", avg_citation_value=75,
    ),
    "facebook": CitationChannel(
        "facebook", "social_post", "Facebook",
        domain_authority=96, indexable=False, entity_signal=True,
        automation_level="full", avg_citation_value=60,
    ),
    "instagram": CitationChannel(
        "instagram", "social_post", "Instagram",
        domain_authority=93, indexable=False, entity_signal=True,
        automation_level="full", avg_citation_value=55,
    ),
    "x": CitationChannel(
        "x", "social_post", "X (Twitter)",
        domain_authority=94, indexable=True, entity_signal=False,
        automation_level="full", avg_citation_value=50,
    ),
    "medium": CitationChannel(
        "medium", "syndication", "Medium",
        domain_authority=95, indexable=True, entity_signal=True,
        automation_level="assisted", avg_citation_value=80,
    ),
    "yelp": CitationChannel(
        "yelp", "directory", "Yelp",
        domain_authority=94, indexable=True, entity_signal=True,
        automation_level="manual_template", avg_citation_value=85,
    ),
    "yellow_pages": CitationChannel(
        "yellow_pages", "directory", "Yellow Pages AU",
        domain_authority=72, indexable=True, entity_signal=True,
        automation_level="manual_template", avg_citation_value=70,
    ),
    "true_local": CitationChannel(
        "true_local", "directory", "True Local AU",
        domain_authority=58, indexable=True, entity_signal=True,
        automation_level="manual_template", avg_citation_value=65,
    ),
    "reddit": CitationChannel(
        "reddit", "qa_platform", "Reddit",
        domain_authority=99, indexable=True, entity_signal=False,
        automation_level="manual_template", avg_citation_value=70,
    ),
    "quora": CitationChannel(
        "quora", "qa_platform", "Quora",
        domain_authority=93, indexable=True, entity_signal=False,
        automation_level="manual_template", avg_citation_value=65,
    ),
}

# Per page type: which channels are appropriate
PAGE_TYPE_CHANNELS: Dict[str, List[str]] = {
    "landing_page":      ["gbp_post", "facebook", "instagram", "pinterest"],
    "occasion_page":     ["gbp_post", "facebook", "instagram", "pinterest", "x"],
    "guide_page":        ["pinterest", "facebook", "medium"],
    "category_page":     ["pinterest", "facebook"],
    "faq_page":          ["facebook", "quora"],
    "comparison_page":   ["pinterest", "facebook", "x", "reddit"],
    "best_of_page":      ["facebook", "instagram", "pinterest"],
    "city_landing_page": ["gbp_post", "facebook", "yelp"],
}

# Minimum recommended channels per published page
MIN_CITATIONS_TARGET = 3


@dataclass
class CitationBrief:
    page_url: str
    page_type: str
    title: str
    excerpt: str
    keyword: str
    channel: CitationChannel
    suggested_caption: str
    suggested_hashtags: List[str] = field(default_factory=list)
    canonical_note: str = ""  # for syndication channels


# ---------------------------------------------------------------------------
# Citation SQLite log schema
# ---------------------------------------------------------------------------

_CITATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS citations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_url    TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    citation_url TEXT,
    site_id     TEXT NOT NULL DEFAULT 'sweetsworld',
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL,
    published_at TEXT,
    notes       TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_cite_page ON citations(page_url);
CREATE INDEX IF NOT EXISTS idx_cite_channel ON citations(channel_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cite_unique ON citations(page_url, channel_id);
"""


@contextmanager
def _conn(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Citation Planner
# ---------------------------------------------------------------------------

class CitationPlanner:
    """Manages citation strategy and tracks distribution coverage per page."""

    def __init__(
        self,
        db_path: str,
        site_id: str = "sweetsworld",
        graph_db_path: Optional[str] = None,
    ) -> None:
        self.db_path = db_path
        self.site_id = site_id
        self._graph_db_path = graph_db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with _conn(db_path) as con:
            con.executescript(_CITATION_SCHEMA)

    def _get_graph(self) -> Any:
        """Lazy-load EntityGraph if graph_db_path is configured."""
        if not self._graph_db_path:
            return None
        try:
            import sys
            from pathlib import Path as _Path
            growth_graph_src = str(_Path(__file__).parent.parent.parent.parent / "apps" / "growth-graph" / "src")
            if growth_graph_src not in sys.path:
                sys.path.insert(0, growth_graph_src)
            from growth_graph.entity_graph import EntityGraph
            return EntityGraph(self._graph_db_path, site_id=self.site_id)
        except Exception as exc:
            logger.warning(f"EntityGraph not available: {exc}")
            return None

    # ------------------------------------------------------------------
    # Channel selection
    # ------------------------------------------------------------------

    def get_channels_for_page_type(self, page_type: str) -> List[CitationChannel]:
        channel_ids = PAGE_TYPE_CHANNELS.get(page_type, PAGE_TYPE_CHANNELS.get("landing_page", []))
        return [ALL_CHANNELS[cid] for cid in channel_ids if cid in ALL_CHANNELS]

    def get_auto_channels(self, page_type: str) -> List[CitationChannel]:
        """Return only fully-automated channels for this page type."""
        return [c for c in self.get_channels_for_page_type(page_type) if c.automation_level == "full"]

    # ------------------------------------------------------------------
    # Brief generation
    # ------------------------------------------------------------------

    def build_citation_brief(
        self,
        page_url: str,
        page_type: str,
        title: str,
        excerpt: str,
        keyword: str,
        channel_id: str,
    ) -> Optional[CitationBrief]:
        channel = ALL_CHANNELS.get(channel_id)
        if not channel:
            return None

        # Build platform-appropriate caption
        caption = self._build_caption(page_type, title, excerpt, keyword, channel)
        hashtags = self._build_hashtags(page_type, keyword)
        canonical = (
            f"Originally published at: {page_url}" if channel.channel_type == "syndication" else ""
        )

        return CitationBrief(
            page_url=page_url,
            page_type=page_type,
            title=title,
            excerpt=excerpt,
            keyword=keyword,
            channel=channel,
            suggested_caption=caption,
            suggested_hashtags=hashtags,
            canonical_note=canonical,
        )

    @property
    def _brand_name(self) -> str:
        """Derive a display brand name from site_id for use in captions/hashtags."""
        return getattr(self, "_ctx_display_name", None) or "".join(
            w.capitalize() for w in self.site_id.replace("-", "_").split("_")
        )

    def _build_caption(
        self, page_type: str, title: str, excerpt: str, keyword: str, channel: CitationChannel
    ) -> str:
        brand = self._brand_name
        if channel.channel_id == "gbp_post":
            return f"{title}\n\n{excerpt}\n\nLearn more at {brand}."
        if channel.channel_id == "pinterest":
            return f"{title}\n\n{excerpt}\n\nFind the full guide at {brand}."
        if channel.channel_id == "medium":
            return f"# {title}\n\n{excerpt}\n\n---\n*This article was originally published on {brand}*"
        if channel.channel_type == "qa_platform":
            return f"Regarding '{keyword}': {excerpt} For a full breakdown, see {brand}."
        return f"{title}\n\n{excerpt}"

    def _build_hashtags(self, page_type: str, keyword: str) -> List[str]:
        brand_tag = "#" + self._brand_name
        safe_keyword = keyword or ""
        keyword_tag = "#" + "".join(w.capitalize() for w in safe_keyword.split()[:3])
        base = ["#SweetsWorld", "#AustralianCandy", "#CandyAustralia"]
        if brand_tag not in base:
            base.append(brand_tag)
        if keyword_tag != "#" and keyword_tag not in base:
            base.append(keyword_tag)
        if page_type == "occasion_page":
            return base + ["#PartyPlanning", "#EventMarketing"]
        if page_type == "guide_page":
            return base + ["#BusinessGuide"]
        if page_type == "city_landing_page":
            return base + ["#LocalBusiness", "#LocalSEO"]
        return base

    # ------------------------------------------------------------------
    # Citation logging
    # ------------------------------------------------------------------

    def log_citation(
        self,
        page_url: str,
        channel_id: str,
        citation_url: str = "",
        status: str = "published",
        notes: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        published_at = now if status == "published" else None
        with _conn(self.db_path) as con:
            con.execute(
                """INSERT INTO citations (page_url, channel_id, citation_url, site_id, status, created_at, published_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(page_url, channel_id) DO UPDATE SET
                       citation_url=COALESCE(excluded.citation_url, citation_url),
                       status=excluded.status,
                       published_at=COALESCE(excluded.published_at, published_at),
                       notes=excluded.notes""",
                (page_url, channel_id, citation_url, self.site_id, status, now, published_at, notes),
            )
        logger.info(f"Citation logged: {page_url} → {channel_id} ({status})")

        # Mirror to entity graph if available and status is published
        if status == "published":
            self._sync_to_graph(page_url, channel_id, citation_url)

    def _sync_to_graph(self, page_url: str, channel_id: str, citation_url: str) -> None:
        """Write page→platform distribution edge to entity graph."""
        graph = self._get_graph()
        if graph is None:
            return
        try:
            # Ensure page entity exists (upsert is idempotent)
            page_slug = urlparse(page_url).path.strip("/").split("/")[-1] or page_url.rstrip("/").split("/")[-1]
            page_entity_id = f"page:{page_slug}"
            graph.upsert_entity(page_entity_id, "page", page_url, slug=page_slug, url=page_url)

            # Ensure platform entity exists
            channel = ALL_CHANNELS.get(channel_id)
            platform_name = channel.display_name if channel else channel_id
            platform_entity_id = f"platform:{channel_id}"
            graph.upsert_entity(
                platform_entity_id, "social_platform", platform_name,
                properties={"channel_type": channel.channel_type if channel else "unknown"},
            )

            # Add distribution relationship
            graph.add_relationship(
                page_entity_id,
                platform_entity_id,
                "page:distributed_to:platform",
                properties={"citation_url": citation_url},
            )
            logger.debug(f"Graph: {page_entity_id} → {platform_entity_id}")
        except Exception as exc:
            logger.warning(f"Graph sync failed for {page_url} → {channel_id}: {exc}")

    def get_citation_coverage(self, page_url: str) -> Dict[str, Any]:
        with _conn(self.db_path) as con:
            rows = con.execute(
                "SELECT * FROM citations WHERE page_url=? AND site_id=?",
                (page_url, self.site_id),
            ).fetchall()

        published = [r for r in rows if r["status"] == "published"]
        return {
            "page_url": page_url,
            "total_citations": len(rows),
            "published_citations": len(published),
            "channels": [r["channel_id"] for r in published],
            "meets_minimum": len(published) >= MIN_CITATIONS_TARGET,
        }

    def get_pages_below_minimum(self) -> List[Dict[str, Any]]:
        """Return pages that have fewer than MIN_CITATIONS_TARGET published citations."""
        with _conn(self.db_path) as con:
            rows = con.execute(
                """SELECT page_url, COUNT(*) as cnt FROM citations
                   WHERE site_id=? AND status='published'
                   GROUP BY page_url HAVING cnt < ?""",
                (self.site_id, MIN_CITATIONS_TARGET),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_uncited_channels(self, page_url: str, page_type: str) -> List[CitationChannel]:
        """Return channels that should be covered but haven't been cited yet."""
        coverage = self.get_citation_coverage(page_url)
        covered = set(coverage["channels"])
        target_channels = self.get_channels_for_page_type(page_type)
        return [c for c in target_channels if c.channel_id not in covered]

    def citation_summary(self) -> Dict[str, Any]:
        with _conn(self.db_path) as con:
            total = con.execute(
                "SELECT COUNT(*) as n FROM citations WHERE site_id=?", (self.site_id,)
            ).fetchone()["n"]
            by_channel = {
                r["channel_id"]: r["n"]
                for r in con.execute(
                    "SELECT channel_id, COUNT(*) as n FROM citations WHERE site_id=? AND status='published' GROUP BY channel_id",
                    (self.site_id,),
                ).fetchall()
            }
        return {"total_citations": total, "by_channel": by_channel}


def get_planner(db_path: Optional[str] = None, site_id: str = "sweetsworld") -> CitationPlanner:
    """Get a CitationPlanner instance, resolving DB path from SiteContext or growth_graph registry."""
    graph_db_path: Optional[str] = None
    display_name: Optional[str] = None

    if db_path is None:
        # 1. Try SiteContext first (supports all registered sites)
        try:
            from site_context import load_site_context
            ctx = load_site_context(site_id)
            db_path = str(ctx.site_dir / "data" / "citations.db")
            display_name = ctx.display_name
        except Exception:
            pass

    if db_path is None:
        # 2. Fall back to growth_graph site_registry (legacy sweetsworld path)
        try:
            import sys
            from pathlib import Path as _Path
            growth_graph_src = str(_Path(__file__).parent.parent.parent.parent / "apps" / "growth-graph" / "src")
            if growth_graph_src not in sys.path:
                sys.path.insert(0, growth_graph_src)
            from growth_graph.site_registry import load_registry
            registry = load_registry()
            profile = registry.get(site_id)
            if profile:
                db_path = str(_Path(profile.topics_db).parent / "citations.db")
                graph_db_path = profile.growth_graph_db
        except Exception:
            pass

    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "data" / "citations.db")

    planner = CitationPlanner(db_path, site_id=site_id, graph_db_path=graph_db_path)
    if display_name:
        planner._ctx_display_name = display_name
    return planner
