"""Evaluate whether the SEO pilot is ready for expansion or should remain on hold."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

try:
    from ranking_monitor import collect_pilot_report
    from telegram_notify import notify_pilot_gate
    from config import get_settings
except ImportError:  # pragma: no cover
    from src.ranking_monitor import collect_pilot_report
    from src.telegram_notify import notify_pilot_gate
    from src.config import get_settings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CRITERIA_PATH = PROJECT_ROOT / "data" / "pilot_exit_criteria.json"
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "data" / "page_registry.json"
DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "pilot_gate.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "pilot_gate.md"
SITEMAP_GRACE_DAYS = 7


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_records(path: Path) -> List[Dict[str, Any]]:
    payload = _load_json(path)
    records = payload.get("records", [])
    return records if isinstance(records, list) else []


def _parse_datetime(value: Any, fallback_tz=timezone.utc) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=fallback_tz)
    return parsed


def _load_previous_dashboard_report(path: Path | None) -> Dict[str, Any] | None:
    if path is None:
        return None
    payload = _load_json(path)
    report = payload.get("dashboard_report")
    return report if isinstance(report, dict) else None


def _report_looks_offline(report: Dict[str, Any]) -> bool:
    pages = report.get("pages")
    if not isinstance(pages, list) or not pages:
        return False

    for page in pages:
        issues = page.get("issues")
        if not isinstance(issues, list) or not issues:
            return False
        for issue in issues:
            if not isinstance(issue, str):
                return False
            if not issue.startswith(("http_check_failed:", "gsc_query_failed:")):
                return False
    return True


def _site_host_is_resolvable() -> bool:
    try:
        host = urlparse(get_settings().wp_base_url).hostname or ""
    except Exception:
        return True
    if not host:
        return True
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    return True


def _classify_issue(issue: str, published_at: datetime | None, report_time: datetime) -> tuple[bool, str]:
    if issue == "missing_from_post_sitemap":
        if published_at is not None:
            age_days = max(0.0, (report_time - published_at).total_seconds() / 86400)
            if age_days < SITEMAP_GRACE_DAYS:
                return False, f"fresh publish ({age_days:.1f}d old); allow sitemap propagation"
        return True, "not in post sitemap after grace window"

    if issue.startswith("h1_count_"):
        try:
            h1_count = int(issue.rsplit("_", 1)[-1])
        except ValueError:
            return True, "unparseable H1 check result"
        if h1_count <= 0:
            return True, "page is missing an H1"
        # Multiple H1s are still worth tracking in the dashboard, but the
        # technical scanner only treats a missing H1 as a blocker.
        return False, "extra H1s are tracked as warning-only"

    return True, "hard technical issue"


def _analyze_ga4_signals(
    report: Dict[str, Any],
    criteria: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute GA4 behavior metrics used by the pilot gate.

    Returns a dict with:
        total_sessions, avg_bounce_rate, avg_session_duration_s,
        pages_with_ga4, pages_high_bounce, pages_low_duration,
        ga4_check_applicable, engagement_acceptable,
        max_bounce_rate, min_session_duration_s,
        pages_high_bounce_detail, pages_low_duration_detail
    """
    ga4_quality = (criteria.get("ga4_quality") or {}) if isinstance(criteria, dict) else {}
    max_bounce_rate = float(ga4_quality.get("max_bounce_rate", 0.70) or 0.70)
    min_session_duration_s = float(ga4_quality.get("min_session_duration_s", 30.0) or 30.0)
    min_sessions_for_check = int(ga4_quality.get("min_sessions_for_check", 50) or 50)
    min_page_sessions = int(ga4_quality.get("min_page_sessions_for_rule", 10) or 10)

    pages_with_ga4: List[Dict[str, Any]] = []
    total_sessions = 0
    bounce_weighted = 0.0
    duration_weighted = 0.0

    for page in report.get("pages", []):
        ga4 = page.get("ga4")
        if not isinstance(ga4, dict):
            continue
        sessions = int(ga4.get("sessions", 0) or 0)
        if sessions == 0:
            continue
        bounce_rate = float(ga4.get("bounce_rate", 0.0) or 0.0)
        avg_duration = float(ga4.get("avg_session_duration_s", 0.0) or 0.0)
        total_sessions += sessions
        bounce_weighted += bounce_rate * sessions
        duration_weighted += avg_duration * sessions
        pages_with_ga4.append(
            {
                "slug": page.get("slug"),
                "page_type": page.get("page_type"),
                "sessions": sessions,
                "bounce_rate": bounce_rate,
                "avg_session_duration_s": avg_duration,
            }
        )

    avg_bounce_rate = round(bounce_weighted / total_sessions, 4) if total_sessions > 0 else 0.0
    avg_session_duration_s = round(duration_weighted / total_sessions, 1) if total_sessions > 0 else 0.0

    pages_high_bounce = [
        p for p in pages_with_ga4
        if p["sessions"] >= min_page_sessions and p["bounce_rate"] > max_bounce_rate
    ]
    pages_low_duration = [
        p for p in pages_with_ga4
        if p["sessions"] >= min_page_sessions and p["avg_session_duration_s"] < min_session_duration_s
    ]

    ga4_check_applicable = total_sessions >= min_sessions_for_check
    engagement_acceptable = (not ga4_check_applicable) or (
        len(pages_high_bounce) == 0 and len(pages_low_duration) == 0
    )

    return {
        "total_sessions": total_sessions,
        "avg_bounce_rate": avg_bounce_rate,
        "avg_session_duration_s": avg_session_duration_s,
        "pages_with_ga4": len(pages_with_ga4),
        "pages_high_bounce": len(pages_high_bounce),
        "pages_low_duration": len(pages_low_duration),
        "ga4_check_applicable": ga4_check_applicable,
        "engagement_acceptable": engagement_acceptable,
        "max_bounce_rate": max_bounce_rate,
        "min_session_duration_s": min_session_duration_s,
        "pages_high_bounce_detail": pages_high_bounce,
        "pages_low_duration_detail": pages_low_duration,
    }


def _analyze_gsc_signals(
    report: Dict[str, Any],
    criteria: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute rich GSC performance metrics used by the pilot gate.

    Returns a dict with:
        total_impressions, total_clicks, avg_ctr, avg_position,
        pages_with_impressions, pages_stuck_in_positions_5_to_10,
        pages_low_ctr, content_upgrade_candidates,
        ctr_check_applicable, ctr_meets_threshold, min_ctr_pct,
        pages_stuck_detail, pages_low_ctr_detail
    """
    gsc_quality = (criteria.get("gsc_quality") or {}) if isinstance(criteria, dict) else {}
    ctr_check_min_impressions = int(gsc_quality.get("ctr_check_min_impressions", 100) or 100)
    min_ctr_pct = float(gsc_quality.get("min_ctr_pct", 1.0) or 1.0)
    position_stuck_min = float(gsc_quality.get("position_stuck_min", 5.0) or 5.0)
    position_stuck_max = float(gsc_quality.get("position_stuck_max", 10.9) or 10.9)

    pages_with_gsc: List[Dict[str, Any]] = []
    total_impressions = 0
    total_clicks = 0
    position_sum_weighted = 0.0

    for page in report.get("pages", []):
        gsc = page.get("gsc")
        if not isinstance(gsc, dict):
            continue
        impressions = int(gsc.get("impressions", 0) or 0)
        if impressions == 0:
            continue
        clicks = int(gsc.get("clicks", 0) or 0)
        # ctr from ranking_monitor is already expressed as a percentage (e.g. 1.5 means 1.5%)
        ctr = float(gsc.get("ctr", 0.0) or 0.0)
        position = float(gsc.get("position", 0.0) or 0.0)
        total_impressions += impressions
        total_clicks += clicks
        position_sum_weighted += position * impressions
        pages_with_gsc.append(
            {
                "slug": page.get("slug"),
                "page_type": page.get("page_type"),
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr,
                "position": position,
            }
        )

    avg_ctr = round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0.0
    avg_position = round(position_sum_weighted / total_impressions, 2) if total_impressions > 0 else 0.0

    pages_stuck = [
        p for p in pages_with_gsc
        if position_stuck_min <= p["position"] <= position_stuck_max
    ]
    pages_low_ctr = [
        p for p in pages_with_gsc
        if p["impressions"] >= 20 and p["ctr"] < min_ctr_pct
    ]

    ctr_check_applicable = total_impressions >= ctr_check_min_impressions
    ctr_meets_threshold = (not ctr_check_applicable) or (avg_ctr >= min_ctr_pct)

    upgrade_candidates = sorted(
        {p["slug"] for p in pages_stuck} | {p["slug"] for p in pages_low_ctr}
    )

    return {
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "avg_ctr": avg_ctr,
        "avg_position": avg_position,
        "pages_with_impressions": len(pages_with_gsc),
        "pages_stuck_in_positions_5_to_10": len(pages_stuck),
        "pages_low_ctr": len(pages_low_ctr),
        "content_upgrade_candidates": upgrade_candidates,
        "ctr_check_applicable": ctr_check_applicable,
        "ctr_meets_threshold": ctr_meets_threshold,
        "min_ctr_pct": min_ctr_pct,
        "pages_stuck_detail": pages_stuck,
        "pages_low_ctr_detail": pages_low_ctr,
    }


def _summarize_technical_blockers(report: Dict[str, Any]) -> Dict[str, Any]:
    report_time = _parse_datetime(report.get("generated_at")) or datetime.now(timezone.utc)
    blocking_pages: List[Dict[str, Any]] = []
    warning_pages: List[Dict[str, Any]] = []
    blocking_issue_breakdown: Counter[str] = Counter()
    warning_issue_breakdown: Counter[str] = Counter()

    pages = report.get("pages")
    if not isinstance(pages, list):
        pages = []

    for page in pages:
        issues = page.get("issues")
        if not isinstance(issues, list) or not issues:
            continue

        published_at = _parse_datetime(page.get("published_at"), report_time.tzinfo or timezone.utc)
        blocking_issues: List[Dict[str, str]] = []
        warning_issues: List[Dict[str, str]] = []
        for issue in issues:
            if not isinstance(issue, str):
                continue
            is_blocking, note = _classify_issue(issue, published_at, report_time)
            issue_payload = {"issue": issue, "note": note}
            if is_blocking:
                blocking_issues.append(issue_payload)
                blocking_issue_breakdown[issue] += 1
            else:
                warning_issues.append(issue_payload)
                warning_issue_breakdown[issue] += 1

        if blocking_issues:
            blocking_pages.append(
                {
                    "slug": page.get("slug"),
                    "page_type": page.get("page_type"),
                    "post_link": page.get("post_link"),
                    "published_at": page.get("published_at"),
                    "issues": blocking_issues,
                    "warnings": warning_issues,
                }
            )
        elif warning_issues:
            warning_pages.append(
                {
                    "slug": page.get("slug"),
                    "page_type": page.get("page_type"),
                    "post_link": page.get("post_link"),
                    "published_at": page.get("published_at"),
                    "issues": warning_issues,
                }
            )

    return {
        "blocking_issue_count": len(blocking_pages),
        "dashboard_issue_count": len(blocking_pages) + len(warning_pages),
        "warning_issue_count": len(warning_pages),
        "blocking_issue_breakdown": dict(blocking_issue_breakdown),
        "warning_issue_breakdown": dict(warning_issue_breakdown),
        "blocking_pages": blocking_pages,
        "warning_pages": warning_pages,
    }


def evaluate_pilot_gate(
    criteria_path: Path = DEFAULT_CRITERIA_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    days: int = 7,
    previous_json_path: Path | None = None,
) -> Dict[str, Any]:
    criteria = _load_json(criteria_path)
    dashboard_report_source = "live"
    previous_report = _load_previous_dashboard_report(previous_json_path)
    if previous_report and not _site_host_is_resolvable():
        report = previous_report
        dashboard_report_source = "cached_previous_run"
    else:
        report = collect_pilot_report(days=days, registry_path=registry_path)
    if dashboard_report_source == "live" and _report_looks_offline(report):
        previous_report = _load_previous_dashboard_report(previous_json_path)
        if previous_report:
            report = previous_report
            dashboard_report_source = "cached_previous_run"
    records = _registry_records(registry_path)
    technical_summary = _summarize_technical_blockers(report)
    gsc_signals = _analyze_gsc_signals(report, criteria)
    ga4_signals = _analyze_ga4_signals(report, criteria)

    scope = criteria.get("pilot_scope", {}) if isinstance(criteria, dict) else {}
    manual = criteria.get("manual_qa_requirements", {}) if isinstance(criteria, dict) else {}
    gates = criteria.get("expansion_gates", {}) if isinstance(criteria, dict) else {}
    gsc_quality = (criteria.get("gsc_quality") or {}) if isinstance(criteria, dict) else {}

    published = [r for r in records if str(r.get("status", "")).lower() == "published"]
    approved = [r for r in records if str(r.get("status", "")).lower() == "approved"]
    reviewed = [r for r in records if str(r.get("status", "")).lower() in {"approved", "published", "blocked"}]

    published_count = len(published)
    approved_count = len(approved)
    reviewed_count = len(reviewed)
    initial_publish_batch_min = int(scope.get("initial_publish_batch_min", 0) or 0)
    initial_publish_batch_max = int(scope.get("initial_publish_batch_max", 999) or 999)
    review_window_days = int(scope.get("review_window_days", 14) or 14)
    minimum_pass_rate = float(manual.get("minimum_pass_rate", 1.0) or 1.0)

    qa_pass_rate = 1.0
    if reviewed_count:
        qa_pass_rate = round((len([r for r in reviewed if str(r.get("status", "")).lower() != "blocked"]) / reviewed_count), 3)

    total_impressions = gsc_signals["total_impressions"]
    total_clicks = gsc_signals["total_clicks"]
    has_technical_blockers = int(technical_summary.get("blocking_issue_count", 0) or 0) > 0
    indexation_signal = total_impressions > 0
    query_intent_fit = total_clicks > 0

    orphaned_count = len([r for r in records if str(r.get("status", "")).lower() == "orphaned"])

    checks = {
        "published_batch_within_expected_range": initial_publish_batch_min <= published_count <= initial_publish_batch_max,
        "manual_qa_complete": qa_pass_rate >= minimum_pass_rate,
        "no_technical_blockers": not has_technical_blockers,
        "no_orphaned_records": orphaned_count == 0,
        "search_console_review_available": bool(report.get("gsc_enabled")),
        "indexation_signal_present": indexation_signal,
        "query_intent_fit_present": query_intent_fit,
        "ctr_meets_threshold": gsc_signals["ctr_meets_threshold"],
        "engagement_acceptable": ga4_signals["engagement_acceptable"],
        "approved_queue_available": approved_count > 0,
    }

    blocking_reasons: List[str] = []
    if gates.get("require_no_duplicate_publishes", True):
        # Current registry has no duplicate published slug/page_type pairs because we key workflow by slug ownership.
        duplicate_keys = set()
        seen = set()
        for record in published:
            key = (record.get("slug"), record.get("page_type"))
            if key in seen:
                duplicate_keys.add(key)
            seen.add(key)
        if duplicate_keys:
            checks["no_duplicate_publishes"] = False
            blocking_reasons.append("duplicate published registry keys detected")
        else:
            checks["no_duplicate_publishes"] = True

    if not checks["published_batch_within_expected_range"]:
        blocking_reasons.append(
            f"published pilot count is {published_count}; expected {initial_publish_batch_min}-{initial_publish_batch_max} before expansion"
        )
    if not checks["manual_qa_complete"]:
        blocking_reasons.append(f"manual QA pass rate is {qa_pass_rate}, below required {minimum_pass_rate}")
    if not checks["no_technical_blockers"]:
        blocking_reasons.append("technical blockers remain on published pilot pages after filtering soft warnings")
    if not checks["no_orphaned_records"]:
        blocking_reasons.append(
            f"{orphaned_count} orphaned registry record(s) detected — run --verify-registry to confirm"
        )
    if gates.get("require_search_console_review", True) and not checks["search_console_review_available"]:
        blocking_reasons.append("GSC review is required but GSC metrics are not available")
    if gates.get("require_indexation_signal", True) and not checks["indexation_signal_present"]:
        blocking_reasons.append("no GSC impression signal yet on the published pilot batch")
    if gates.get("require_query_intent_fit", True) and not checks["query_intent_fit_present"]:
        blocking_reasons.append("no GSC click/query-fit signal yet on the published pilot batch")
    if gsc_quality.get("require_ctr_gate", False) and not gsc_signals["ctr_meets_threshold"]:
        blocking_reasons.append(
            f"CTR ({gsc_signals['avg_ctr']:.2f}%) is below required {gsc_signals['min_ctr_pct']:.1f}% "
            f"(based on {total_impressions} impressions)"
        )
    ga4_quality = (criteria.get("ga4_quality") or {}) if isinstance(criteria, dict) else {}
    if ga4_quality.get("require_engagement_gate", False) and not ga4_signals["engagement_acceptable"]:
        parts = []
        if ga4_signals["pages_high_bounce"] > 0:
            pct = ga4_signals["avg_bounce_rate"] * 100
            parts.append(
                f"{ga4_signals['pages_high_bounce']} page(s) have high bounce rate "
                f"(avg {pct:.1f}%, threshold {ga4_signals['max_bounce_rate'] * 100:.0f}%)"
            )
        if ga4_signals["pages_low_duration"] > 0:
            parts.append(
                f"{ga4_signals['pages_low_duration']} page(s) have low session duration "
                f"(avg {ga4_signals['avg_session_duration_s']:.0f}s, "
                f"min {ga4_signals['min_session_duration_s']:.0f}s)"
            )
        blocking_reasons.append("GA4 engagement gate: " + "; ".join(parts))

    decision = "expand"
    if blocking_reasons:
        decision = "hold"

    # Derive a plain-language next action so the operator knows exactly what to do
    # without having to reason through the checks themselves.
    upgrade_count = len(gsc_signals["content_upgrade_candidates"])
    upgrade_suffix = (
        f" {upgrade_count} page(s) are content upgrade candidates "
        f"(low CTR or stuck at positions 5-10) — consider regenerating content."
        if upgrade_count > 0 else ""
    )
    if decision == "expand" and approved:
        next_slug = approved[0].get("slug", "")
        next_action = (
            f"Gate is clear. Publish next approved page: '{next_slug}'. "
            f"Command: .venv/bin/python src/run_mvp.py --slug {next_slug} --only-approved --publish-created"
            + upgrade_suffix
        )
    elif decision == "expand" and not approved:
        next_action = (
            "Gate is clear but approved queue is empty. Generate and approve a new page before publishing."
            + upgrade_suffix
        )
    elif not checks.get("indexation_signal_present") and not checks.get("query_intent_fit_present"):
        review_after = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        live_page_word = "page" if published_count == 1 else "pages"
        next_action = (
            f"Waiting for GSC impression signal on the {published_count} live pilot {live_page_word}. "
            f"Re-run pilot_gate after {review_after} to check again."
            + upgrade_suffix
        )
    elif not checks.get("published_batch_within_expected_range"):
        next_action = (
            f"Published count ({published_count}) is below the pilot minimum ({initial_publish_batch_min}). "
            f"Consider publishing an approved page once GSC signals appear."
            + upgrade_suffix
        )
    else:
        next_action = "Resolve blocking reasons listed above before expanding." + upgrade_suffix

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "generated_at": generated_at,
        "days": days,
        "decision": decision,
        "next_action": next_action,
        "dashboard_report_source": dashboard_report_source,
        "summary": {
            "published_count": published_count,
            "approved_count": approved_count,
            "reviewed_count": reviewed_count,
            "qa_pass_rate": qa_pass_rate,
            "review_window_days": review_window_days,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "avg_ctr": gsc_signals["avg_ctr"],
            "avg_position": gsc_signals["avg_position"],
            "pages_with_impressions": gsc_signals["pages_with_impressions"],
            "pages_stuck_in_positions_5_to_10": gsc_signals["pages_stuck_in_positions_5_to_10"],
            "content_upgrade_count": len(gsc_signals["content_upgrade_candidates"]),
            "ga4_total_sessions": ga4_signals["total_sessions"],
            "ga4_avg_bounce_rate": ga4_signals["avg_bounce_rate"],
            "ga4_avg_session_duration_s": ga4_signals["avg_session_duration_s"],
            "ga4_pages_with_data": ga4_signals["pages_with_ga4"],
            "ga4_pages_high_bounce": ga4_signals["pages_high_bounce"],
            "ga4_pages_low_duration": ga4_signals["pages_low_duration"],
            "blocking_issue_count": int(technical_summary.get("blocking_issue_count", 0) or 0),
            "dashboard_issue_count": int(technical_summary.get("dashboard_issue_count", 0) or 0),
            "warning_issue_count": int(technical_summary.get("warning_issue_count", 0) or 0),
        },
        "checks": checks,
        "blocking_reasons": blocking_reasons,
        "technical_blockers": technical_summary,
        "gsc_performance": {
            "avg_ctr": gsc_signals["avg_ctr"],
            "avg_position": gsc_signals["avg_position"],
            "ctr_check_applicable": gsc_signals["ctr_check_applicable"],
            "min_ctr_pct": gsc_signals["min_ctr_pct"],
            "pages_stuck_detail": gsc_signals["pages_stuck_detail"],
            "pages_low_ctr_detail": gsc_signals["pages_low_ctr_detail"],
            "content_upgrade_candidates": gsc_signals["content_upgrade_candidates"],
        },
        "ga4_behavior": {
            "total_sessions": ga4_signals["total_sessions"],
            "avg_bounce_rate": ga4_signals["avg_bounce_rate"],
            "avg_session_duration_s": ga4_signals["avg_session_duration_s"],
            "pages_with_ga4": ga4_signals["pages_with_ga4"],
            "ga4_check_applicable": ga4_signals["ga4_check_applicable"],
            "max_bounce_rate": ga4_signals["max_bounce_rate"],
            "min_session_duration_s": ga4_signals["min_session_duration_s"],
            "pages_high_bounce_detail": ga4_signals["pages_high_bounce_detail"],
            "pages_low_duration_detail": ga4_signals["pages_low_duration_detail"],
        },
        "approved_queue": [
            {
                "slug": item.get("slug"),
                "page_type": item.get("page_type"),
                "notes": item.get("notes", ""),
                "approved_at": item.get("approved_at"),
            }
            for item in approved
        ],
        "dashboard_report": report,
    }


def render_markdown(decision: Dict[str, Any]) -> str:
    checks = decision.get("checks", {})
    summary = decision.get("summary", {})
    technical = decision.get("technical_blockers", {}) if isinstance(decision, dict) else {}
    gsc_perf = decision.get("gsc_performance") or {}
    ga4_beh = decision.get("ga4_behavior") or {}
    lines = [
        "# Pilot Gate",
        "",
        f"- Generated at: `{decision.get('generated_at')}`",
        f"- Decision: **`{decision.get('decision')}`**",
        f"- Next action: {decision.get('next_action', '')}",
        f"- Dashboard source: `{decision.get('dashboard_report_source', 'live')}`",
        "",
        f"- Published pilot pages: `{summary.get('published_count')}`",
        f"- Approved but unpublished pages: `{summary.get('approved_count')}`",
        f"- QA pass rate: `{summary.get('qa_pass_rate')}`",
        f"- GSC impressions: `{summary.get('total_impressions')}` "
        f"| clicks: `{summary.get('total_clicks')}` "
        f"| avg CTR: `{summary.get('avg_ctr')}%` "
        f"| avg position: `{summary.get('avg_position')}`",
        f"- Pages with impressions: `{summary.get('pages_with_impressions')}`",
        f"- Pages stuck at positions 5-10: `{summary.get('pages_stuck_in_positions_5_to_10')}`",
        f"- Content upgrade candidates: `{summary.get('content_upgrade_count')}`",
        f"- GA4 sessions: `{summary.get('ga4_total_sessions')}` "
        f"| avg bounce: `{round((summary.get('ga4_avg_bounce_rate') or 0) * 100, 1)}%` "
        f"| avg duration: `{summary.get('ga4_avg_session_duration_s')}s`",
        f"- GA4 pages with data: `{summary.get('ga4_pages_with_data')}` "
        f"| high bounce: `{summary.get('ga4_pages_high_bounce')}` "
        f"| low duration: `{summary.get('ga4_pages_low_duration')}`",
        f"- Technical blockers: `{summary.get('blocking_issue_count')}`",
        f"- Dashboard issue pages: `{summary.get('dashboard_issue_count')}`",
        f"- Non-blocking technical warnings: `{summary.get('warning_issue_count')}`",
        "",
        "## Checks",
        "",
    ]
    for name, passed in checks.items():
        lines.append(f"- `{name}`: `{passed}`")

    lines.extend(["", "## Blocking Reasons", ""])
    reasons = decision.get("blocking_reasons", []) or []
    if reasons:
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- None")

    warning_breakdown = technical.get("warning_issue_breakdown") or {}
    if warning_breakdown:
        lines.extend(["", "## Technical Warnings", ""])
        for issue, count in sorted(warning_breakdown.items()):
            lines.append(f"- `{issue}`: `{count}` page(s)")

    # GSC Performance section
    lines.extend(["", "## GSC Performance Analysis", ""])
    if gsc_perf:
        ctr_applicable = gsc_perf.get("ctr_check_applicable", False)
        lines.append(
            f"- Average CTR: `{gsc_perf.get('avg_ctr')}%` "
            f"(threshold: `{gsc_perf.get('min_ctr_pct')}%`; "
            f"check {'active' if ctr_applicable else 'inactive — need more impressions'})"
        )
        lines.append(f"- Average position: `{gsc_perf.get('avg_position')}`")

        stuck = gsc_perf.get("pages_stuck_detail") or []
        if stuck:
            lines.extend(["", "### Pages Stuck at Positions 5-10 (content upgrade priority)", ""])
            for p in sorted(stuck, key=lambda x: x.get("position", 99)):
                lines.append(
                    f"- `{p['slug']}` | pos `{p['position']}` | CTR `{p['ctr']}%` | "
                    f"impressions `{p['impressions']}` | clicks `{p['clicks']}`"
                )

        low_ctr = gsc_perf.get("pages_low_ctr_detail") or []
        low_ctr_only = [p for p in low_ctr if p["slug"] not in {s["slug"] for s in stuck}]
        if low_ctr_only:
            lines.extend(["", "### Low CTR Pages (≥20 impressions, CTR below threshold)", ""])
            for p in sorted(low_ctr_only, key=lambda x: x.get("ctr", 99)):
                lines.append(
                    f"- `{p['slug']}` | CTR `{p['ctr']}%` | pos `{p['position']}` | "
                    f"impressions `{p['impressions']}`"
                )

        candidates = gsc_perf.get("content_upgrade_candidates") or []
        if candidates:
            lines.extend(["", "### All Content Upgrade Candidates", ""])
            for slug in candidates:
                lines.append(f"- `{slug}`")
        else:
            lines.append("- No content upgrade candidates identified.")
    else:
        lines.append("- GSC performance data not available.")

    # GA4 Behavior section
    lines.extend(["", "## GA4 Behavior Analysis", ""])
    if ga4_beh and ga4_beh.get("pages_with_ga4", 0) > 0:
        ga4_check = ga4_beh.get("ga4_check_applicable", False)
        bounce_pct = round((ga4_beh.get("avg_bounce_rate") or 0) * 100, 1)
        max_bounce_pct = round((ga4_beh.get("max_bounce_rate") or 0.70) * 100, 0)
        lines.append(
            f"- Total sessions: `{ga4_beh.get('total_sessions')}` "
            f"({'check active' if ga4_check else 'check inactive — need more sessions'})"
        )
        lines.append(
            f"- Avg bounce rate: `{bounce_pct}%` "
            f"(threshold: `{max_bounce_pct:.0f}%`)"
        )
        lines.append(
            f"- Avg session duration: `{ga4_beh.get('avg_session_duration_s')}s` "
            f"(min: `{ga4_beh.get('min_session_duration_s')}s`)"
        )

        high_bounce = ga4_beh.get("pages_high_bounce_detail") or []
        if high_bounce:
            lines.extend(["", "### High Bounce Rate Pages (content/intent mismatch risk)", ""])
            for p in sorted(high_bounce, key=lambda x: -x.get("bounce_rate", 0)):
                pct = round(p["bounce_rate"] * 100, 1)
                lines.append(
                    f"- `{p['slug']}` | bounce `{pct}%` | "
                    f"sessions `{p['sessions']}` | "
                    f"duration `{p['avg_session_duration_s']}s`"
                )

        low_dur = ga4_beh.get("pages_low_duration_detail") or []
        low_dur_only = [p for p in low_dur if p["slug"] not in {b["slug"] for b in high_bounce}]
        if low_dur_only:
            lines.extend(["", "### Low Session Duration Pages (thin content risk)", ""])
            for p in sorted(low_dur_only, key=lambda x: x.get("avg_session_duration_s", 9999)):
                lines.append(
                    f"- `{p['slug']}` | duration `{p['avg_session_duration_s']}s` | "
                    f"sessions `{p['sessions']}`"
                )
    elif ga4_beh.get("pages_with_ga4", 0) == 0:
        lines.append(
            "- No GA4 data available. Set `GA4_PROPERTY_ID` and `GA4_CREDENTIALS_FILE` in `.env` to enable."
        )
    else:
        lines.append("- GA4 data present but no sessions yet (too early).")

    # Surface missing backlinks from internal_links.json if available
    internal_links_path = PROJECT_ROOT / "data" / "internal_links.json"
    if internal_links_path.exists():
        try:
            il = json.loads(internal_links_path.read_text(encoding="utf-8"))
            missing_bl = il.get("missing_backlinks") or []
            lines.extend(["", "## Missing Backlinks", ""])
            if missing_bl:
                for bl in missing_bl:
                    lines.append(
                        f"- `{bl.get('from_slug')}` should link to `{bl.get('to_slug')}` "
                        f"(suggested anchor: _{bl.get('suggested_anchor')}_)"
                    )
            else:
                lines.append("- None — all published pages link to each other")
        except Exception:
            logging.exception("Failed to load internal link analysis from %s", internal_links_path)
            lines.append("Internal link analysis unavailable.")

    lines.extend(["", "## Approved Queue", ""])
    approved_queue = decision.get("approved_queue", []) or []
    if approved_queue:
        for item in approved_queue:
            lines.append(f"- `{item.get('slug')}` | `{item.get('page_type')}` | approved at `{item.get('approved_at')}`")
            note = str(item.get("notes") or "").strip()
            if note:
                lines.append(f"  - note: {note}")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate whether the SEO pilot should remain on hold or expand.")
    parser.add_argument("--days", type=int, default=7, help="Lookback window for GSC metrics.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT), help="Path to write pilot_gate.json")
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT), help="Path to write pilot_gate.md")
    parser.add_argument("--notify", action="store_true", help="Push result to Telegram after evaluation.")
    parser.add_argument("--site", default=None, help="Site ID (e.g. sweetsworld, newcastlehub). Loads SiteContext for per-site paths and credentials.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # ── Multi-site: resolve paths and credentials from SiteContext ────────────
    _ctx = None
    registry_path = DEFAULT_REGISTRY_PATH
    json_path = Path(args.json_output)
    md_path = Path(args.md_output)
    tg_token: str = ""
    tg_chat:  str = ""

    if args.site:
        try:
            from site_context import apply_site_context_env, load_site_context
            _ctx = load_site_context(args.site)
            apply_site_context_env(_ctx)
            site_data = _ctx.site_dir / "data"
            registry_path = site_data / "page_registry.json"
            criteria_path = site_data / "pilot_exit_criteria.json"
            if not criteria_path.exists():
                criteria_path = DEFAULT_CRITERIA_PATH
            reports_dir = _ctx.site_dir / "reports"
            json_path = reports_dir / "pilot_gate.json"
            md_path   = reports_dir / "pilot_gate.md"
            tg_token  = _ctx.telegram_bot_token
            tg_chat   = _ctx.telegram_chat_id
        except Exception as exc:
            print(f"ERROR: Failed to load SiteContext for '{args.site}': {exc}", flush=True)
            return 1
    else:
        criteria_path = DEFAULT_CRITERIA_PATH

    decision = evaluate_pilot_gate(
        criteria_path=criteria_path,
        days=max(1, args.days),
        registry_path=registry_path,
        previous_json_path=json_path,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_json = json_path.with_suffix(".tmp")
    tmp_json.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    os.replace(tmp_json, json_path)

    tmp_md = md_path.with_suffix(".tmp")
    tmp_md.write_text(render_markdown(decision), encoding="utf-8")
    os.replace(tmp_md, md_path)

    if args.notify:
        try:
            if not tg_token:
                settings = get_settings()
                tg_token = settings.telegram_bot_token
                tg_chat  = settings.telegram_chat_id
            notify_pilot_gate(tg_token, tg_chat, decision)
        except Exception as exc:
            print(f"WARN: Telegram notification failed: {exc}", flush=True)

    print(
        json.dumps(
            {
                "decision": decision.get("decision"),
                "technical_blockers": (decision.get("summary") or {}).get("blocking_issue_count"),
                "dashboard_issue_pages": (decision.get("summary") or {}).get("dashboard_issue_count"),
                "dashboard_source": decision.get("dashboard_report_source"),
                "json_output": str(json_path),
                "md_output": str(md_path),
            },
            indent=2,
        )
    )

    # Obsidian vault sync — log pilot gate result
    try:
        import sys as _sys
        _sys.path.insert(0, "/Users/michaelzhao/agents/obsidian-vault/ops")
        from obsidian_sync import log_event as _obs_log
        _gate_decision = decision.get("decision", "unknown")
        _obs_log(f"Pilot gate: {_gate_decision}", "sweetsworld-seo")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
