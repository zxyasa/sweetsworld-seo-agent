"""Tests for the _take_pre_publish_snapshot helper in run_mvp.py.

All tests mock the WP REST API — no real HTTP calls are made.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Make src/ importable
# ---------------------------------------------------------------------------
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from run_mvp import _take_pre_publish_snapshot  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wp_client(existing_post: dict | None = None) -> MagicMock:
    """Return a mock WPClient whose find_post_by_slug returns *existing_post*."""
    client = MagicMock()
    client.find_post_by_slug.return_value = existing_post
    return client


def _existing_post(slug: str = "test-slug") -> dict:
    return {
        "id": 42,
        "title": {"rendered": "Test Title"},
        "content": {"rendered": "<p>Hello world</p>"},
        "excerpt": {"rendered": "Short excerpt."},
        "modified": "2026-04-08T10:00:00",
        "status": "publish",
        "link": f"https://example.com/{slug}/",
    }


# ---------------------------------------------------------------------------
# Test 1 — new post: no snapshot file written, only debug log
# ---------------------------------------------------------------------------

def test_new_post_skips_snapshot(tmp_path):
    """When find_post_by_slug returns None, no snapshot file should be created."""
    client = _make_wp_client(existing_post=None)

    _take_pre_publish_snapshot(
        wp_client=client,
        slug="brand-new-slug",
        project_root=tmp_path,
        dry_run=False,
    )

    snapshot_dir = tmp_path / "snapshots" / "pre_publish"
    assert not snapshot_dir.exists() or list(snapshot_dir.iterdir()) == [], (
        "No snapshot files should be created for a brand-new post"
    )
    client.find_post_by_slug.assert_called_once_with("brand-new-slug")


# ---------------------------------------------------------------------------
# Test 2 — existing post: snapshot file is written with correct fields
# ---------------------------------------------------------------------------

def test_existing_post_writes_snapshot(tmp_path):
    """When a post already exists, a snapshot JSON file must be saved."""
    post = _existing_post("buy-candy-online")
    client = _make_wp_client(existing_post=post)

    _take_pre_publish_snapshot(
        wp_client=client,
        slug="buy-candy-online",
        project_root=tmp_path,
        dry_run=False,
    )

    snapshot_dir = tmp_path / "snapshots" / "pre_publish"
    files = list(snapshot_dir.iterdir())
    assert len(files) == 1, "Exactly one snapshot file should exist"

    data = json.loads(files[0].read_text(encoding="utf-8"))

    assert data["snapshot_type"] == "pre_publish"
    assert data["slug"] == "buy-candy-online"
    assert data["post_id"] == 42
    assert data["title"] == "Test Title"
    assert data["excerpt"] == "Short excerpt."
    assert data["wp_modified"] == "2026-04-08T10:00:00"
    assert "captured_at" in data and len(data["captured_at"]) > 10  # valid ISO timestamp


# ---------------------------------------------------------------------------
# Test 3 — content_length and content_hash are correct
# ---------------------------------------------------------------------------

def test_snapshot_content_metrics(tmp_path):
    """content_length and content_hash must match the rendered content."""
    post = _existing_post()
    rendered = "<p>Hello world</p>"
    post["content"]["rendered"] = rendered
    client = _make_wp_client(existing_post=post)

    _take_pre_publish_snapshot(
        wp_client=client,
        slug="test-slug",
        project_root=tmp_path,
        dry_run=False,
    )

    files = list((tmp_path / "snapshots" / "pre_publish").iterdir())
    data = json.loads(files[0].read_text(encoding="utf-8"))

    expected_bytes = rendered.encode("utf-8")
    assert data["content_length"] == len(expected_bytes)
    assert data["content_hash"] == hashlib.sha256(expected_bytes).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Test 4 — dry_run=True: no HTTP calls, no file written
# ---------------------------------------------------------------------------

def test_dry_run_skips_everything(tmp_path):
    """dry_run=True must bypass both the HTTP call and the file write."""
    client = _make_wp_client(existing_post=_existing_post())

    _take_pre_publish_snapshot(
        wp_client=client,
        slug="some-slug",
        project_root=tmp_path,
        dry_run=True,
    )

    client.find_post_by_slug.assert_not_called()
    snapshot_dir = tmp_path / "snapshots" / "pre_publish"
    assert not snapshot_dir.exists() or list(snapshot_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# Test 5 — WP API exception is caught, publish not blocked
# ---------------------------------------------------------------------------

def test_wp_api_error_is_non_blocking(tmp_path):
    """A WP API error must be logged as a warning and not raise."""
    client = MagicMock()
    client.find_post_by_slug.side_effect = RuntimeError("WP connection refused")

    # Must not raise
    _take_pre_publish_snapshot(
        wp_client=client,
        slug="error-slug",
        project_root=tmp_path,
        dry_run=False,
    )

    snapshot_dir = tmp_path / "snapshots" / "pre_publish"
    assert not snapshot_dir.exists() or list(snapshot_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# Test 6 — snapshot directory is auto-created
# ---------------------------------------------------------------------------

def test_snapshot_directory_is_created_automatically(tmp_path):
    """The snapshots/pre_publish directory must be created if it does not exist."""
    post = _existing_post("candy-gifts")
    client = _make_wp_client(existing_post=post)
    project_root = tmp_path / "nonexistent_project"  # does not exist yet

    _take_pre_publish_snapshot(
        wp_client=client,
        slug="candy-gifts",
        project_root=project_root,
        dry_run=False,
    )

    snapshot_dir = project_root / "snapshots" / "pre_publish"
    assert snapshot_dir.is_dir()
    assert len(list(snapshot_dir.iterdir())) == 1


# ---------------------------------------------------------------------------
# Test 7 — missing title/excerpt/content fields handled gracefully
# ---------------------------------------------------------------------------

def test_snapshot_handles_missing_wp_fields(tmp_path):
    """A post with None/missing rendered fields must not raise."""
    post = {
        "id": 99,
        "title": None,
        "content": None,
        "excerpt": None,
        "modified": None,
    }
    client = _make_wp_client(existing_post=post)

    _take_pre_publish_snapshot(
        wp_client=client,
        slug="minimal-post",
        project_root=tmp_path,
        dry_run=False,
    )

    files = list((tmp_path / "snapshots" / "pre_publish").iterdir())
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["post_id"] == 99
    assert data["content_length"] == 0
