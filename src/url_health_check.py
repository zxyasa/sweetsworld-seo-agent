"""Product URL health check — detects broken links, bad redirects, and 404s.

Pulls all published WooCommerce products, checks each URL, and sends a
Telegram alert when problems are found. Safe to run as a scheduled job.

Usage:
    python src/url_health_check.py [--limit N] [--notify] [--dry-run]

Flags:
    --limit N    Only check first N products (useful for testing)
    --notify     Send Telegram alert with results (even if no issues)
    --dry-run    Print what would be done, do not make any requests
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

import os as _os

from config import get_settings, setup_logging
from telegram_notify import send_telegram

logger = logging.getLogger(__name__)


def _settings_brand() -> str:
    """Return brand name from SITE_BRAND env var, falling back to 'SweetsWorld'."""
    return _os.getenv("SITE_BRAND", "SweetsWorld")

REPORT_PATH = Path(__file__).resolve().parent.parent / "data" / "url_health_report.json"

# How many seconds to wait between requests to avoid hammering the server
REQUEST_DELAY = 0.3
# Timeout for each URL check
TIMEOUT = 15
# Max redirects to follow before giving up
MAX_REDIRECTS = 5


@dataclass
class URLResult:
    product_id: int
    product_name: str
    sku: str
    original_url: str
    final_url: str
    status_code: int
    redirect_chain: List[str] = field(default_factory=list)
    issue: str = ""          # "" = healthy, else short issue label
    diagnosis: str = ""      # human-readable explanation

    @property
    def is_healthy(self) -> bool:
        return self.issue == ""


def _check_url(url: str) -> tuple[int, str, List[str]]:
    """Follow redirects manually and return (final_status, final_url, chain).

    We follow redirects manually (allow_redirects=False) so we can capture
    the full chain and detect redirect loops / homepage redirects.
    """
    chain: List[str] = []
    current = url
    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS

    for _ in range(MAX_REDIRECTS + 1):
        try:
            resp = session.head(
                current,
                allow_redirects=False,
                timeout=TIMEOUT,
                headers={"User-Agent": f"{_settings_brand()}Bot/1.0"},
            )
        except requests.exceptions.TooManyRedirects:
            return 0, current, chain
        except requests.exceptions.ConnectionError as exc:
            logger.warning(f"Connection error for {current}: {exc}")
            return 0, current, chain
        except requests.exceptions.Timeout:
            return 0, current, chain

        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location", "")
            if not location:
                return resp.status_code, current, chain
            # Resolve relative redirects
            if location.startswith("/"):
                parsed = urlparse(current)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            chain.append(f"{resp.status_code} → {location}")
            current = location
        else:
            return resp.status_code, current, chain

    # Exhausted hops without settling
    return 0, current, chain


def _diagnose(result: URLResult, site_base: str) -> URLResult:
    """Classify the issue and write a human-readable diagnosis."""
    code = result.status_code
    final = result.final_url.rstrip("/")
    base = site_base.rstrip("/")

    if code == 200:
        return result  # healthy

    if code == 404:
        result.issue = "404_not_found"
        result.diagnosis = f"Page not found. URL may have been deleted or slug changed."
        return result

    if code == 0:
        result.issue = "connection_error"
        result.diagnosis = "Could not connect to the URL (timeout or connection refused)."
        return result

    # Redirect cases
    if code in (301, 302, 307, 308):
        # Redirect chain landed on homepage?
        if final == base or final == base + "/" or final.rstrip("/") == base:
            result.issue = "redirect_to_homepage"
            result.diagnosis = (
                f"Product URL redirects to the homepage ({final}). "
                f"Likely a bad Rank Math redirect rule pointing to a deleted slug. "
                f"Chain: {' → '.join(result.redirect_chain)}"
            )
        elif final != result.original_url.rstrip("/"):
            result.issue = "unexpected_redirect"
            result.diagnosis = (
                f"URL redirects to an unexpected destination: {final}. "
                f"Chain: {' → '.join(result.redirect_chain)}"
            )
        return result

    if code in (500, 502, 503, 504):
        result.issue = "server_error"
        result.diagnosis = f"Server returned HTTP {code}. May be a transient issue."
        return result

    result.issue = f"http_{code}"
    result.diagnosis = f"Unexpected HTTP status {code}."
    return result


def fetch_published_products(
    wp_base_url: str,
    wp_username: str,
    wp_app_password: str,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch all published WooCommerce products via REST API."""
    import base64
    token = base64.b64encode(f"{wp_username}:{wp_app_password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    api_url = f"{wp_base_url.rstrip('/')}/wp-json/wc/v3/products"

    products: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        params: Dict[str, Any] = {
            "status": "publish",
            "per_page": per_page,
            "page": page,
            "fields": "id,name,sku,permalink",
        }
        if limit:
            params["per_page"] = min(per_page, limit - len(products))

        resp = requests.get(api_url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        products.extend(batch)
        logger.info(f"Fetched page {page}: {len(batch)} products (total {len(products)})")

        if limit and len(products) >= limit:
            products = products[:limit]
            break
        if len(batch) < per_page:
            break
        page += 1
        time.sleep(0.1)

    return products


def run_health_check(
    *,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run the full URL health check and return a report dict."""
    settings = get_settings()
    site_base = settings.wp_base_url

    logger.info("Fetching published WooCommerce products...")
    if dry_run:
        logger.info("[DRY RUN] Would fetch products and check URLs")
        return {"dry_run": True, "issues": []}

    products = fetch_published_products(
        wp_base_url=settings.wp_base_url,
        wp_username=settings.wp_username,
        wp_app_password=settings.wp_app_password,
        limit=limit,
    )
    logger.info(f"Checking {len(products)} product URLs...")

    results: List[URLResult] = []
    issues: List[URLResult] = []

    for i, product in enumerate(products, 1):
        url = product.get("permalink", "")
        if not url:
            continue

        status, final_url, chain = _check_url(url)
        result = URLResult(
            product_id=product.get("id", 0),
            product_name=product.get("name", ""),
            sku=product.get("sku", ""),
            original_url=url,
            final_url=final_url,
            status_code=status,
            redirect_chain=chain,
        )
        result = _diagnose(result, site_base)
        results.append(result)

        if not result.is_healthy:
            issues.append(result)
            logger.warning(f"[{i}/{len(products)}] ISSUE ({result.issue}): {url}")
        else:
            if i % 50 == 0:
                logger.info(f"[{i}/{len(products)}] checked, {len(issues)} issues so far...")

        time.sleep(REQUEST_DELAY)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_checked": len(results),
        "total_issues": len(issues),
        "issues": [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "sku": r.sku,
                "original_url": r.original_url,
                "final_url": r.final_url,
                "status_code": r.status_code,
                "issue": r.issue,
                "diagnosis": r.diagnosis,
                "redirect_chain": r.redirect_chain,
            }
            for r in issues
        ],
        "healthy": len(results) - len(issues),
    }

    # Atomic write
    tmp = REPORT_PATH.with_suffix(".tmp")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REPORT_PATH)
    logger.info(f"Report saved to {REPORT_PATH}")

    return report


def _build_telegram_message(report: Dict[str, Any]) -> str:
    total = report["total_checked"]
    issues = report["issues"]
    n = len(issues)
    date = report.get("generated_at", "")[:10]

    if n == 0:
        return (
            f"✅ *Product URL Health Check*\n"
            f"Date: {date}\n"
            f"Checked: {total} products\n"
            f"Result: All URLs healthy 🎉"
        )

    lines = [
        f"⚠️ *Product URL Health Check*",
        f"Date: {date}",
        f"Checked: {total} products",
        f"Issues found: *{n}*",
        "",
    ]

    # Group by issue type
    by_type: Dict[str, List[Dict]] = {}
    for issue in issues:
        t = issue["issue"]
        by_type.setdefault(t, []).append(issue)

    type_labels = {
        "redirect_to_homepage": "🏠 Redirects to homepage (bad redirect rule)",
        "404_not_found": "❌ 404 Not Found",
        "unexpected_redirect": "↪️ Unexpected redirect",
        "server_error": "💥 Server error",
        "connection_error": "🔌 Connection error",
    }

    for issue_type, items in by_type.items():
        label = type_labels.get(issue_type, f"⚠️ {issue_type}")
        lines.append(f"*{label}* ({len(items)})")
        for item in items[:5]:  # max 5 per type to avoid huge messages
            name = item["product_name"][:40]
            lines.append(f"  • {name}")
            lines.append(f"    `{item['original_url']}`")
        if len(items) > 5:
            lines.append(f"  _...and {len(items) - 5} more_")
        lines.append("")

    lines.append(f"Full report: `data/url_health_report.json`")
    return "\n".join(lines)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Product URL health check")
    parser.add_argument("--limit", type=int, help="Only check first N products")
    parser.add_argument("--notify", action="store_true", help="Send Telegram notification")
    parser.add_argument("--dry-run", action="store_true", help="Don't make any requests")
    args = parser.parse_args()

    report = run_health_check(limit=args.limit, dry_run=args.dry_run)

    total = report.get("total_checked", 0)
    n_issues = report.get("total_issues", 0)
    logger.info(f"\nDone: {total} checked, {n_issues} issues found")

    if n_issues > 0:
        logger.warning("Issues:")
        for item in report.get("issues", []):
            logger.warning(f"  [{item['issue']}] {item['original_url']}")
            logger.warning(f"    → {item['diagnosis']}")

    if args.notify and not args.dry_run:
        settings = get_settings()
        msg = _build_telegram_message(report)
        send_telegram(settings.telegram_bot_token, settings.telegram_chat_id, msg)
        logger.info("Telegram notification sent")

    # Obsidian vault sync — log health check result
    try:
        import sys as _sys
        _sys.path.insert(0, "/Users/michaelzhao/agents/obsidian-vault/ops")
        from obsidian_sync import log_event as _obs_log
        _obs_log(f"URL health check: {total} checked, {n_issues} issues", "sweetsworld-seo")
    except Exception:
        pass


if __name__ == "__main__":
    main()
