"""Unit tests for pilot_gate.py — focusing on the GSC signal analysis layer
and its integration into evaluate_pilot_gate / render_markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.pilot_gate import (
    _analyze_ga4_signals,
    _analyze_gsc_signals,
    evaluate_pilot_gate,
    render_markdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_criteria(**gsc_overrides) -> Dict[str, Any]:
    base_gsc = {
        "ctr_check_min_impressions": 100,
        "min_ctr_pct": 1.0,
        "position_stuck_min": 5.0,
        "position_stuck_max": 10.9,
        "require_ctr_gate": False,
    }
    base_gsc.update(gsc_overrides)
    return {
        "pilot_scope": {
            "initial_publish_batch_min": 3,
            "initial_publish_batch_max": 500,
            "review_window_days": 14,
        },
        "manual_qa_requirements": {"minimum_pass_rate": 0.9},
        "expansion_gates": {
            "require_no_duplicate_publishes": True,
            "require_search_console_review": True,
            "require_indexation_signal": True,
            "require_query_intent_fit": True,
        },
        "gsc_quality": base_gsc,
    }


def _make_page(
    slug: str,
    impressions: int,
    clicks: int,
    ctr: float,
    position: float,
    sessions: int = 0,
    bounce_rate: float = 0.0,
    avg_session_duration_s: float = 60.0,
) -> Dict[str, Any]:
    page: Dict[str, Any] = {
        "slug": slug,
        "page_type": "landing_page",
        "post_link": f"https://example.com/{slug}/",
        "published_at": "2026-01-01T00:00:00+00:00",
        "issues": [],
        "gsc": {
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "position": position,
            "top_queries": [],
        },
        "ga4": None,
    }
    if sessions > 0:
        page["ga4"] = {
            "sessions": sessions,
            "bounce_rate": bounce_rate,
            "avg_session_duration_s": avg_session_duration_s,
        }
    return page


def _make_report(pages, gsc_enabled=True) -> Dict[str, Any]:
    return {
        "generated_at": "2026-04-07T10:00:00+00:00",
        "gsc_enabled": gsc_enabled,
        "pages": pages,
    }


# ---------------------------------------------------------------------------
# _analyze_gsc_signals — unit tests
# ---------------------------------------------------------------------------


class TestAnalyzeGscSignals:
    def test_empty_report(self):
        result = _analyze_gsc_signals({}, _make_criteria())
        assert result["total_impressions"] == 0
        assert result["total_clicks"] == 0
        assert result["avg_ctr"] == 0.0
        assert result["avg_position"] == 0.0
        assert result["pages_with_impressions"] == 0
        assert result["pages_stuck_in_positions_5_to_10"] == 0
        assert result["content_upgrade_candidates"] == []
        # Not enough impressions → CTR check not applicable → passes
        assert result["ctr_check_applicable"] is False
        assert result["ctr_meets_threshold"] is True

    def test_pages_with_no_gsc(self):
        pages = [{"slug": "page-a", "gsc": None}, {"slug": "page-b"}]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria())
        assert result["total_impressions"] == 0
        assert result["pages_with_impressions"] == 0

    def test_basic_aggregation(self):
        pages = [
            _make_page("a", impressions=200, clicks=4, ctr=2.0, position=3.0),
            _make_page("b", impressions=100, clicks=1, ctr=1.0, position=12.0),
        ]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria())
        assert result["total_impressions"] == 300
        assert result["total_clicks"] == 5
        # avg_ctr from clicks/impressions
        assert result["avg_ctr"] == round(5 / 300 * 100, 2)
        # weighted avg position: (3.0*200 + 12.0*100) / 300
        assert result["avg_position"] == round((3.0 * 200 + 12.0 * 100) / 300, 2)
        assert result["pages_with_impressions"] == 2

    def test_pages_stuck_in_positions_5_to_10(self):
        pages = [
            _make_page("stuck-1", impressions=100, clicks=1, ctr=1.0, position=5.5),
            _make_page("stuck-2", impressions=100, clicks=1, ctr=1.0, position=10.0),
            _make_page("not-stuck", impressions=100, clicks=5, ctr=5.0, position=2.0),
            _make_page("below-range", impressions=100, clicks=2, ctr=2.0, position=11.5),
        ]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria())
        assert result["pages_stuck_in_positions_5_to_10"] == 2
        stuck_slugs = {p["slug"] for p in result["pages_stuck_detail"]}
        assert stuck_slugs == {"stuck-1", "stuck-2"}

    def test_pages_low_ctr(self):
        pages = [
            _make_page("low-ctr", impressions=50, clicks=0, ctr=0.0, position=3.0),
            _make_page("ok-ctr", impressions=50, clicks=2, ctr=4.0, position=3.0),
            # Below threshold impressions (< 20) — not checked for low CTR
            _make_page("too-few", impressions=10, clicks=0, ctr=0.0, position=3.0),
        ]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria())
        assert result["pages_low_ctr"] == 1
        assert result["pages_low_ctr_detail"][0]["slug"] == "low-ctr"

    def test_upgrade_candidates_deduplication(self):
        """A page stuck in positions 5-10 AND low CTR should appear once in candidates."""
        pages = [
            _make_page("both", impressions=50, clicks=0, ctr=0.0, position=7.0),
        ]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria())
        assert result["content_upgrade_candidates"].count("both") == 1

    def test_ctr_check_not_applicable_below_threshold(self):
        pages = [_make_page("p", impressions=50, clicks=0, ctr=0.0, position=1.0)]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria(ctr_check_min_impressions=100))
        assert result["ctr_check_applicable"] is False
        assert result["ctr_meets_threshold"] is True  # passes because check N/A

    def test_ctr_check_applicable_fails(self):
        # 200 impressions, 0 clicks → CTR = 0% < threshold 1%
        pages = [_make_page("p", impressions=200, clicks=0, ctr=0.0, position=1.0)]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria(ctr_check_min_impressions=100))
        assert result["ctr_check_applicable"] is True
        assert result["ctr_meets_threshold"] is False

    def test_ctr_check_applicable_passes(self):
        # 200 impressions, 4 clicks → CTR = 2% >= threshold 1%
        pages = [_make_page("p", impressions=200, clicks=4, ctr=2.0, position=1.0)]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria(ctr_check_min_impressions=100))
        assert result["ctr_check_applicable"] is True
        assert result["ctr_meets_threshold"] is True

    def test_pages_with_zero_impressions_excluded(self):
        pages = [
            _make_page("has-imp", impressions=100, clicks=2, ctr=2.0, position=4.0),
            _make_page("no-imp", impressions=0, clicks=0, ctr=0.0, position=0.0),
        ]
        result = _analyze_gsc_signals(_make_report(pages), _make_criteria())
        assert result["pages_with_impressions"] == 1
        assert result["total_impressions"] == 100


# ---------------------------------------------------------------------------
# evaluate_pilot_gate — integration tests with mocked collect_pilot_report
# ---------------------------------------------------------------------------

def _make_registry(published=5, approved=2):
    records = []
    for i in range(published):
        records.append({"slug": f"pub-{i}", "status": "published", "page_type": "landing_page"})
    for i in range(approved):
        records.append({"slug": f"app-{i}", "status": "approved", "page_type": "landing_page"})
    return {"records": records}


class TestEvaluatePilotGate:
    """Tests that gsc_signals are correctly incorporated into the gate decision."""

    def _run(self, report_pages, criteria=None, published=5, approved=2, registry=None, tmp_path=None):
        """Helper: run evaluate_pilot_gate with mocked data."""
        import tempfile, json as _json
        if criteria is None:
            criteria = _make_criteria()
        if registry is None:
            registry = _make_registry(published=published, approved=approved)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            crit_path = td / "criteria.json"
            reg_path = td / "registry.json"
            crit_path.write_text(_json.dumps(criteria))
            reg_path.write_text(_json.dumps(registry))

            report = _make_report(report_pages)

            with patch("src.pilot_gate.collect_pilot_report", return_value=report), \
                 patch("src.pilot_gate._site_host_is_resolvable", return_value=True):
                return evaluate_pilot_gate(
                    criteria_path=crit_path,
                    registry_path=reg_path,
                    days=7,
                )

    def test_gsc_performance_key_present(self):
        pages = [_make_page("p", 200, 4, 2.0, 3.0)]
        result = self._run(pages)
        assert "gsc_performance" in result
        assert result["gsc_performance"]["avg_ctr"] == round(4 / 200 * 100, 2)

    def test_summary_includes_new_fields(self):
        pages = [_make_page("p", 200, 4, 2.0, 7.0)]  # stuck in 5-10
        result = self._run(pages)
        s = result["summary"]
        assert "avg_ctr" in s
        assert "avg_position" in s
        assert "pages_with_impressions" in s
        assert "pages_stuck_in_positions_5_to_10" in s
        assert "content_upgrade_count" in s
        assert s["pages_stuck_in_positions_5_to_10"] == 1

    def test_ctr_check_in_checks(self):
        pages = [_make_page("p", 200, 4, 2.0, 3.0)]
        result = self._run(pages)
        assert "ctr_meets_threshold" in result["checks"]

    def test_require_ctr_gate_false_does_not_block(self):
        """With require_ctr_gate=False (default), low CTR should not block expansion."""
        pages = [_make_page("p", 200, 0, 0.0, 3.0)]  # 0% CTR
        criteria = _make_criteria(require_ctr_gate=False)
        result = self._run(pages, criteria=criteria)
        blocking = result["blocking_reasons"]
        assert not any("CTR" in r for r in blocking)
        assert result["checks"]["ctr_meets_threshold"] is False  # check is False

    def test_require_ctr_gate_true_blocks_when_ctr_low(self):
        """With require_ctr_gate=True, low CTR should add a blocking reason."""
        pages = [_make_page("p", 200, 0, 0.0, 3.0)]  # 0% CTR, 200 impressions
        criteria = _make_criteria(require_ctr_gate=True, ctr_check_min_impressions=100)
        result = self._run(pages, criteria=criteria)
        assert any("CTR" in r for r in result["blocking_reasons"])
        assert result["decision"] == "hold"

    def test_require_ctr_gate_true_passes_when_ctr_ok(self):
        pages = [_make_page("p", 200, 4, 2.0, 3.0)]  # 2% CTR
        criteria = _make_criteria(require_ctr_gate=True, ctr_check_min_impressions=100)
        # Need enough published pages and clicks for other gates to clear
        result = self._run(pages, criteria=criteria)
        assert not any("CTR" in r for r in result["blocking_reasons"])

    def test_upgrade_suffix_in_next_action(self):
        """next_action should mention upgrade candidates when any exist."""
        pages = [_make_page("stuck", 200, 0, 0.0, 7.5)]  # stuck at 7.5, low CTR
        result = self._run(pages)
        assert "upgrade candidate" in result["next_action"].lower()

    def test_no_upgrade_suffix_when_none(self):
        pages = [_make_page("good", 200, 10, 5.0, 2.0)]  # great CTR, good position
        result = self._run(pages)
        assert "upgrade candidate" not in result["next_action"].lower()


# ---------------------------------------------------------------------------
# render_markdown — smoke tests
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def _make_decision(self, pages=None):
        if pages is None:
            pages = [_make_page("p", 150, 3, 2.0, 7.5)]
        criteria = _make_criteria()
        registry = _make_registry(published=5, approved=2)

        import tempfile, json as _json
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            crit_path = td / "criteria.json"
            reg_path = td / "registry.json"
            crit_path.write_text(_json.dumps(criteria))
            reg_path.write_text(_json.dumps(registry))
            report = _make_report(pages)
            with patch("src.pilot_gate.collect_pilot_report", return_value=report), \
                 patch("src.pilot_gate._site_host_is_resolvable", return_value=True):
                return evaluate_pilot_gate(criteria_path=crit_path, registry_path=reg_path, days=7)

    def test_gsc_performance_section_present(self):
        decision = self._make_decision()
        md = render_markdown(decision)
        assert "## GSC Performance Analysis" in md

    def test_stuck_pages_listed(self):
        decision = self._make_decision([_make_page("stuck-p", 150, 1, 0.7, 6.5)])
        md = render_markdown(decision)
        assert "stuck-p" in md
        assert "Positions 5-10" in md

    def test_no_candidates_message(self):
        decision = self._make_decision([_make_page("good-p", 150, 10, 6.7, 2.0)])
        md = render_markdown(decision)
        assert "No content upgrade candidates identified" in md

    def test_ctr_check_inactive_label(self):
        # Only 50 impressions — below the 100 threshold
        decision = self._make_decision([_make_page("p", 50, 1, 2.0, 3.0)])
        md = render_markdown(decision)
        assert "inactive" in md

    def test_ctr_check_active_label(self):
        # 200 impressions — above the 100 threshold
        decision = self._make_decision([_make_page("p", 200, 4, 2.0, 3.0)])
        md = render_markdown(decision)
        assert "active" in md


# ---------------------------------------------------------------------------
# _analyze_ga4_signals — unit tests
# ---------------------------------------------------------------------------


def _ga4_criteria(**overrides) -> Dict[str, Any]:
    base = {
        "min_sessions_for_check": 50,
        "max_bounce_rate": 0.70,
        "min_session_duration_s": 30.0,
        "min_page_sessions_for_rule": 10,
        "require_engagement_gate": False,
    }
    base.update(overrides)
    return {**_make_criteria(), "ga4_quality": base}


class TestAnalyzeGa4Signals:
    def test_empty_report(self):
        result = _analyze_ga4_signals({}, _ga4_criteria())
        assert result["total_sessions"] == 0
        assert result["avg_bounce_rate"] == 0.0
        assert result["avg_session_duration_s"] == 0.0
        assert result["pages_with_ga4"] == 0
        assert result["pages_high_bounce"] == 0
        assert result["pages_low_duration"] == 0
        # Not enough sessions → check N/A → engagement passes
        assert result["ga4_check_applicable"] is False
        assert result["engagement_acceptable"] is True

    def test_pages_without_ga4_excluded(self):
        pages = [{"slug": "p", "ga4": None}, {"slug": "q"}]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["pages_with_ga4"] == 0

    def test_aggregation(self):
        pages = [
            _make_page("a", 0, 0, 0, 0, sessions=100, bounce_rate=0.50, avg_session_duration_s=60.0),
            _make_page("b", 0, 0, 0, 0, sessions=50,  bounce_rate=0.30, avg_session_duration_s=90.0),
        ]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["total_sessions"] == 150
        assert result["pages_with_ga4"] == 2
        # Weighted avg bounce: (0.50*100 + 0.30*50) / 150
        expected_bounce = round((0.50 * 100 + 0.30 * 50) / 150, 4)
        assert result["avg_bounce_rate"] == expected_bounce
        # Weighted avg duration: (60*100 + 90*50) / 150
        expected_dur = round((60 * 100 + 90 * 50) / 150, 1)
        assert result["avg_session_duration_s"] == expected_dur

    def test_high_bounce_detection(self):
        pages = [
            _make_page("bad", 0, 0, 0, 0, sessions=20, bounce_rate=0.85, avg_session_duration_s=60.0),
            _make_page("ok",  0, 0, 0, 0, sessions=20, bounce_rate=0.40, avg_session_duration_s=60.0),
        ]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["pages_high_bounce"] == 1
        assert result["pages_high_bounce_detail"][0]["slug"] == "bad"

    def test_low_duration_detection(self):
        pages = [
            _make_page("thin",   0, 0, 0, 0, sessions=20, bounce_rate=0.30, avg_session_duration_s=10.0),
            _make_page("normal", 0, 0, 0, 0, sessions=20, bounce_rate=0.30, avg_session_duration_s=90.0),
        ]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["pages_low_duration"] == 1
        assert result["pages_low_duration_detail"][0]["slug"] == "thin"

    def test_check_not_applicable_below_session_threshold(self):
        # Only 30 sessions < min_sessions_for_check 50
        pages = [_make_page("p", 0, 0, 0, 0, sessions=30, bounce_rate=0.90, avg_session_duration_s=5.0)]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["ga4_check_applicable"] is False
        assert result["engagement_acceptable"] is True  # check N/A → passes

    def test_check_applicable_fails_when_high_bounce(self):
        pages = [_make_page("p", 0, 0, 0, 0, sessions=60, bounce_rate=0.85, avg_session_duration_s=60.0)]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["ga4_check_applicable"] is True
        assert result["engagement_acceptable"] is False

    def test_check_applicable_passes_when_good(self):
        pages = [_make_page("p", 0, 0, 0, 0, sessions=60, bounce_rate=0.40, avg_session_duration_s=90.0)]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["ga4_check_applicable"] is True
        assert result["engagement_acceptable"] is True

    def test_min_page_sessions_gate(self):
        """Pages with too few sessions should not trigger high-bounce/low-duration rules."""
        # Only 5 sessions — below min_page_sessions_for_rule=10
        pages = [_make_page("p", 0, 0, 0, 0, sessions=5, bounce_rate=0.95, avg_session_duration_s=2.0)]
        result = _analyze_ga4_signals({"pages": pages}, _ga4_criteria())
        assert result["pages_high_bounce"] == 0
        assert result["pages_low_duration"] == 0


class TestEvaluatePilotGateGa4:
    """End-to-end tests covering GA4 integration in evaluate_pilot_gate."""

    def _run(self, report_pages, criteria=None):
        import tempfile, json as _json
        if criteria is None:
            criteria = _ga4_criteria()
        registry = _make_registry(published=5, approved=2)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cp = td / "c.json"
            rp = td / "r.json"
            cp.write_text(_json.dumps(criteria))
            rp.write_text(_json.dumps(registry))
            with patch("src.pilot_gate.collect_pilot_report", return_value=_make_report(report_pages)), \
                 patch("src.pilot_gate._site_host_is_resolvable", return_value=True):
                return evaluate_pilot_gate(criteria_path=cp, registry_path=rp, days=7)

    def test_ga4_behavior_key_present(self):
        result = self._run([_make_page("p", 100, 2, 2.0, 3.0, sessions=60, bounce_rate=0.4, avg_session_duration_s=80.0)])
        assert "ga4_behavior" in result

    def test_summary_ga4_fields(self):
        result = self._run([_make_page("p", 100, 2, 2.0, 3.0, sessions=60, bounce_rate=0.4, avg_session_duration_s=80.0)])
        s = result["summary"]
        assert "ga4_total_sessions" in s
        assert "ga4_avg_bounce_rate" in s
        assert "ga4_avg_session_duration_s" in s
        assert s["ga4_total_sessions"] == 60

    def test_engagement_acceptable_in_checks(self):
        result = self._run([_make_page("p", 0, 0, 0, 0)])
        assert "engagement_acceptable" in result["checks"]

    def test_require_engagement_gate_false_no_block(self):
        pages = [_make_page("p", 0, 0, 0, 0, sessions=60, bounce_rate=0.90, avg_session_duration_s=5.0)]
        criteria = _ga4_criteria(require_engagement_gate=False)
        result = self._run(pages, criteria=criteria)
        assert not any("GA4" in r for r in result["blocking_reasons"])

    def test_require_engagement_gate_true_blocks(self):
        pages = [_make_page("p", 0, 0, 0, 0, sessions=60, bounce_rate=0.90, avg_session_duration_s=5.0)]
        criteria = _ga4_criteria(require_engagement_gate=True)
        result = self._run(pages, criteria=criteria)
        assert any("GA4 engagement gate" in r for r in result["blocking_reasons"])
        assert result["decision"] == "hold"


class TestRenderMarkdownGa4:
    def _run(self, pages):
        import tempfile, json as _json
        criteria = _ga4_criteria()
        registry = _make_registry(published=5, approved=2)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cp = td / "c.json"
            rp = td / "r.json"
            cp.write_text(_json.dumps(criteria))
            rp.write_text(_json.dumps(registry))
            with patch("src.pilot_gate.collect_pilot_report", return_value=_make_report(pages)), \
                 patch("src.pilot_gate._site_host_is_resolvable", return_value=True):
                decision = evaluate_pilot_gate(criteria_path=cp, registry_path=rp, days=7)
        return render_markdown(decision)

    def test_ga4_section_present(self):
        md = self._run([_make_page("p", 0, 0, 0, 0)])
        assert "## GA4 Behavior Analysis" in md

    def test_no_ga4_message_when_no_data(self):
        md = self._run([_make_page("p", 100, 2, 2.0, 3.0)])  # no ga4 key
        assert "GA4_PROPERTY_ID" in md

    def test_high_bounce_listed(self):
        pages = [_make_page("bad", 0, 0, 0, 0, sessions=20, bounce_rate=0.85, avg_session_duration_s=60.0)]
        md = self._run(pages)
        assert "bad" in md
        assert "High Bounce Rate" in md

    def test_low_duration_listed(self):
        pages = [_make_page("thin", 0, 0, 0, 0, sessions=20, bounce_rate=0.30, avg_session_duration_s=10.0)]
        md = self._run(pages)
        assert "thin" in md
        assert "Low Session Duration" in md
