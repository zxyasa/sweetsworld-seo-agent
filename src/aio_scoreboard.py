"""Append-only storage for SweetsWorld AI visibility probes.

This module is deliberately read-only with respect to the website.  It stores
API probe evidence in the site-local SQLite database and never calls WordPress.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Iterable


_SCHEMA = """
CREATE TABLE IF NOT EXISTS aio_probe_runs (
    run_id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    basket_version TEXT NOT NULL,
    trigger TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS aio_probe_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    query TEXT NOT NULL,
    provider TEXT NOT NULL,
    surface TEXT NOT NULL,
    model TEXT NOT NULL,
    model_version TEXT NOT NULL DEFAULT '',
    location_json TEXT NOT NULL DEFAULT '{}',
    replicate_no INTEGER NOT NULL DEFAULT 1,
    answer_text TEXT NOT NULL DEFAULT '',
    answer_sha256 TEXT NOT NULL DEFAULT '',
    brand_mentioned INTEGER NOT NULL DEFAULT 0,
    brand_recommended INTEGER NOT NULL DEFAULT 0,
    domain_cited INTEGER NOT NULL DEFAULT 0,
    product_cited INTEGER NOT NULL DEFAULT 0,
    recommendation_position INTEGER,
    citation_urls_json TEXT NOT NULL DEFAULT '[]',
    source_urls_json TEXT NOT NULL DEFAULT '[]',
    competitors_json TEXT NOT NULL DEFAULT '[]',
    raw_response_path TEXT NOT NULL DEFAULT '',
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    estimated_cost_usd REAL,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    observed_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES aio_probe_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_aio_probe_run ON aio_probe_observations(run_id);
CREATE INDEX IF NOT EXISTS idx_aio_probe_period ON aio_probe_observations(observed_at);
CREATE INDEX IF NOT EXISTS idx_aio_probe_surface ON aio_probe_observations(provider, surface);
CREATE INDEX IF NOT EXISTS idx_aio_probe_prompt ON aio_probe_observations(prompt_id);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@contextmanager
def _conn(path: Path) -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(str(path))
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


@dataclass(frozen=True)
class ProbeObservation:
    run_id: str
    site_id: str
    prompt_id: str
    prompt_version: str
    query: str
    provider: str
    surface: str
    model: str
    replicate_no: int = 1
    model_version: str = ""
    location: dict[str, Any] = field(default_factory=dict)
    answer_text: str = ""
    brand_mentioned: bool = False
    brand_recommended: bool = False
    domain_cited: bool = False
    product_cited: bool = False
    recommendation_position: int | None = None
    citation_urls: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    error_code: str = ""
    error_message: str = ""
    observed_at: str = ""
    observation_id: str = ""


class AIOScoreboard:
    """Immutable evidence ledger for provider-specific AI search probes."""

    def __init__(self, db_path: str | Path, raw_dir: str | Path | None = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(raw_dir) if raw_dir else self.db_path.parent / "aio_raw"
        with _conn(self.db_path) as con:
            con.executescript(_SCHEMA)

    def start_run(self, site_id: str, basket_version: str, trigger: str = "manual") -> str:
        run_id = str(uuid.uuid4())
        with _conn(self.db_path) as con:
            con.execute(
                "INSERT INTO aio_probe_runs(run_id,site_id,basket_version,trigger,started_at) VALUES(?,?,?,?,?)",
                (run_id, site_id, basket_version, trigger, utc_now()),
            )
        return run_id

    def finish_run(self, run_id: str, status: str = "completed", notes: str = "") -> None:
        if status not in {"completed", "partial", "failed"}:
            raise ValueError(f"Invalid run status: {status}")
        with _conn(self.db_path) as con:
            con.execute(
                "UPDATE aio_probe_runs SET status=?,completed_at=?,notes=? WHERE run_id=?",
                (status, utc_now(), notes, run_id),
            )

    def log(self, observation: ProbeObservation, raw_response: Any | None = None) -> str:
        observed_at = observation.observed_at or utc_now()
        observation_id = observation.observation_id or str(uuid.uuid4())
        answer_hash = hashlib.sha256(observation.answer_text.encode("utf-8")).hexdigest()
        raw_path = ""
        if raw_response is not None:
            run_dir = self.raw_dir / observation.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            target = run_dir / f"{observation_id}.json"
            target.write_text(json.dumps(raw_response, ensure_ascii=False, indent=2), encoding="utf-8")
            raw_path = str(target)

        values = (
            observation_id, observation.run_id, observation.site_id,
            observation.prompt_id, observation.prompt_version, observation.query,
            observation.provider, observation.surface, observation.model,
            observation.model_version, _json(observation.location), observation.replicate_no,
            observation.answer_text, answer_hash, int(observation.brand_mentioned),
            int(observation.brand_recommended), int(observation.domain_cited),
            int(observation.product_cited), observation.recommendation_position,
            _json(observation.citation_urls), _json(observation.source_urls),
            _json(observation.competitors), raw_path, observation.latency_ms,
            observation.input_tokens, observation.output_tokens,
            observation.estimated_cost_usd, observation.error_code,
            observation.error_message, observed_at,
        )
        placeholders = ",".join("?" for _ in values)
        columns = """observation_id,run_id,site_id,prompt_id,prompt_version,query,
provider,surface,model,model_version,location_json,replicate_no,answer_text,
answer_sha256,brand_mentioned,brand_recommended,domain_cited,product_cited,
recommendation_position,citation_urls_json,source_urls_json,competitors_json,
raw_response_path,latency_ms,input_tokens,output_tokens,estimated_cost_usd,
error_code,error_message,observed_at""".replace("\n", "")
        with _conn(self.db_path) as con:
            con.execute(f"INSERT INTO aio_probe_observations({columns}) VALUES({placeholders})", values)
        return observation_id

    def rows(self, where: str = "", params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        sql = "SELECT * FROM aio_probe_observations"
        if where:
            sql += " WHERE " + where
        sql += " ORDER BY observed_at"
        with _conn(self.db_path) as con:
            result = [dict(row) for row in con.execute(sql, tuple(params)).fetchall()]
        for row in result:
            for key in ("location_json", "citation_urls_json", "source_urls_json", "competitors_json"):
                row[key[:-5] if key.endswith("_json") else key] = json.loads(row[key])
        return result

    def run_status(self, run_id: str) -> dict[str, Any] | None:
        with _conn(self.db_path) as con:
            row = con.execute("SELECT * FROM aio_probe_runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def runs(self, site_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        sql = "SELECT * FROM aio_probe_runs"
        params: list[Any] = []
        if site_id:
            sql += " WHERE site_id=?"
            params.append(site_id)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        with _conn(self.db_path) as con:
            return [dict(row) for row in con.execute(sql, params).fetchall()]
