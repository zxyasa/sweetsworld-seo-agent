"""AIO Visibility Monitor — tracks AI answer engine citation of site pages.

Records manual observations when a site URL appears as a source in:
  - ChatGPT / OpenAI browse results
  - Perplexity AI
  - Google AI Overviews (SGE)
  - Microsoft Copilot / Bing Chat

Observations are stored in a SQLite table and mirrored to the EntityGraph as
`page:cited_by:aio_engine` edges, enabling CommandCenter to boost scores for
pages with low AIO coverage.

Usage:
    from aio_visibility_monitor import AIOVisibilityMonitor, get_monitor
    monitor = get_monitor()

    # Log a manual observation (paste the AIO answer + source URL)
    monitor.log_observation(
        page_url="https://sweetsworld.com.au/guides/bulk-lollies/",
        engine="perplexity",
        query="where to buy bulk lollies australia",
        was_cited=True,
        citation_url="https://www.perplexity.ai/search/...",
        notes="Appeared as #2 source",
    )

    # Get coverage report
    report = monitor.coverage_report()

    # Get pages with zero AIO citations (priority targets)
    uncited = monitor.get_uncited_pages(page_urls=[...])
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AIO Engine definitions
# ---------------------------------------------------------------------------

AIO_ENGINES: Dict[str, Dict[str, Any]] = {
    "chatgpt": {
        "name": "ChatGPT / OpenAI",
        "weight": 1.0,
        "url_hint": "chat.openai.com",
    },
    "perplexity": {
        "name": "Perplexity AI",
        "weight": 0.9,
        "url_hint": "perplexity.ai",
    },
    "google_aio": {
        "name": "Google AI Overview",
        "weight": 1.0,
        "url_hint": "google.com/search",
    },
    "copilot": {
        "name": "Microsoft Copilot",
        "weight": 0.8,
        "url_hint": "copilot.microsoft.com",
    },
    "gemini": {
        "name": "Google Gemini",
        "weight": 0.9,
        "url_hint": "gemini.google.com",
    },
}


# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------

_AIO_SCHEMA = """
CREATE TABLE IF NOT EXISTS aio_observations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    page_url     TEXT NOT NULL,
    engine       TEXT NOT NULL,
    query        TEXT NOT NULL DEFAULT '',
    was_cited    INTEGER NOT NULL DEFAULT 0,
    citation_url TEXT NOT NULL DEFAULT '',
    site_id      TEXT NOT NULL DEFAULT 'sweetsworld',
    observed_at  TEXT NOT NULL,
    notes        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_aio_page    ON aio_observations(page_url);
CREATE INDEX IF NOT EXISTS idx_aio_engine  ON aio_observations(engine);
CREATE INDEX IF NOT EXISTS idx_aio_site    ON aio_observations(site_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_aio_unique ON aio_observations(site_id, page_url, engine, query);
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
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AIOObservation:
    page_url: str
    engine: str
    query: str
    was_cited: bool
    citation_url: str = ""
    observed_at: str = ""
    notes: str = ""

    @property
    def engine_name(self) -> str:
        return AIO_ENGINES.get(self.engine, {}).get("name", self.engine)


@dataclass
class AIOCoverageReport:
    site_id: str
    total_observations: int
    total_citations: int
    citation_rate: float                      # 0.0–1.0
    by_engine: Dict[str, Dict[str, int]]      # engine → {observations, citations}
    top_cited_pages: List[Dict[str, Any]]     # sorted by citation count desc
    zero_citation_pages: List[str]            # pages with observations but 0 citations


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

class AIOVisibilityMonitor:
    """Tracks AI engine citation observations and mirrors to entity graph."""

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
            con.executescript(_AIO_SCHEMA)

    # ------------------------------------------------------------------
    # Graph bridge
    # ------------------------------------------------------------------

    def _get_graph(self) -> Any:
        if not self._graph_db_path:
            return None
        try:
            import sys
            from pathlib import Path as _Path
            src = str(_Path(__file__).parent.parent.parent.parent / "apps" / "growth-graph" / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            from growth_graph.entity_graph import EntityGraph
            return EntityGraph(self._graph_db_path, site_id=self.site_id)
        except Exception as exc:
            logger.warning(f"EntityGraph unavailable for AIO monitor: {exc}")
            return None

    def _sync_to_graph(self, obs: AIOObservation) -> None:
        """Write page:cited_by:aio_engine edge when was_cited=True."""
        if not obs.was_cited:
            return
        graph = self._get_graph()
        if graph is None:
            return
        try:
            page_id = f"page:{obs.page_url}"
            graph.upsert_entity(page_id, "page", obs.page_url, url=obs.page_url)

            engine_id = f"aio_engine:{obs.engine}"
            engine_info = AIO_ENGINES.get(obs.engine, {})
            graph.upsert_entity(
                engine_id, "aio_engine", engine_info.get("name", obs.engine),
                properties={"weight": engine_info.get("weight", 1.0)},
            )

            graph.add_relationship(
                page_id,
                engine_id,
                "page:cited_by:aio_engine",
                weight=engine_info.get("weight", 1.0),
                properties={"query": obs.query, "citation_url": obs.citation_url},
            )
            logger.debug(f"Graph AIO: {page_id} cited_by {obs.engine}")
        except Exception as exc:
            logger.warning(f"Graph AIO sync failed: {exc}")

    # ------------------------------------------------------------------
    # Observation logging
    # ------------------------------------------------------------------

    def log_observation(
        self,
        page_url: str,
        engine: str,
        query: str = "",
        was_cited: bool = False,
        citation_url: str = "",
        notes: str = "",
    ) -> AIOObservation:
        """Record an AIO observation (cited or not)."""
        if engine not in AIO_ENGINES:
            raise ValueError(f"Unknown engine '{engine}'. Valid: {list(AIO_ENGINES)}")

        now = datetime.now(timezone.utc).isoformat()
        with _conn(self.db_path) as con:
            con.execute(
                """INSERT INTO aio_observations
                       (page_url, engine, query, was_cited, citation_url, site_id, observed_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(site_id, page_url, engine, query) DO UPDATE SET
                       was_cited=excluded.was_cited,
                       citation_url=COALESCE(excluded.citation_url, citation_url),
                       observed_at=excluded.observed_at,
                       notes=excluded.notes""",
                (page_url, engine, query, int(was_cited), citation_url, self.site_id, now, notes),
            )

        obs = AIOObservation(
            page_url=page_url,
            engine=engine,
            query=query,
            was_cited=was_cited,
            citation_url=citation_url,
            observed_at=now,
            notes=notes,
        )
        logger.info(f"AIO observation: {page_url} {'CITED' if was_cited else 'not cited'} by {engine}")
        self._sync_to_graph(obs)
        return obs

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_observations_for_page(self, page_url: str) -> List[AIOObservation]:
        with _conn(self.db_path) as con:
            rows = con.execute(
                "SELECT * FROM aio_observations WHERE page_url=? AND site_id=? ORDER BY observed_at DESC",
                (page_url, self.site_id),
            ).fetchall()
        return [
            AIOObservation(
                page_url=r["page_url"],
                engine=r["engine"],
                query=r["query"],
                was_cited=bool(r["was_cited"]),
                citation_url=r["citation_url"],
                observed_at=r["observed_at"],
                notes=r["notes"],
            )
            for r in rows
        ]

    def get_uncited_pages(self, page_urls: List[str]) -> List[str]:
        """Return pages from the given list that have zero positive AIO citations."""
        if not page_urls:
            return []
        with _conn(self.db_path) as con:
            cited = {
                r["page_url"]
                for r in con.execute(
                    f"""SELECT DISTINCT page_url FROM aio_observations
                        WHERE site_id=? AND was_cited=1
                        AND page_url IN ({','.join('?' * len(page_urls))})""",
                    (self.site_id, *page_urls),
                ).fetchall()
            }
        return [url for url in page_urls if url not in cited]

    def get_aio_score(self, page_url: str) -> float:
        """Return a 0.0–1.0 AIO visibility score for a page.

        Score = sum(engine weight for each citation) / sum(all engine weights).
        A page cited by all engines at full weight scores 1.0.
        """
        total_weight = sum(e["weight"] for e in AIO_ENGINES.values())
        with _conn(self.db_path) as con:
            rows = con.execute(
                "SELECT engine FROM aio_observations WHERE page_url=? AND site_id=? AND was_cited=1",
                (page_url, self.site_id),
            ).fetchall()
        cited_weight = sum(
            AIO_ENGINES.get(r["engine"], {}).get("weight", 1.0) for r in rows
        )
        return min(cited_weight / total_weight, 1.0) if total_weight else 0.0

    def coverage_report(self) -> AIOCoverageReport:
        with _conn(self.db_path) as con:
            all_rows = con.execute(
                "SELECT page_url, engine, was_cited FROM aio_observations WHERE site_id=?",
                (self.site_id,),
            ).fetchall()

        total = len(all_rows)
        cited = sum(1 for r in all_rows if r["was_cited"])

        by_engine: Dict[str, Dict[str, int]] = {}
        page_citations: Dict[str, int] = {}

        for r in all_rows:
            eng = r["engine"]
            if eng not in by_engine:
                by_engine[eng] = {"observations": 0, "citations": 0}
            by_engine[eng]["observations"] += 1
            if r["was_cited"]:
                by_engine[eng]["citations"] += 1
                page_citations[r["page_url"]] = page_citations.get(r["page_url"], 0) + 1

        top_pages = sorted(
            [{"page_url": url, "citation_count": cnt} for url, cnt in page_citations.items()],
            key=lambda x: -x["citation_count"],
        )[:20]

        # Pages with at least one observation but zero citations
        observed_pages = {r["page_url"] for r in all_rows}
        zero_citation = [p for p in observed_pages if p not in page_citations]

        return AIOCoverageReport(
            site_id=self.site_id,
            total_observations=total,
            total_citations=cited,
            citation_rate=cited / total if total else 0.0,
            by_engine=by_engine,
            top_cited_pages=top_pages,
            zero_citation_pages=zero_citation,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_monitor(db_path: Optional[str] = None, site_id: str = "sweetsworld") -> AIOVisibilityMonitor:
    """Get an AIOVisibilityMonitor, resolving paths from SiteContext or growth_graph registry."""
    graph_db_path: Optional[str] = None

    if db_path is None:
        # 1. Try SiteContext first (supports all registered sites without growth_graph dependency)
        try:
            from site_context import load_site_context
            ctx = load_site_context(site_id)
            db_path = str(ctx.site_dir / "data" / "aio_observations.db")
        except Exception:
            pass

    if db_path is None:
        # 2. Fall back to growth_graph site_registry (legacy sweetsworld path)
        try:
            import sys
            from pathlib import Path as _Path
            src = str(_Path(__file__).parent.parent.parent.parent / "apps" / "growth-graph" / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            from growth_graph.site_registry import load_registry
            registry = load_registry()
            profile = registry.get(site_id)
            if profile:
                db_path = str(_Path(profile.topics_db).parent / "aio_observations.db")
                graph_db_path = profile.growth_graph_db
        except Exception:
            pass

    if db_path is None:
        # 3. Last resort: project-level data/ directory
        db_path = str(Path(__file__).parent.parent / "data" / "aio_observations.db")

    return AIOVisibilityMonitor(db_path, site_id=site_id, graph_db_path=graph_db_path)
