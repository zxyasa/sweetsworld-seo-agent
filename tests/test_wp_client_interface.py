"""Tests for WPClient's BasePublisher interface compliance.

Validates that WPClient has the required method signatures and that the
publish() / channel_name contract is honoured regardless of whether
website-os is importable.  All tests run without a real WordPress server —
HTTP calls are patched.
"""
from __future__ import annotations

import inspect
import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Make the src/ package importable when running pytest from repo root or the
# sweetsworld-seo-agent directory.
# ---------------------------------------------------------------------------
import os
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from wp_client import WPClient, _HAS_BASE_PUBLISHER  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> WPClient:
    return WPClient(
        base_url="https://example.com",
        username="admin",
        app_password="xxxx xxxx xxxx",
    )


class _FakePayload:
    """Minimal stand-in for PublishPayload when website-os is not importable."""
    slug = "test-slug"
    title = "Test Title"
    content_html = "<p>Hello</p>"
    excerpt = "A short excerpt."


# ---------------------------------------------------------------------------
# Interface: channel_name
# ---------------------------------------------------------------------------

class TestChannelName:
    def test_channel_name_is_wordpress(self):
        client = _make_client()
        assert client.channel_name == "wordpress"

    def test_channel_name_is_string(self):
        client = _make_client()
        assert isinstance(client.channel_name, str)


# ---------------------------------------------------------------------------
# Interface: publish() signature
# ---------------------------------------------------------------------------

class TestPublishSignature:
    def test_publish_method_exists(self):
        assert hasattr(WPClient, "publish")
        assert callable(WPClient.publish)

    def test_publish_accepts_dry_run_kwarg(self):
        sig = inspect.signature(WPClient.publish)
        assert "dry_run" in sig.parameters

    def test_publish_accepts_payload_arg(self):
        sig = inspect.signature(WPClient.publish)
        # First param is self, second is payload
        params = list(sig.parameters.keys())
        assert "payload" in params


# ---------------------------------------------------------------------------
# Interface: validate() and supports_page_type() (optional, but present in
# BasePublisher default implementation — WPClient should not break them)
# ---------------------------------------------------------------------------

class TestOptionalInterfaceMethods:
    def test_validate_method_exists_when_base_publisher_available(self):
        """validate() is provided by BasePublisher default impl."""
        if not _HAS_BASE_PUBLISHER:
            pytest.skip("BasePublisher not importable in this environment")
        client = _make_client()
        assert hasattr(client, "validate")

    def test_supports_page_type_when_base_publisher_available(self):
        if not _HAS_BASE_PUBLISHER:
            pytest.skip("BasePublisher not importable in this environment")
        client = _make_client()
        assert hasattr(client, "supports_page_type")
        # Default: all page types supported
        assert client.supports_page_type("landing_page") is True


# ---------------------------------------------------------------------------
# publish() dry-run behaviour
# ---------------------------------------------------------------------------

class TestPublishDryRun:
    def test_dry_run_returns_success(self):
        client = _make_client()
        result = client.publish(_FakePayload(), dry_run=True)
        # Result can be PublishResult or plain dict depending on import
        success = result.success if hasattr(result, "success") else result["success"]
        assert success is True

    def test_dry_run_does_not_call_requests(self):
        client = _make_client()
        with patch("wp_client.requests") as mock_requests:
            client.publish(_FakePayload(), dry_run=True)
            mock_requests.post.assert_not_called()

    def test_dry_run_result_has_dry_run_flag(self):
        client = _make_client()
        result = client.publish(_FakePayload(), dry_run=True)
        dry_run_flag = result.dry_run if hasattr(result, "dry_run") else result.get("dry_run")
        assert dry_run_flag is True


# ---------------------------------------------------------------------------
# publish() None payload
# ---------------------------------------------------------------------------

class TestPublishNonePayload:
    def test_none_payload_returns_failure(self):
        client = _make_client()
        result = client.publish(None)
        success = result.success if hasattr(result, "success") else result["success"]
        assert success is False

    def test_none_payload_includes_error_message(self):
        client = _make_client()
        result = client.publish(None)
        error = result.error if hasattr(result, "error") else result.get("error")
        assert error is not None
        assert "None" in error or "payload" in error.lower()


# ---------------------------------------------------------------------------
# publish() live path (mocked HTTP)
# ---------------------------------------------------------------------------

class TestPublishLivePath:
    def _mock_http(self):
        """Return a mock response factory that simulates WP REST API success."""
        draft_resp = MagicMock()
        draft_resp.status_code = 201
        draft_resp.json.return_value = {"id": 42, "link": "https://example.com/test-slug/"}
        draft_resp.raise_for_status = MagicMock()

        publish_resp = MagicMock()
        publish_resp.status_code = 200
        publish_resp.json.return_value = {
            "id": 42,
            "link": "https://example.com/test-slug/",
            "status": "publish",
        }
        publish_resp.raise_for_status = MagicMock()

        return draft_resp, publish_resp

    def test_successful_publish_returns_success(self):
        client = _make_client()
        draft_resp, publish_resp = self._mock_http()

        with patch.object(client, "_request_with_retry", side_effect=[draft_resp, publish_resp]):
            result = client.publish(_FakePayload(), dry_run=False)

        success = result.success if hasattr(result, "success") else result["success"]
        assert success is True

    def test_successful_publish_returns_url(self):
        client = _make_client()
        draft_resp, publish_resp = self._mock_http()

        with patch.object(client, "_request_with_retry", side_effect=[draft_resp, publish_resp]):
            result = client.publish(_FakePayload(), dry_run=False)

        url = result.published_url if hasattr(result, "published_url") else result.get("published_url")
        assert url == "https://example.com/test-slug/"

    def test_publish_exception_returns_failure(self):
        client = _make_client()
        import requests as _requests
        with patch.object(client, "create_post_draft", side_effect=_requests.HTTPError("WP error")):
            result = client.publish(_FakePayload(), dry_run=False)

        success = result.success if hasattr(result, "success") else result["success"]
        assert success is False

    def test_publish_exception_includes_error_text(self):
        client = _make_client()
        import requests as _requests
        with patch.object(client, "create_post_draft", side_effect=_requests.HTTPError("WP error")):
            result = client.publish(_FakePayload(), dry_run=False)

        error = result.error if hasattr(result, "error") else result.get("error")
        assert error is not None
        assert len(error) > 0


# ---------------------------------------------------------------------------
# Backwards compatibility: existing WPClient API still works
# ---------------------------------------------------------------------------

class TestBackwardsCompatibility:
    """Verify that adding BasePublisher did not break the pre-existing API."""

    def test_create_post_draft_still_exists(self):
        assert hasattr(WPClient, "create_post_draft")

    def test_publish_post_still_exists(self):
        assert hasattr(WPClient, "publish_post")

    def test_test_connection_still_exists(self):
        assert hasattr(WPClient, "test_connection")

    def test_get_categories_still_exists(self):
        assert hasattr(WPClient, "get_categories")

    def test_find_post_by_slug_still_exists(self):
        assert hasattr(WPClient, "find_post_by_slug")

    def test_constructor_still_works(self):
        client = _make_client()
        assert client.base_url == "https://example.com"
        assert client.username == "admin"
        assert "api_url" in dir(client)
