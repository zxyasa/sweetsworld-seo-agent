import sqlite3

import pytest

from aio_scoreboard import AIOScoreboard, ProbeObservation


def make_obs(run_id: str, **overrides):
    values = {
        "run_id": run_id,
        "site_id": "sweetsworld",
        "prompt_id": "gift-001",
        "prompt_version": "1.0",
        "query": "best Australian candy gift box",
        "provider": "openai",
        "surface": "responses_web_search_api",
        "model": "test-model",
    }
    values.update(overrides)
    return ProbeObservation(**values)


def test_creates_append_only_tables(tmp_path):
    db = tmp_path / "site.db"
    AIOScoreboard(db)
    with sqlite3.connect(db) as con:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"aio_probe_runs", "aio_probe_observations"} <= tables


def test_repeated_prompt_is_never_overwritten(tmp_path):
    board = AIOScoreboard(tmp_path / "site.db")
    run_id = board.start_run("sweetsworld", "1.0")
    board.log(make_obs(run_id, replicate_no=1, domain_cited=False))
    board.log(make_obs(run_id, replicate_no=2, domain_cited=True))
    rows = board.rows("run_id=?", (run_id,))
    assert len(rows) == 2
    assert [r["domain_cited"] for r in rows] == [0, 1]


def test_raw_evidence_is_saved_without_credentials(tmp_path):
    board = AIOScoreboard(tmp_path / "site.db", tmp_path / "raw")
    run_id = board.start_run("sweetsworld", "1.0")
    obs_id = board.log(make_obs(run_id, answer_text="SweetsWorld is cited."), {"output": "safe"})
    row = board.rows("observation_id=?", (obs_id,))[0]
    assert row["answer_sha256"]
    assert row["raw_response_path"].endswith(f"{obs_id}.json")


def test_provider_surface_and_location_are_preserved(tmp_path):
    board = AIOScoreboard(tmp_path / "site.db")
    run_id = board.start_run("sweetsworld", "1.0")
    board.log(make_obs(run_id, location={"country": "AU", "city": "Sydney"}))
    row = board.rows("run_id=?", (run_id,))[0]
    assert row["surface"] == "responses_web_search_api"
    assert row["location"] == {"city": "Sydney", "country": "AU"}


def test_run_lifecycle(tmp_path):
    board = AIOScoreboard(tmp_path / "site.db")
    run_id = board.start_run("sweetsworld", "1.0", trigger="test")
    assert board.run_status(run_id)["status"] == "running"
    board.finish_run(run_id, "partial", "one provider unavailable")
    status = board.run_status(run_id)
    assert status["status"] == "partial"
    assert status["completed_at"]


def test_rejects_invalid_run_status(tmp_path):
    board = AIOScoreboard(tmp_path / "site.db")
    run_id = board.start_run("sweetsworld", "1.0")
    with pytest.raises(ValueError):
        board.finish_run(run_id, "unknown")

