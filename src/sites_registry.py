"""sites_registry.py — central cross-site operational registry.

Maintains sites.db at the sites/ root level.
Stores only operational metadata (last run, publish counts, status).
Never stores content — content lives in each site's own site.db.

Usage:
    from sites_registry import SitesRegistry
    reg = SitesRegistry()
    reg.register("sweetsworld", "SweetsWorld Australia", "https://sweetsworld.com.au")
    reg.record_publish("sweetsworld")
    print(reg.status_table())
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

_SITES_ROOT = Path(__file__).parent.parent / "sites"
_DB_PATH    = _SITES_ROOT / "sites.db"

_DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sites (
    site_id          TEXT PRIMARY KEY,
    display_name     TEXT NOT NULL,
    base_url         TEXT NOT NULL UNIQUE,
    site_dir         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'active',
    last_run_at      TEXT,
    last_publish_at  TEXT,
    total_published  INTEGER NOT NULL DEFAULT 0,
    registered_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS site_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id     TEXT NOT NULL REFERENCES sites(site_id),
    event_type  TEXT NOT NULL,
    details     TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_events_site ON site_events(site_id, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def _conn(path: Path) -> Generator[sqlite3.Connection, None, None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class SitesRegistry:
    """Central cross-site operational view. Thread-safe via SQLite WAL."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or _DB_PATH
        self._init()

    def _init(self) -> None:
        with _conn(self._path) as conn:
            conn.executescript(_DDL)

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        site_id: str,
        display_name: str,
        base_url: str,
        site_dir: Path | None = None,
    ) -> bool:
        """Register a site. Returns True if newly inserted, False if already exists."""
        dir_str = str(site_dir or (_SITES_ROOT / site_id))
        with _conn(self._path) as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO sites "
                "(site_id, display_name, base_url, site_dir) VALUES (?,?,?,?)",
                (site_id, display_name, base_url.rstrip("/"), dir_str),
            )
            if cur.rowcount:
                logger.info("Registered new site: %s (%s)", site_id, base_url)
                return True
            logger.debug("Site already registered: %s", site_id)
            return False

    def register_from_context(self, ctx: Any) -> bool:
        """Convenience: register directly from a SiteContext object."""
        return self.register(
            site_id      = ctx.site_id,
            display_name = ctx.display_name,
            base_url     = ctx.base_url,
            site_dir     = ctx.site_dir,
        )

    # ── Event recording ───────────────────────────────────────────────────────

    def record_run(self, site_id: str) -> None:
        """Call at the start of each daily run."""
        with _conn(self._path) as conn:
            conn.execute(
                "UPDATE sites SET last_run_at=? WHERE site_id=?",
                (_now(), site_id),
            )
            conn.execute(
                "INSERT INTO site_events (site_id, event_type) VALUES (?,?)",
                (site_id, "run"),
            )

    def record_publish(self, site_id: str, slug: str = "", wp_post_id: int | None = None) -> None:
        """Call after each successful publish."""
        details = json.dumps({"slug": slug, "wp_post_id": wp_post_id})
        with _conn(self._path) as conn:
            conn.execute(
                "UPDATE sites SET last_publish_at=?, total_published=total_published+1 "
                "WHERE site_id=?",
                (_now(), site_id),
            )
            conn.execute(
                "INSERT INTO site_events (site_id, event_type, details) VALUES (?,?,?)",
                (site_id, "publish", details),
            )

    def record_error(self, site_id: str, message: str) -> None:
        with _conn(self._path) as conn:
            conn.execute(
                "INSERT INTO site_events (site_id, event_type, details) VALUES (?,?,?)",
                (site_id, "error", json.dumps({"message": message[:500]})),
            )

    def set_status(self, site_id: str, status: str) -> None:
        """active | paused | error"""
        allowed = {"active", "paused", "error"}
        if status not in allowed:
            raise ValueError(f"Invalid status {status!r}. Allowed: {allowed}")
        with _conn(self._path) as conn:
            conn.execute(
                "UPDATE sites SET status=? WHERE site_id=?",
                (status, site_id),
            )
            conn.execute(
                "INSERT INTO site_events (site_id, event_type, details) VALUES (?,?,?)",
                (site_id, "status_change", json.dumps({"status": status})),
            )

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_site(self, site_id: str) -> dict[str, Any] | None:
        with _conn(self._path) as conn:
            row = conn.execute(
                "SELECT * FROM sites WHERE site_id=?", (site_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_sites(self, status: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM sites"
        params: list[Any] = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY site_id"
        with _conn(self._path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_all_base_urls(self) -> list[str]:
        """Used by publish_guard for cross-contamination check."""
        with _conn(self._path) as conn:
            rows = conn.execute("SELECT base_url FROM sites").fetchall()
        return [r["base_url"] for r in rows]

    def recent_events(self, site_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        sql = "SELECT * FROM site_events"
        params: list[Any] = []
        if site_id:
            sql += " WHERE site_id=?"
            params.append(site_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with _conn(self._path) as conn:
            rows = conn.execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["details"])
            except (json.JSONDecodeError, TypeError):
                d["details"] = {}
            result.append(d)
        return result

    def status_table(self) -> str:
        """Human-readable status table for CLI / Telegram summary."""
        sites = self.list_sites()
        if not sites:
            return "No sites registered."

        lines = [
            f"{'SITE':<20} {'STATUS':<8} {'PUBLISHED':>9} {'LAST PUBLISH':<22} {'LAST RUN':<22}",
            "-" * 85,
        ]
        for s in sites:
            lines.append(
                f"{s['site_id']:<20} {s['status']:<8} "
                f"{s['total_published']:>9} "
                f"{(s['last_publish_at'] or '—'):<22} "
                f"{(s['last_run_at'] or '—'):<22}"
            )
        return "\n".join(lines)


# ── publish_guard ─────────────────────────────────────────────────────────────

class ContentContaminationError(RuntimeError):
    """Raised when generated content contains another site's domain."""


def assert_no_cross_site_contamination(
    html: str,
    site_id: str,
    base_url: str,
    registry: SitesRegistry | None = None,
) -> None:
    """Abort if HTML contains any registered site's domain other than base_url.

    Call this immediately before WordPress publish.
    """
    reg = registry or SitesRegistry()
    all_urls = reg.get_all_base_urls()
    foreign = [u for u in all_urls if u != base_url and u in html]
    if foreign:
        raise ContentContaminationError(
            f"[{site_id}] Content contains foreign domain(s): {foreign}\n"
            "This is a data isolation violation — publish aborted."
        )


# ── Auto-sync from sites/ directory ──────────────────────────────────────────

def sync_from_disk(sites_root: Path | None = None) -> list[str]:
    """Scan sites/ directory and register any site with a valid site.json.

    Safe to call at startup — idempotent (INSERT OR IGNORE).
    Returns list of site_ids processed.
    """
    import json as _json
    root = sites_root or _SITES_ROOT
    reg = SitesRegistry()
    processed = []

    if not root.exists():
        return []

    for site_dir in sorted(root.iterdir()):
        cfg_path = site_dir / "site.json"
        if not site_dir.is_dir() or not cfg_path.exists():
            continue
        try:
            cfg = _json.loads(cfg_path.read_text())
            reg.register(
                site_id      = cfg["site_id"],
                display_name = cfg["display_name"],
                base_url     = cfg["base_url"],
                site_dir     = site_dir,
            )
            processed.append(cfg["site_id"])
        except Exception as exc:
            logger.warning("Could not register site from %s: %s", cfg_path, exc)

    return processed
