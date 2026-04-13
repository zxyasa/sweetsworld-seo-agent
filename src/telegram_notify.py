"""Telegram notification module for sending updates."""
from __future__ import annotations

import html
import logging
import traceback
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


def extract_site_domain(base_url: str) -> str:
    """Return a bare domain from a configured site URL."""
    cleaned = (base_url or "").strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    return cleaned.split("/", 1)[0]


def _get_configured_site_domain() -> str:
    try:
        from config import get_settings
    except ImportError:  # pragma: no cover
        from src.config import get_settings

    return extract_site_domain(get_settings().wp_base_url)


def format_topic_suggestions(suggestions: list) -> str:
    """Format a list of SEO suggestions as Telegram-friendly HTML."""
    lines = ["🎯 <b>选题建议</b>\n"]
    for i, s in enumerate(suggestions, 1):
        title = html.escape(s.get("title", ""))
        slug = html.escape(s.get("slug", ""))
        keyword = html.escape(s.get("primary_keyword", ""))
        lines.append(f"{i}. <b>{title}</b>")
        lines.append(f"   🔑 {keyword}")
        lines.append(f"   🔗 /{slug}\n")
    return "\n".join(lines)


def send_telegram(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> None:
    """Send a message via Telegram Bot API.

    Raises:
        requests.HTTPError: If the API request fails
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured, skipping notification")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    logger.info("Telegram notification sent")


def notify_pilot_gate(bot_token: str, chat_id: str, gate: dict) -> None:
    """Send a pilot gate status update to Telegram.

    Always sends a brief daily summary. Uses a special header when the gate
    decision is 'expand' or when GSC impressions appear for the first time.
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured, skipping pilot gate notification")
        return

    decision = gate.get("decision", "unknown")
    summary = gate.get("summary", {})
    impressions = int(summary.get("total_impressions") or 0)
    clicks = int(summary.get("total_clicks") or 0)
    published = int(summary.get("published_count") or 0)
    blockers = int(summary.get("blocking_issue_count") or 0)
    next_action = gate.get("next_action", "")
    generated_at = gate.get("generated_at", "")[:10]  # date only
    site_domain = _get_configured_site_domain()
    domain_suffix = f" — {html.escape(site_domain)}" if site_domain else ""

    if decision == "expand":
        header = f"✅ <b>SEO Pilot Gate: EXPAND</b>{domain_suffix}"
    elif impressions > 0:
        header = f"📈 SEO Pilot: GSC Signal Detected!{domain_suffix}"
    else:
        header = f"📊 <b>SEO Pilot Daily Report</b>{domain_suffix}"

    blocking_reasons = gate.get("blocking_reasons") or []
    reasons_text = ""
    if blocking_reasons:
        escaped_reasons = "\n".join(f"  • {html.escape(str(r))}" for r in blocking_reasons)
        reasons_text = f"\n<b>Blocking:</b>\n{escaped_reasons}"

    text = (
        f"{header}\n"
        f"Date: <code>{html.escape(generated_at)}</code>\n"
        f"\n"
        f"Decision: <code>{html.escape(str(decision))}</code>\n"
        f"Published pages: <code>{published}</code>\n"
        f"GSC Impressions: <code>{impressions}</code>\n"
        f"GSC Clicks: <code>{clicks}</code>\n"
        f"Technical blockers: <code>{blockers}</code>"
        f"{reasons_text}\n"
        f"\n"
        f"<b>Next:</b> {html.escape(str(next_action))}"
    )

    send_telegram(bot_token, chat_id, text, parse_mode="HTML")


def send_error_alert(
    bot_token: str,
    chat_id: str,
    context: str,
    exc: Exception,
    site_id: str = "",
) -> None:
    """Push an error alert to Telegram. Swallows any send failure so it never
    masks the original exception."""
    if not bot_token or not chat_id:
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    tb = traceback.format_exc().strip()
    # Keep the traceback short to stay within Telegram's 4096-char limit
    if len(tb) > 800:
        tb = "..." + tb[-800:]

    site_line = f"Site: <code>{html.escape(site_id)}</code>\n" if site_id else ""
    text = (
        f"<b>SEO Agent Error</b>\n"
        f"{site_line}"
        f"Time: <code>{html.escape(ts)}</code>\n"
        f"Context: <code>{html.escape(str(context))}</code>\n"
        f"Error: <code>{html.escape(f'{type(exc).__name__}: {exc}')}</code>\n"
        f"<pre>{html.escape(tb)}</pre>"
    )

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as alert_exc:
        logger.warning(f"Failed to send error alert to Telegram: {alert_exc}")
