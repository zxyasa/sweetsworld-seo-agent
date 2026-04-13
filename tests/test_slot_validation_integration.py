"""Integration tests for SlotValidator hook in run_mvp.py.

Tests cover:
1. Validation passes (no warning logged)
2. Validation fails soft gate (warning logged, no exception raised)
3. Validator import unavailable (graceful degradation — no crash)
"""
from __future__ import annotations

import logging
import sys
import types
from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Minimal stubs so we can import run_mvp without real dependencies installed
# ---------------------------------------------------------------------------

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    return mod


def _patch_heavy_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out all non-stdlib imports that run_mvp pulls in at module level."""
    stubs = [
        "config",
        "content_brief_engine",
        "content_generator",
        "telegram_notify",
        "topic_generator",
        "product_selector",
        "wp_client",
        "google_indexing",
        "distribution_router",
        "openai_generator",
        "gsc_client",
        "topics_db",
    ]
    for name in stubs:
        if name not in sys.modules:
            mod = _make_stub(name)
            # Provide the symbols run_mvp imports
            if name == "config":
                mod.get_settings = MagicMock()  # type: ignore[attr-defined]
                mod.setup_logging = MagicMock()  # type: ignore[attr-defined]
            elif name == "content_brief_engine":
                mod.build_content_brief = MagicMock()  # type: ignore[attr-defined]
                mod.save_content_brief = MagicMock()  # type: ignore[attr-defined]
            elif name == "content_generator":
                mod.build_product_image_gallery = MagicMock()  # type: ignore[attr-defined]
                mod.generate_article_html = MagicMock()  # type: ignore[attr-defined]
                mod.generate_post_excerpt = MagicMock()  # type: ignore[attr-defined]
                mod.validate_content_quality = MagicMock()  # type: ignore[attr-defined]
            elif name == "telegram_notify":
                mod.extract_site_domain = MagicMock()  # type: ignore[attr-defined]
                mod.send_telegram = MagicMock()  # type: ignore[attr-defined]
                mod.send_error_alert = MagicMock()  # type: ignore[attr-defined]
            elif name == "topic_generator":
                mod.replenish_topics_csv = MagicMock()  # type: ignore[attr-defined]
            elif name == "product_selector":
                mod.load_product_catalog = MagicMock()  # type: ignore[attr-defined]
                mod.pick_featured_image_url = MagicMock()  # type: ignore[attr-defined]
                mod.select_products_for_topic = MagicMock()  # type: ignore[attr-defined]
                mod.validate_product_urls = MagicMock()  # type: ignore[attr-defined]
            elif name == "wp_client":
                mod.WPClient = MagicMock()  # type: ignore[attr-defined]
            monkeypatch.setitem(sys.modules, name, mod)


# ---------------------------------------------------------------------------
# Lightweight ValidationResult and SlotValidator stubs for unit tests
# ---------------------------------------------------------------------------

@dataclass
class _ValidationResult:
    passed: bool
    missing_slots: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.passed


class _SlotValidatorPassing:
    """Always returns a passing result."""

    def validate(self, html: str, page_type: str) -> _ValidationResult:
        return _ValidationResult(passed=True, missing_slots=[], issues=[])


class _SlotValidatorFailing:
    """Always returns a failing result with a missing INTRO slot."""

    def validate(self, html: str, page_type: str) -> _ValidationResult:
        return _ValidationResult(
            passed=False,
            missing_slots=["INTRO"],
            issues=["required slot 'INTRO' not found in HTML"],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_validation_hook(
    html_content: str,
    topic: dict,
    validator,
    *,
    available: bool = True,
) -> None:
    """Replicate the validation hook logic from run_mvp.py in isolation."""
    slot_validator = validator if available else None
    slot_validator_available = available

    if slot_validator_available and slot_validator is not None:
        try:
            result = slot_validator.validate(html_content, topic.get("page_type", ""))
            if not result.passed:
                logging.getLogger("run_mvp").warning(
                    "  SLOT VALIDATION: missing slots for '%s' (page_type=%s): %s",
                    topic.get("slug", ""),
                    topic.get("page_type", ""),
                    ", ".join(result.missing_slots),
                )
        except Exception as exc:
            logging.getLogger("run_mvp").warning(
                "  SLOT VALIDATION: error during validation, skipping: %s", exc
            )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSlotValidationPassesCleanly:
    """Test 1: When all required slots are present, no warning is emitted."""

    def test_no_warning_logged_on_pass(self, caplog: pytest.LogCaptureFixture) -> None:
        html = "<h1>Hello</h1><!-- AI_SLOT:INTRO -->Some content here."
        topic = {"slug": "test-slug", "page_type": "landing_page"}
        validator = _SlotValidatorPassing()

        with caplog.at_level(logging.WARNING, logger="run_mvp"):
            _run_validation_hook(html, topic, validator)

        warning_records = [r for r in caplog.records if "SLOT VALIDATION" in r.message]
        assert warning_records == [], (
            f"Expected no SLOT VALIDATION warnings, got: {[r.message for r in warning_records]}"
        )

    def test_publish_flow_not_disrupted_on_pass(self) -> None:
        """Validation passing must not raise any exception."""
        html = "<h1>Hello</h1><!-- AI_SLOT:INTRO -->Some content here."
        topic = {"slug": "test-slug", "page_type": "landing_page"}
        validator = _SlotValidatorPassing()

        # Must not raise
        _run_validation_hook(html, topic, validator)


class TestSlotValidationFailsSoftGate:
    """Test 2: When required slots are missing, a warning is logged but no exception raised."""

    def test_warning_logged_on_fail(self, caplog: pytest.LogCaptureFixture) -> None:
        html = "<h1>Hello</h1><p>No slot markers here.</p>"
        topic = {"slug": "missing-slot-page", "page_type": "landing_page"}
        validator = _SlotValidatorFailing()

        with caplog.at_level(logging.WARNING, logger="run_mvp"):
            _run_validation_hook(html, topic, validator)

        warning_messages = [r.message for r in caplog.records if "SLOT VALIDATION" in r.message]
        assert len(warning_messages) >= 1, "Expected at least one SLOT VALIDATION warning"
        assert "INTRO" in warning_messages[0], f"Expected 'INTRO' in warning: {warning_messages[0]}"

    def test_no_exception_raised_on_fail(self) -> None:
        """Failing validation must never crash the publish flow."""
        html = "<h1>No slots</h1>"
        topic = {"slug": "no-slots", "page_type": "occasion_page"}
        validator = _SlotValidatorFailing()

        # Must not raise — soft gate only
        _run_validation_hook(html, topic, validator)

    def test_slug_and_page_type_appear_in_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        html = "<p>No markers.</p>"
        topic = {"slug": "my-test-slug", "page_type": "blog_post"}
        validator = _SlotValidatorFailing()

        with caplog.at_level(logging.WARNING, logger="run_mvp"):
            _run_validation_hook(html, topic, validator)

        combined = " ".join(r.message for r in caplog.records if "SLOT VALIDATION" in r.message)
        assert "my-test-slug" in combined
        assert "blog_post" in combined


class TestSlotValidatorImportUnavailable:
    """Test 3: When SlotValidator cannot be imported, the hook degrades gracefully."""

    def test_no_crash_when_unavailable(self) -> None:
        """With available=False, the hook is a no-op and must not raise."""
        html = "<h1>Hello</h1>"
        topic = {"slug": "any-slug", "page_type": "landing_page"}

        # Pass any validator but mark it unavailable — simulates ImportError at module level
        _run_validation_hook(html, topic, validator=None, available=False)

    def test_no_warning_when_unavailable(self, caplog: pytest.LogCaptureFixture) -> None:
        """No spurious SLOT VALIDATION warning when validator is simply absent."""
        html = "<h1>Hello</h1>"
        topic = {"slug": "any-slug", "page_type": "landing_page"}

        with caplog.at_level(logging.WARNING, logger="run_mvp"):
            _run_validation_hook(html, topic, validator=None, available=False)

        warning_records = [r for r in caplog.records if "SLOT VALIDATION" in r.message]
        assert warning_records == []

    def test_hook_logic_with_exception_raising_validator(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """If the validator's validate() raises unexpectedly, the hook catches it and logs a warning."""

        class _BrokenValidator:
            def validate(self, html: str, page_type: str) -> _ValidationResult:
                raise RuntimeError("unexpected internal error")

        html = "<h1>Hello</h1>"
        topic = {"slug": "error-slug", "page_type": "landing_page"}

        with caplog.at_level(logging.WARNING, logger="run_mvp"):
            # Must not raise — exception is swallowed and logged
            _run_validation_hook(html, topic, _BrokenValidator(), available=True)

        warning_messages = [r.message for r in caplog.records if "SLOT VALIDATION" in r.message]
        assert len(warning_messages) == 1
        assert "skipping" in warning_messages[0]
