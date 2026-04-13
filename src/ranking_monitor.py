"""Generate a small weekly SEO dashboard for published pilot pages."""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Retry policy for the sitemap fetch only.
# A transient 503 on the sitemap would mark ALL published pages as
# "missing_from_post_sitemap" — a false positive that blocks the pilot gate.
# Page health checks intentionally do NOT use this adapter (we want real state).
_SITEMAP_RETRY = Retry(
    total=3,
    backoff_factor=1.5,
    status_forcelist={429, 500, 502, 503, 504},
    allowed_methods={"GET"},
    raise_on_status=False,
)

try:
    from config import get_settings
    from ga4_client import make_ga4_client, _normalize_url as _norm_url
    from gsc_client import GSCClient
except ImportError:  # pragma: no cover - allows module-style imports
    from src.config import get_settings
    from src.ga4_client import make_ga4_client, _normalize_url as _norm_url
    from src.gsc_client import GSCClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "data" / "page_registry.json"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "seo_dashboard.md"
DEFAULT_POST_SITEMAP_PATH = "post-sitemap.xml"
REQUEST_TIMEOUT = 20
USER_AGENT = "sweetsworld-ranking-monitor/1.0"


@dataclass
class PageHealth:
    status_code: int
    final_url: str
    title: str
    meta_description: str
    canonical: str
    h1_count: int
    noindex: bool


class _SeoPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: List[str] = []
        self.h1_count = 0
        self.meta_description = ""
        self.meta_robots = ""
        self.canonical = ""

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        tag_name = tag.lower()

        if tag_name == "title":
            self.in_title = True
        elif tag_name == "h1":
            self.h1_count += 1
        elif tag_name == "meta":
            name = attr_map.get("name", "").lower()
            content = attr_map.get("content", "").strip()
            if name == "description" and not self.meta_description:
                self.meta_description = content
            elif name == "robots" and not self.meta_robots:
                self.meta_robots = content.lower()
        elif tag_name == "link":
            rel = attr_map.get("rel", "").lower()
            href = attr_map.get("href", "").strip()
            if "canonical" in rel and href and not self.canonical:
                self.canonical = href

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(part.strip() for part in self.title_parts if part.strip()).strip()


def _load_registry_records(registry_path: Path) -> List[Dict]:
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("page_registry.json records must be a list")
    return records


def _fetch_post_sitemap(base_url: str, session: requests.Session) -> str:
    sitemap_url = f"{base_url.rstrip('/')}/{DEFAULT_POST_SITEMAP_PATH}"
    response = session.get(sitemap_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text or ""


def _check_page(url: str, session: requests.Session) -> PageHealth:
    response = session.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
    parser = _SeoPageParser()
    parser.feed(response.text or "")
    return PageHealth(
        status_code=response.status_code,
        final_url=response.url,
        title=parser.title,
        meta_description=parser.meta_description,
        canonical=parser.canonical,
        h1_count=parser.h1_count,
        noindex=("noindex" in parser.meta_robots),
    )


def _make_gsc_client(settings) -> tuple[Optional[GSCClient], str]:
    if not settings.use_gsc_data:
        return None, "USE_GSC_DATA=false"
    credentials_path = Path(settings.gsc_credentials_file)
    if not settings.gsc_property_url:
        return None, "GSC_PROPERTY_URL is empty"
    if not credentials_path.exists():
        return None, f"credentials not found at {credentials_path}"
    try:
        return GSCClient(settings.gsc_property_url, str(credentials_path)), ""
    except Exception as exc:  # pragma: no cover - depends on environment credentials
        return None, str(exc)


def _query_gsc_for_page(gsc_client: GSCClient, page_url: str, days: int) -> Dict:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    page_filter = {
        "dimensionFilterGroups": [
            {
                "filters": [
                    {
                        "dimension": "page",
                        "operator": "equals",
                        "expression": page_url,
                    }
                ]
            }
        ]
    }

    totals_request = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "dimensions": ["page"],
        "rowLimit": 1,
        **page_filter,
    }
    query_request = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "dimensions": ["query"],
        "rowLimit": 50,
        **page_filter,
    }

    totals_response = gsc_client.service.searchanalytics().query(
        siteUrl=gsc_client.property_url,
        body=totals_request,
    ).execute()
    queries_response = gsc_client.service.searchanalytics().query(
        siteUrl=gsc_client.property_url,
        body=query_request,
    ).execute()

    total_row = (totals_response.get("rows") or [{}])[0]
    top_queries = []
    for row in queries_response.get("rows", []) or []:
        top_queries.append(
            {
                "query": (row.get("keys") or [""])[0],
                "clicks": int(row.get("clicks", 0) or 0),
                "impressions": int(row.get("impressions", 0) or 0),
                "ctr": round(float(row.get("ctr", 0.0) or 0.0) * 100.0, 2),
                "position": round(float(row.get("position", 0.0) or 0.0), 2),
            }
        )

    return {
        "clicks": int(total_row.get("clicks", 0) or 0),
        "impressions": int(total_row.get("impressions", 0) or 0),
        "ctr": round(float(total_row.get("ctr", 0.0) or 0.0) * 100.0, 2),
        "position": round(float(total_row.get("position", 0.0) or 0.0), 2),
        "top_queries": top_queries,
    }


def collect_pilot_report(days: int = 7, slugs: Optional[List[str]] = None, registry_path: Path = DEFAULT_REGISTRY_PATH) -> Dict:
    settings = get_settings()
    session = requests.Session()
    sitemap_session = requests.Session()
    sitemap_session.mount("https://", HTTPAdapter(max_retries=_SITEMAP_RETRY))
    sitemap_session.mount("http://", HTTPAdapter(max_retries=_SITEMAP_RETRY))
    records = _load_registry_records(registry_path)
    slug_filter = {slug.strip() for slug in (slugs or []) if slug.strip()}
    published_records = [
        record for record in records
        if str(record.get("status") or "").lower() == "published"
        and (not slug_filter or str(record.get("slug") or "") in slug_filter)
    ]

    sitemap_error = ""
    sitemap_text = ""
    try:
        sitemap_text = _fetch_post_sitemap(settings.wp_base_url, sitemap_session)
    except Exception as exc:  # pragma: no cover - depends on network
        sitemap_error = str(exc)

    gsc_client, gsc_error = _make_gsc_client(settings)

    # One bulk GA4 call for all pages (avoids per-page quota pressure)
    ga4_error = ""
    ga4_metrics_by_url: Dict[str, Dict] = {}
    ga4_client = make_ga4_client(settings.ga4_property_id, settings.ga4_credentials_file)
    if ga4_client:
        try:
            ga4_metrics_by_url = ga4_client.query_site(days=days)
        except Exception as exc:
            ga4_error = str(exc)
            logger.warning("GA4 query_site failed: %s", exc)

    pages = []
    blocking_issues = 0
    for record in published_records:
        url = str(record.get("post_link") or "").strip()
        page_issues: List[str] = []
        health = None
        effective_url = url
        if url:
            try:
                health = _check_page(url, session)
            except Exception as exc:  # pragma: no cover - depends on network
                page_issues.append(f"http_check_failed: {exc}")

        if health and health.final_url:
            effective_url = health.final_url.strip()

        in_sitemap = bool(effective_url and sitemap_text and effective_url in sitemap_text)
        if effective_url and sitemap_text and not in_sitemap:
            page_issues.append("missing_from_post_sitemap")
        if health:
            normalized_final = health.final_url.rstrip("/")
            normalized_url = url.rstrip("/")
            if health.status_code != 200:
                page_issues.append(f"http_{health.status_code}")
            if health.noindex:
                page_issues.append("noindex")
            if health.canonical and health.canonical.rstrip("/") != normalized_final:
                page_issues.append("canonical_mismatch")
            # A clean redirect to the canonical final URL is acceptable for
            # reporting. We still surface the final URL in the dashboard, but
            # do not treat this as a blocker.
            if normalized_final != normalized_url and (not health.canonical or health.canonical.rstrip("/") != normalized_final):
                page_issues.append("final_url_differs")
            if not health.title:
                page_issues.append("missing_title")
            if not health.meta_description:
                page_issues.append("missing_meta_description")
            if health.h1_count != 1:
                page_issues.append(f"h1_count_{health.h1_count}")

        gsc_metrics = None
        if gsc_client and effective_url:
            try:
                gsc_metrics = _query_gsc_for_page(gsc_client, effective_url, days=days)
            except Exception as exc:  # pragma: no cover - depends on live GSC
                page_issues.append(f"gsc_query_failed: {exc}")

        # GA4 lookup — O(1) from pre-fetched dict
        ga4_metrics = None
        if effective_url and ga4_metrics_by_url:
            ga4_metrics = ga4_metrics_by_url.get(_norm_url(effective_url))

        if page_issues:
            blocking_issues += 1

        pages.append(
            {
                "slug": record.get("slug"),
                "keyword": record.get("keyword"),
                "page_type": record.get("page_type"),
                "post_link": url,
                "published_at": record.get("published_at"),
                "wp_modified": record.get("wp_modified"),
                "health": health.__dict__ if health else None,
                "in_post_sitemap": in_sitemap,
                "gsc": gsc_metrics,
                "ga4": ga4_metrics,
                "issues": page_issues,
            }
        )

    recommendation = "Hold expansion until pilot checks are cleaner."
    if not pages:
        recommendation = "No published pilot pages found. Keep the rollout in review mode."
    elif blocking_issues == 0 and gsc_client:
        recommendation = "Pilot pages look technically healthy. Review GSC impressions and query fit before approving more pages."
    elif blocking_issues == 0:
        recommendation = "Technical checks look good. Next step is to review GSC once data appears, then decide whether to approve another sample."

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "generated_at": generated_at,
        "days": days,
        "published_count": len(pages),
        "blocking_issue_count": blocking_issues,
        "gsc_enabled": bool(gsc_client),
        "gsc_error": gsc_error,
        "ga4_enabled": bool(ga4_client),
        "ga4_error": ga4_error,
        "sitemap_error": sitemap_error,
        "pages": pages,
        "recommendation": recommendation,
    }


def render_markdown_report(report: Dict) -> str:
    lines = [
        "# SEO Dashboard",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Window: last `{report['days']}` days",
        f"- Published pilot pages: `{report['published_count']}`",
        f"- Pages with blocking issues: `{report['blocking_issue_count']}`",
        f"- GSC enabled: `{report['gsc_enabled']}`",
    ]
    if report.get("gsc_error"):
        lines.append(f"- GSC note: `{report['gsc_error']}`")
    if report.get("sitemap_error"):
        lines.append(f"- Sitemap note: `{report['sitemap_error']}`")

    lines.extend(["", "## Pilot Pages", ""])
    if not report["pages"]:
        lines.append("No published pilot pages found.")
    for page in report["pages"]:
        lines.append(f"### {page['slug']}")
        lines.append(f"- Page type: `{page['page_type']}`")
        lines.append(f"- URL: {page['post_link']}")
        lines.append(f"- Published at: `{page.get('published_at') or 'n/a'}`")
        lines.append(f"- In post sitemap: `{page['in_post_sitemap']}`")

        health = page.get("health") or {}
        if health:
            lines.append(f"- HTTP status: `{health.get('status_code')}`")
            lines.append(f"- Final URL: `{health.get('final_url')}`")
            lines.append(f"- Canonical: `{health.get('canonical') or 'missing'}`")
            lines.append(f"- Noindex: `{health.get('noindex')}`")
            lines.append(f"- H1 count: `{health.get('h1_count')}`")
            lines.append(f"- Title present: `{bool(health.get('title'))}`")
            lines.append(f"- Meta description present: `{bool(health.get('meta_description'))}`")

        gsc = page.get("gsc")
        if gsc:
            lines.append(f"- GSC clicks: `{gsc['clicks']}`")
            lines.append(f"- GSC impressions: `{gsc['impressions']}`")
            lines.append(f"- GSC CTR: `{gsc['ctr']}%`")
            lines.append(f"- GSC avg position: `{gsc['position']}`")
            if gsc["top_queries"]:
                lines.append("- Top queries:")
                for item in gsc["top_queries"]:
                    lines.append(
                        f"  - `{item['query']}` | clicks `{item['clicks']}` | impressions `{item['impressions']}` | position `{item['position']}`"
                    )

        if page["issues"]:
            lines.append("- Issues:")
            for issue in page["issues"]:
                lines.append(f"  - `{issue}`")
        else:
            lines.append("- Issues: none")
        lines.append("")

    lines.extend(["## Recommendation", "", report["recommendation"], ""])
    return "\n".join(lines)


def write_markdown_report(report: Dict, output_path: Path = DEFAULT_REPORT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(render_markdown_report(report), encoding="utf-8")
    os.replace(tmp, output_path)
    return output_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a small SEO dashboard for published pilot pages.")
    parser.add_argument("--days", type=int, default=7, help="Lookback window for GSC metrics.")
    parser.add_argument("--slug", action="append", default=[], help="Limit the report to one or more slugs.")
    parser.add_argument("--output", default=str(DEFAULT_REPORT_PATH), help="Markdown output path.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = collect_pilot_report(days=max(1, args.days), slugs=args.slug)
    output_path = write_markdown_report(report, Path(args.output))
    print(json.dumps({"output_path": str(output_path), "published_count": report["published_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
