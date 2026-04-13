"""Minimal GA4 Analytics Data API client for pilot-gate page metrics.

Design: one bulk query per run (not per-page) to stay within quota.
The caller receives a dict keyed by normalized URL, so individual page
lookups are O(1) after the single API call.
"""

from __future__ import annotations

import importlib
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
_PAGE_SIZE = 100_000


def _import_client_class():
    for module_name in ("google.analytics.data", "google.analytics.data_v1beta"):
        try:
            mod = importlib.import_module(module_name)
            for attr in ("BetaAnalyticsDataClient", "AnalyticsDataClient"):
                cls = getattr(mod, attr, None)
                if cls is not None:
                    return cls
        except Exception:
            continue
    raise ModuleNotFoundError(
        "google-analytics-data SDK not installed. "
        "Run: pip install google-analytics-data"
    )


def _cell_value(cell: Any) -> str:
    if hasattr(cell, "value"):
        return str(cell.value)
    return str(cell)


def _normalize_url(url: str) -> str:
    """Lowercase and strip trailing slash for consistent dict key lookup."""
    return url.lower().rstrip("/")


class GA4Client:
    """Thin wrapper around the GA4 Analytics Data API.

    Parameters
    ----------
    property_id:
        GA4 property numeric ID (e.g. ``"123456789"``), or the full
        ``"properties/123456789"`` form.
    credentials_file:
        Path to a service-account JSON file with Analytics read scope.
    """

    def __init__(self, property_id: str, credentials_file: str) -> None:
        from google.oauth2 import service_account  # lazy to avoid hard import

        self.property_name = (
            property_id
            if property_id.startswith("properties/")
            else f"properties/{property_id}"
        )
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=_SCOPES
        )
        client_cls = _import_client_class()
        self._client = client_cls(credentials=creds)

    def query_site(
        self, days: int = 28
    ) -> Dict[str, Dict[str, Any]]:
        """Bulk-fetch sessions, bounce rate, and session duration for all pages.

        Returns a dict mapping ``normalized_url → metrics`` where ``metrics``
        has keys ``sessions``, ``bounce_rate`` (0–1 float), and
        ``avg_session_duration_s``.  Pages with zero sessions are excluded.
        """
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=max(days, 1) - 1)

        result: Dict[str, Dict[str, Any]] = {}
        offset = 0

        while True:
            request = {
                "property": self.property_name,
                "dimensions": [{"name": "fullPageUrl"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "bounceRate"},
                    {"name": "averageSessionDuration"},
                ],
                "date_ranges": [
                    {"start_date": start.isoformat(), "end_date": end.isoformat()}
                ],
                "limit": _PAGE_SIZE,
                "offset": offset,
            }

            response = self._client.run_report(request=request)
            rows = list(getattr(response, "rows", None) or [])
            if not rows:
                break

            for row in rows:
                dvs = getattr(row, "dimension_values", []) or []
                mvs = getattr(row, "metric_values", []) or []
                if not dvs or len(mvs) < 3:
                    continue

                raw_url = _cell_value(dvs[0])
                sessions = float(_cell_value(mvs[0]) or 0)
                if sessions == 0:
                    continue
                bounce_rate = float(_cell_value(mvs[1]) or 0)
                avg_duration = float(_cell_value(mvs[2]) or 0)

                key = _normalize_url(raw_url)
                if key in result:
                    # Aggregate URL variants (trailing-slash, case)
                    prev = result[key]
                    total_s = prev["sessions"] + sessions
                    result[key] = {
                        "sessions": total_s,
                        "bounce_rate": (
                            prev["bounce_rate"] * prev["sessions"]
                            + bounce_rate * sessions
                        ) / total_s,
                        "avg_session_duration_s": (
                            prev["avg_session_duration_s"] * prev["sessions"]
                            + avg_duration * sessions
                        ) / total_s,
                    }
                else:
                    result[key] = {
                        "sessions": int(sessions),
                        "bounce_rate": round(bounce_rate, 4),
                        "avg_session_duration_s": round(avg_duration, 1),
                    }

            if len(rows) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        logger.info(
            "GA4 query_site: %d pages with data (%s → %s)",
            len(result),
            start,
            end,
        )
        return result


def make_ga4_client(
    property_id: str, credentials_file: str
) -> Optional[GA4Client]:
    """Build a GA4Client, returning None (with a logged warning) on failure.

    This is the safe factory used by ranking_monitor; callers never see
    exceptions from missing dependencies or misconfigured credentials.
    """
    if not property_id:
        logger.debug("GA4 skipped: GA4_PROPERTY_ID not set")
        return None
    if not credentials_file:
        logger.debug("GA4 skipped: GA4_CREDENTIALS_FILE not set")
        return None
    if not Path(credentials_file).exists():
        logger.warning("GA4 credentials file not found: %s", credentials_file)
        return None
    try:
        return GA4Client(property_id, credentials_file)
    except Exception as exc:
        logger.warning("Failed to create GA4Client: %s", exc)
        return None
