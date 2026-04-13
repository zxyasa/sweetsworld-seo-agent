"""SQLite-backed topic queue — drop-in replacement for topics.csv read/write.

Feature flag: set USE_TOPICS_DB=true in .env to enable.
Falls back to CSV when disabled or DB is missing.

Schema mirrors topics.csv columns plus status tracking fields.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS topics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    slug             TEXT    NOT NULL UNIQUE,
    title            TEXT    NOT NULL,
    primary_keyword  TEXT    NOT NULL,
    category_hint    TEXT    DEFAULT '',
    page_type        TEXT    NOT NULL DEFAULT 'landing_page',
    cluster          TEXT    DEFAULT '',
    priority         INTEGER DEFAULT 99,
    status           TEXT    NOT NULL DEFAULT 'pending',
    wp_post_id       INTEGER,
    wp_post_url      TEXT,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL,
    published_at     TEXT,
    quality_blocked  INTEGER DEFAULT 0,
    quality_reasons  TEXT    DEFAULT '[]',
    source           TEXT    DEFAULT 'csv_import'
);

CREATE INDEX IF NOT EXISTS idx_topics_status   ON topics(status);
CREATE INDEX IF NOT EXISTS idx_topics_cluster  ON topics(cluster);
CREATE INDEX IF NOT EXISTS idx_topics_priority ON topics(priority);
CREATE INDEX IF NOT EXISTS idx_topics_page_type ON topics(page_type);
"""

# Valid statuses (mirrors page_registry.json + run_mvp.py constants)
VALID_STATUSES = {
    "pending", "in_progress", "drafted", "review_pending",
    "approved", "published", "monitored", "blocked",
    "quality_blocked", "exists", "skipped",
}


@contextmanager
def _conn(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["quality_reasons"] = json.loads(d.get("quality_reasons") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["quality_reasons"] = []
    return d


class TopicsDB:
    """Thread-safe SQLite topic queue with CSV import/export compatibility."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with _conn(self.db_path) as con:
            con.executescript(_SCHEMA_SQL)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_topic(self, topic: Dict[str, Any], source: str = "manual") -> bool:
        """Insert a topic. Returns True if inserted, False if slug already exists."""
        slug = str(topic.get("slug", "")).strip()
        if not slug:
            raise ValueError("topic must have a non-empty slug")

        now = _now()
        try:
            with _conn(self.db_path) as con:
                con.execute(
                    """INSERT INTO topics
                       (slug, title, primary_keyword, category_hint, page_type,
                        cluster, priority, status, created_at, updated_at, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        slug,
                        str(topic.get("title", slug)).strip(),
                        str(topic.get("primary_keyword", slug)).strip(),
                        str(topic.get("category_hint", "")).strip(),
                        str(topic.get("page_type", "landing_page")).strip(),
                        str(topic.get("cluster", "")).strip(),
                        int(topic.get("priority", 99)),
                        str(topic.get("status", "pending")).strip(),
                        now,
                        now,
                        source,
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False  # duplicate slug

    def add_topics_bulk(self, topics: List[Dict[str, Any]], source: str = "bulk") -> Dict[str, int]:
        """Insert many topics. Returns {inserted, skipped}."""
        inserted = skipped = 0
        for t in topics:
            ok = self.add_topic(t, source=source)
            if ok:
                inserted += 1
            else:
                skipped += 1
        return {"inserted": inserted, "skipped": skipped}

    def mark_status(
        self,
        slug: str,
        status: str,
        *,
        wp_post_id: Optional[int] = None,
        wp_post_url: Optional[str] = None,
        quality_reasons: Optional[List[str]] = None,
    ) -> bool:
        """Update topic status and optional WP metadata. Returns True if found."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Valid: {VALID_STATUSES}")

        now = _now()
        published_at = now if status == "published" else None
        quality_blocked = 1 if status == "quality_blocked" else 0
        reasons_json = json.dumps(quality_reasons or [])

        with _conn(self.db_path) as con:
            result = con.execute(
                """UPDATE topics
                   SET status=?, updated_at=?,
                       wp_post_id=COALESCE(?, wp_post_id),
                       wp_post_url=COALESCE(?, wp_post_url),
                       published_at=COALESCE(?, published_at),
                       quality_blocked=?,
                       quality_reasons=CASE WHEN ? != '[]' THEN ? ELSE quality_reasons END
                   WHERE slug=?""",
                (
                    status, now,
                    wp_post_id, wp_post_url,
                    published_at,
                    quality_blocked,
                    reasons_json, reasons_json,
                    slug,
                ),
            )
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_pending_queue(
        self,
        limit: Optional[int] = None,
        slugs: Optional[List[str]] = None,
        page_type: Optional[str] = None,
        cluster: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return pending topics sorted by priority asc, created_at asc."""
        where_clauses = ["status = 'pending'"]
        params: List[Any] = []

        if slugs:
            placeholders = ",".join("?" * len(slugs))
            where_clauses.append(f"slug IN ({placeholders})")
            params.extend(slugs)
        if page_type:
            where_clauses.append("page_type = ?")
            params.append(page_type)
        if cluster:
            where_clauses.append("cluster = ?")
            params.append(cluster)

        where = " AND ".join(where_clauses)
        sql = f"SELECT * FROM topics WHERE {where} ORDER BY priority ASC, created_at ASC"
        if limit:
            sql += f" LIMIT {limit}"

        with _conn(self.db_path) as con:
            rows = con.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        with _conn(self.db_path) as con:
            row = con.execute("SELECT * FROM topics WHERE slug=?", (slug,)).fetchone()
        return _row_to_dict(row) if row else None

    def get_cluster_peers(
        self, cluster: str, statuses: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Return published/monitored pages in the same cluster (for internal linking)."""
        if statuses is None:
            statuses = ["published", "monitored"]
        placeholders = ",".join("?" * len(statuses))
        sql = f"SELECT * FROM topics WHERE cluster=? AND status IN ({placeholders})"
        with _conn(self.db_path) as con:
            rows = con.execute(sql, [cluster] + statuses).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count_by_status(self) -> Dict[str, int]:
        with _conn(self.db_path) as con:
            rows = con.execute(
                "SELECT status, COUNT(*) as n FROM topics GROUP BY status"
            ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def count_pending(self) -> int:
        with _conn(self.db_path) as con:
            row = con.execute(
                "SELECT COUNT(*) as n FROM topics WHERE status='pending'"
            ).fetchone()
        return row["n"] if row else 0

    def slug_exists(self, slug: str) -> bool:
        with _conn(self.db_path) as con:
            row = con.execute(
                "SELECT 1 FROM topics WHERE slug=?", (slug,)
            ).fetchone()
        return row is not None

    def get_all_slugs(self) -> List[str]:
        with _conn(self.db_path) as con:
            rows = con.execute("SELECT slug FROM topics").fetchall()
        return [r["slug"] for r in rows]

    def get_published(self) -> List[Dict[str, Any]]:
        with _conn(self.db_path) as con:
            rows = con.execute(
                "SELECT * FROM topics WHERE status IN ('published','monitored') ORDER BY published_at DESC"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # CSV import / export
    # ------------------------------------------------------------------

    def migrate_from_csv(self, csv_path: str, source: str = "csv_import") -> Dict[str, int]:
        """Import all rows from topics.csv. Skips existing slugs."""
        path = Path(csv_path)
        if not path.exists():
            return {"inserted": 0, "skipped": 0, "error": "file not found"}

        topics: List[Dict[str, Any]] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                topics.append({
                    "slug": row.get("slug", "").strip(),
                    "title": row.get("title", "").strip(),
                    "primary_keyword": row.get("primary_keyword", "").strip(),
                    "category_hint": row.get("category_hint", "").strip(),
                    "page_type": row.get("page_type", "landing_page").strip(),
                    "cluster": row.get("cluster", "").strip(),
                    "priority": int(row.get("priority") or 99),
                    "status": "pending",
                })

        result = self.add_topics_bulk(topics, source=source)
        logger.info(f"CSV migration: inserted={result['inserted']}, skipped={result['skipped']}")
        return result

    def export_csv(self, output_path: str) -> int:
        """Export all topics to CSV (compatible with topics.csv format)."""
        fields = ["slug", "title", "primary_keyword", "category_hint", "page_type", "cluster", "priority"]
        with _conn(self.db_path) as con:
            rows = con.execute(
                "SELECT * FROM topics ORDER BY priority ASC, created_at ASC"
            ).fetchall()

        out = Path(output_path)
        tmp = out.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: dict(row).get(k, "") for k in fields})
        os.replace(tmp, out)
        return len(rows)


# ------------------------------------------------------------------
# Feature-flag-aware factory
# ------------------------------------------------------------------

def get_topics_db(db_path: Optional[str] = None) -> Optional[TopicsDB]:
    """Return a TopicsDB if USE_TOPICS_DB=true, otherwise None.

    Callers that get None should fall back to CSV-based logic.
    """
    enabled = os.getenv("USE_TOPICS_DB", "false").lower() in ("true", "1", "yes")
    if not enabled:
        return None

    if db_path is None:
        # Try site registry first
        try:
            from pathlib import Path as _Path
            registry_path = _Path(__file__).parent.parent.parent.parent.parent / "apps" / "growth-graph" / "site_registry.json"
            if registry_path.exists():
                import json as _json
                with open(registry_path) as _f:
                    _data = _json.load(_f)
                db_path = _data["sites"]["sweetsworld"]["topics_db"]
        except Exception:
            pass

    if db_path is None:
        # Default relative to this file
        db_path = str(Path(__file__).parent.parent / "data" / "topics.db")

    return TopicsDB(db_path)
