"""SiteDB — per-site SQLite store for multi-site SEO agent architecture.

Manages 5 tables:
  pages            — published page registry (replaces page_registry.json)
  publish_log      — immutable audit trail of every publish/update action
  aio_observations — AIO citation tracking (replaces aio_observations.db)
  job_runs         — bulk script progress for checkpoint/resume
  write_log        — rate-limit tracking per target URL

TopicsDB (topics_db.py) handles the topics table separately and is unchanged.

Usage:
    db = SiteDB(site_dir=Path("sites/sweetsworld"))
    db.upsert_page({"slug": "best-candy", "status": "published", ...})
    peers = db.get_cluster_peers("american_candy", exclude_slug="best-candy")
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── pages ────────────────────────────────────────────────────────────────────
-- Mirrors page_registry.json schema + adds multi-site / content-ops fields.
CREATE TABLE IF NOT EXISTS pages (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,

    -- identity (unique key)
    slug                     TEXT NOT NULL UNIQUE,

    -- discovery / planning
    keyword                  TEXT NOT NULL DEFAULT '',
    page_type                TEXT NOT NULL DEFAULT 'landing_page',
    intent                   TEXT NOT NULL DEFAULT 'informational',
    cluster                  TEXT NOT NULL DEFAULT '',
    primary_keyword          TEXT NOT NULL DEFAULT '',

    -- WordPress
    wp_post_id               INTEGER,
    url                      TEXT NOT NULL DEFAULT '',
    title                    TEXT NOT NULL DEFAULT '',

    -- lifecycle
    status                   TEXT NOT NULL DEFAULT 'pending',
    template_version         TEXT NOT NULL DEFAULT '',
    product_rule_version     TEXT NOT NULL DEFAULT '',
    brief_id                 TEXT NOT NULL DEFAULT '',
    blocking_reason          TEXT,
    notes                    TEXT NOT NULL DEFAULT '',

    -- content quality
    word_count               INTEGER,

    -- injection tracking (0/1 flags)
    faq_injected             INTEGER NOT NULL DEFAULT 0,
    meta_injected            INTEGER NOT NULL DEFAULT 0,
    internal_links_injected  INTEGER NOT NULL DEFAULT 0,
    indexing_submitted       INTEGER NOT NULL DEFAULT 0,

    -- timestamps
    published_at             TEXT,
    last_updated_at          TEXT,
    created_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_pages_status   ON pages(status);
CREATE INDEX IF NOT EXISTS idx_pages_cluster  ON pages(cluster);
CREATE INDEX IF NOT EXISTS idx_pages_page_type ON pages(page_type);

-- ── publish_log ──────────────────────────────────────────────────────────────
-- Immutable audit trail. Never UPDATE or DELETE rows here.
CREATE TABLE IF NOT EXISTS publish_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT    NOT NULL,
    action      TEXT    NOT NULL,   -- publish / update / quality_blocked / error / skipped
    wp_post_id  INTEGER,
    details     TEXT    NOT NULL DEFAULT '{}',  -- JSON blob
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_plog_slug       ON publish_log(slug);
CREATE INDEX IF NOT EXISTS idx_plog_created_at ON publish_log(created_at);

-- ── aio_observations ─────────────────────────────────────────────────────────
-- Compatible with existing aio_observations.db schema.
CREATE TABLE IF NOT EXISTS aio_observations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    page_url     TEXT    NOT NULL,
    engine       TEXT    NOT NULL,   -- chatgpt / perplexity / google_aio / copilot / gemini
    query        TEXT    NOT NULL DEFAULT '',
    was_cited    INTEGER NOT NULL DEFAULT 0,
    citation_url TEXT    NOT NULL DEFAULT '',
    site_id      TEXT    NOT NULL DEFAULT '',
    notes        TEXT    NOT NULL DEFAULT '',
    observed_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_aio_url_engine ON aio_observations(page_url, engine);
CREATE INDEX IF NOT EXISTS idx_aio_observed   ON aio_observations(observed_at);

-- ── job_runs ─────────────────────────────────────────────────────────────────
-- Checkpoint table for bulk scripts. Enables resume after interruption.
CREATE TABLE IF NOT EXISTS job_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name         TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'running',  -- running / completed / failed
    total_items      INTEGER NOT NULL DEFAULT 0,
    processed_items  INTEGER NOT NULL DEFAULT 0,
    failed_items     INTEGER NOT NULL DEFAULT 0,
    checkpoint_slug  TEXT,           -- last successfully processed slug
    started_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    completed_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_name_status ON job_runs(job_name, status);

-- ── write_log ────────────────────────────────────────────────────────────────
-- Rate-limit tracking. Query: count writes per target in last N hours.
CREATE TABLE IF NOT EXISTS write_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_url  TEXT NOT NULL,
    action      TEXT NOT NULL,
    written_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_wlog_target_time ON write_log(target_url, written_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def _conn(path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class SiteDB:
    """Per-site SQLite store. Instantiate once per SiteContext."""

    def __init__(self, site_dir: Path) -> None:
        self._path = site_dir / "data" / "site.db"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.debug("SiteDB initialised at %s", self._path)

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        with _conn(self._path) as conn:
            conn.executescript(_DDL)

    # ── pages ─────────────────────────────────────────────────────────────────

    def upsert_page(self, page: dict[str, Any]) -> None:
        """Insert or update a page record keyed by slug."""
        if "slug" not in page:
            raise ValueError("page dict must contain 'slug'")

        page = {**page, "updated_at": _now()}
        cols = ", ".join(page.keys())
        placeholders = ", ".join("?" * len(page))
        updates = ", ".join(
            f"{k}=excluded.{k}" for k in page if k not in ("slug", "created_at")
        )
        sql = (
            f"INSERT INTO pages ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(slug) DO UPDATE SET {updates}"
        )
        with _conn(self._path) as conn:
            conn.execute(sql, list(page.values()))

    def get_page(self, slug: str) -> dict[str, Any] | None:
        with _conn(self._path) as conn:
            row = conn.execute("SELECT * FROM pages WHERE slug=?", (slug,)).fetchone()
        return dict(row) if row else None

    def get_cluster_peers(
        self,
        cluster: str,
        exclude_slug: str,
        statuses: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Published pages in the same cluster — for internal link injection."""
        if statuses is None:
            statuses = ["published", "monitored"]
        placeholders = ",".join("?" * len(statuses))
        sql = (
            f"SELECT slug, url, title, primary_keyword FROM pages "
            f"WHERE cluster=? AND slug!=? AND status IN ({placeholders}) "
            f"ORDER BY published_at DESC LIMIT ?"
        )
        with _conn(self._path) as conn:
            rows = conn.execute(
                sql, [cluster, exclude_slug] + statuses + [limit]
            ).fetchall()
        return [dict(r) for r in rows]

    def count_by_status(self) -> dict[str, int]:
        with _conn(self._path) as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as n FROM pages GROUP BY status"
            ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def get_published_pages(self, limit: int = 500) -> list[dict[str, Any]]:
        with _conn(self._path) as conn:
            rows = conn.execute(
                "SELECT * FROM pages WHERE status IN ('published','monitored') "
                "ORDER BY published_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_page_flag(self, slug: str, flag: str, value: int = 1) -> None:
        """Set a 0/1 injection flag: faq_injected, meta_injected, etc."""
        allowed = {"faq_injected", "meta_injected", "internal_links_injected", "indexing_submitted"}
        if flag not in allowed:
            raise ValueError(f"Unknown flag: {flag!r}. Allowed: {allowed}")
        with _conn(self._path) as conn:
            conn.execute(
                f"UPDATE pages SET {flag}=?, updated_at=? WHERE slug=?",
                (value, _now(), slug),
            )

    # ── publish_log ───────────────────────────────────────────────────────────

    def log_publish(
        self,
        slug: str,
        action: str,
        wp_post_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        with _conn(self._path) as conn:
            conn.execute(
                "INSERT INTO publish_log (slug, action, wp_post_id, details) VALUES (?,?,?,?)",
                (slug, action, wp_post_id, json.dumps(details or {})),
            )

    def get_publish_history(self, slug: str) -> list[dict[str, Any]]:
        with _conn(self._path) as conn:
            rows = conn.execute(
                "SELECT * FROM publish_log WHERE slug=? ORDER BY created_at DESC",
                (slug,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["details"])
            except (json.JSONDecodeError, TypeError):
                d["details"] = {}
            result.append(d)
        return result

    # ── aio_observations ──────────────────────────────────────────────────────

    def log_aio_observation(
        self,
        page_url: str,
        engine: str,
        query: str = "",
        was_cited: bool = False,
        citation_url: str = "",
        site_id: str = "",
        notes: str = "",
    ) -> None:
        with _conn(self._path) as conn:
            conn.execute(
                "INSERT INTO aio_observations "
                "(page_url, engine, query, was_cited, citation_url, site_id, notes) "
                "VALUES (?,?,?,?,?,?,?)",
                (page_url, engine, query, int(was_cited), citation_url, site_id, notes),
            )

    def get_aio_citation_rate(self, page_url: str | None = None) -> dict[str, Any]:
        """Return citation rate overall or for a specific page."""
        with _conn(self._path) as conn:
            if page_url:
                row = conn.execute(
                    "SELECT engine, COUNT(*) as total, SUM(was_cited) as cited "
                    "FROM aio_observations WHERE page_url=? GROUP BY engine",
                    (page_url,),
                ).fetchall()
            else:
                row = conn.execute(
                    "SELECT engine, COUNT(*) as total, SUM(was_cited) as cited "
                    "FROM aio_observations GROUP BY engine"
                ).fetchall()
        return {
            r["engine"]: {
                "total": r["total"],
                "cited": r["cited"] or 0,
                "rate": round((r["cited"] or 0) / r["total"], 4) if r["total"] else 0,
            }
            for r in row
        }

    def migrate_aio_from_db(self, source_db_path: Path) -> int:
        """One-time migration from standalone aio_observations.db."""
        if not source_db_path.exists():
            logger.warning("AIO source DB not found: %s", source_db_path)
            return 0

        src_conn = sqlite3.connect(str(source_db_path))
        src_conn.row_factory = sqlite3.Row
        rows = src_conn.execute("SELECT * FROM aio_observations").fetchall()
        src_conn.close()

        count = 0
        with _conn(self._path) as conn:
            for r in rows:
                conn.execute(
                    "INSERT OR IGNORE INTO aio_observations "
                    "(page_url, engine, query, was_cited, citation_url, site_id, notes, observed_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        r["page_url"], r["engine"], r["query"],
                        r["was_cited"], r["citation_url"],
                        r["site_id"], r["notes"], r["observed_at"],
                    ),
                )
                count += 1
        logger.info("AIO migration: %d rows imported from %s", count, source_db_path)
        return count

    # ── job_runs ──────────────────────────────────────────────────────────────

    def start_job(self, job_name: str, total_items: int) -> int:
        """Create a new job_run record. Returns job_id."""
        with _conn(self._path) as conn:
            cur = conn.execute(
                "INSERT INTO job_runs (job_name, total_items) VALUES (?,?)",
                (job_name, total_items),
            )
        return cur.lastrowid  # type: ignore[return-value]

    def checkpoint_job(self, job_id: int, slug: str, *, failed: bool = False) -> None:
        """Update progress after processing one item."""
        fail_col = "failed_items = failed_items + 1, " if failed else ""
        with _conn(self._path) as conn:
            conn.execute(
                f"UPDATE job_runs SET {fail_col}"
                "processed_items = processed_items + 1, checkpoint_slug=? "
                "WHERE id=?",
                (slug, job_id),
            )

    def complete_job(self, job_id: int, *, status: str = "completed") -> None:
        with _conn(self._path) as conn:
            conn.execute(
                "UPDATE job_runs SET status=?, completed_at=? WHERE id=?",
                (status, _now(), job_id),
            )

    def get_resume_checkpoint(self, job_name: str) -> str | None:
        """Return checkpoint_slug of the most recent interrupted run, or None."""
        with _conn(self._path) as conn:
            row = conn.execute(
                "SELECT checkpoint_slug FROM job_runs "
                "WHERE job_name=? AND status='running' "
                "ORDER BY id DESC LIMIT 1",
                (job_name,),
            ).fetchone()
        return row["checkpoint_slug"] if row else None

    def list_jobs(self, job_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        sql = "SELECT * FROM job_runs"
        params: list[Any] = []
        if job_name:
            sql += " WHERE job_name=?"
            params.append(job_name)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with _conn(self._path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ── write_log (rate limiting) ─────────────────────────────────────────────

    def count_writes(self, target_url: str, hours: int) -> int:
        with _conn(self._path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM write_log "
                "WHERE target_url=? AND replace(replace(written_at,'T',' '),'Z','') > datetime('now', ?)",
                (target_url, f"-{hours} hours"),
            ).fetchone()
        return row["n"] if row else 0

    def record_write(self, target_url: str, action: str) -> None:
        with _conn(self._path) as conn:
            conn.execute(
                "INSERT INTO write_log (target_url, action) VALUES (?,?)",
                (target_url, action),
            )

    # ── migration helpers ─────────────────────────────────────────────────────

    def migrate_page_registry(self, registry_path: Path) -> int:
        """One-time import of page_registry.json → pages table.
        Skips records whose slug already exists.
        """
        if not registry_path.exists():
            logger.warning("Registry not found: %s", registry_path)
            return 0

        data = json.loads(registry_path.read_text())
        records: list[dict] = data.get("records", data) if isinstance(data, dict) else data

        count = 0
        for rec in records:
            slug = rec.get("slug", "").strip()
            if not slug:
                continue
            page = {
                "slug":                 slug,
                "keyword":              rec.get("keyword", ""),
                "page_type":            rec.get("page_type", "landing_page"),
                "intent":               rec.get("intent", "informational"),
                "cluster":              rec.get("cluster", ""),
                "primary_keyword":      rec.get("primary_keyword", rec.get("keyword", "")),
                "wp_post_id":           rec.get("published_post_id"),
                "url":                  rec.get("url", rec.get("wp_post_url", "")),
                "title":                rec.get("title", ""),
                "status":               rec.get("status", "pending"),
                "template_version":     rec.get("template_version", ""),
                "product_rule_version": rec.get("product_rule_version", ""),
                "brief_id":             rec.get("brief_id", ""),
                "blocking_reason":      rec.get("blocking_reason"),
                "notes":                rec.get("notes", ""),
                "word_count":           rec.get("word_count"),
                "published_at":         rec.get("published_at"),
                "created_at":           rec.get("created_at", _now()),
                "updated_at":           rec.get("updated_at", _now()),
            }
            try:
                with _conn(self._path) as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO pages "
                        "(slug, keyword, page_type, intent, cluster, primary_keyword, "
                        "wp_post_id, url, title, status, template_version, "
                        "product_rule_version, brief_id, blocking_reason, notes, "
                        "word_count, published_at, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            page["slug"], page["keyword"], page["page_type"],
                            page["intent"], page["cluster"], page["primary_keyword"],
                            page["wp_post_id"], page["url"], page["title"],
                            page["status"], page["template_version"],
                            page["product_rule_version"], page["brief_id"],
                            page["blocking_reason"], page["notes"],
                            page["word_count"], page["published_at"],
                            page["created_at"], page["updated_at"],
                        ),
                    )
                count += 1
            except Exception as exc:
                logger.warning("Skipping slug %r: %s", slug, exc)

        logger.info("Registry migration: %d/%d records imported", count, len(records))
        return count
