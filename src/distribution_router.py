"""Distribution router — decides which social channels to trigger after publish.

Reads distribution_channels from the content brief (set by PageTypeStrategy),
with fallback to page_type_registry defaults and site_registry.json.

Usage in run_mvp.py (post-publish):
    from distribution_router import get_channels_for_brief, emit_distribution_event
    channels = get_channels_for_brief(brief, page_type)
    emit_distribution_event(post_url, post_id, brief, channels)
"""
from __future__ import annotations

import json
import logging
import os
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Social distribution webhook (TypeScript server on port 8787)
_SOCIAL_WEBHOOK_URL = os.getenv("SOCIAL_WEBHOOK_URL", "http://localhost:8787/webhook/wp")
_WEBHOOK_SECRET = os.getenv("SOCIAL_WEBHOOK_SECRET", "")

# Per-type defaults (mirrors site_registry.json; used when registry isn't loaded)
_DEFAULT_CHANNELS: Dict[str, List[str]] = {
    "landing_page":      ["facebook", "instagram", "gbp", "pinterest"],
    "occasion_page":     ["facebook", "instagram", "gbp", "pinterest", "x"],
    "guide_page":        ["pinterest", "facebook"],
    "category_page":     ["pinterest", "facebook"],
    "faq_page":          ["facebook"],
    "comparison_page":   ["pinterest", "facebook", "x"],
    "best_of_page":      ["facebook", "instagram", "pinterest"],
    "city_landing_page": ["gbp", "facebook"],
}


def get_channels_for_brief(brief: Dict[str, Any], page_type: str) -> List[str]:
    """Return the list of social channels to distribute to for this page.

    Priority:
    1. brief["distribution_channels"] (set by PageTypeStrategy at brief generation time)
    2. page_type_registry defaults
    3. local _DEFAULT_CHANNELS fallback
    """
    # 1. Brief-embedded channels (most specific)
    from_brief = brief.get("distribution_channels")
    if isinstance(from_brief, list) and from_brief:
        return from_brief

    # 2. Registry
    try:
        from page_type_registry import get_distribution_channels
        return get_distribution_channels(page_type)
    except ImportError:
        pass

    # 3. Local fallback
    return _DEFAULT_CHANNELS.get(page_type, ["facebook"])


def emit_distribution_event(
    post_url: str,
    post_id: int,
    brief: Dict[str, Any],
    channels: List[str],
    excerpt: str = "",
    title: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Fire a webhook to the social distribution server with page metadata.

    Returns {success, status_code, channels_requested, dry_run}.
    On dry_run=True, logs the payload without sending.
    """
    payload = {
        "post_id":   post_id,
        "url":       post_url,           # social-agent webhook schema uses "url"
        "title":     title or brief.get("title", ""),
        "excerpt":   excerpt or brief.get("meta_description", ""),
        "page_type": brief.get("page_type", ""),
        "cluster":   brief.get("cluster", ""),
        "slug":      brief.get("slug", ""),
        "platforms": channels,           # social-agent webhook schema uses "platforms"
        "keyword":   brief.get("keyword", ""),
    }

    if dry_run:
        logger.info(f"[DRY RUN] Distribution event: {json.dumps(payload, indent=2)}")
        return {"success": True, "dry_run": True, "channels_requested": channels}

    if not _SOCIAL_WEBHOOK_URL:
        logger.warning("SOCIAL_WEBHOOK_URL not set — skipping distribution event")
        return {"success": False, "reason": "no_webhook_url", "channels_requested": channels}

    headers = {"Content-Type": "application/json"}
    if _WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = _WEBHOOK_SECRET

    try:
        response = requests.post(
            _SOCIAL_WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )
        success = response.status_code < 400
        if not success:
            logger.warning(f"Distribution webhook returned {response.status_code}: {response.text[:200]}")
        else:
            logger.info(f"Distribution event sent → {channels} for {post_url}")
        return {
            "success": success,
            "status_code": response.status_code,
            "channels_requested": channels,
            "dry_run": False,
        }
    except Exception as exc:
        logger.error(f"Distribution webhook failed: {exc}")
        return {"success": False, "reason": str(exc), "channels_requested": channels}
