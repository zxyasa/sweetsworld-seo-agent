"""Main entry point for the SEO automation agent."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import get_settings, setup_logging
from content_brief_engine import build_content_brief, save_content_brief
from content_generator import (
    build_product_image_gallery,
    generate_article_html,
    generate_post_excerpt,
    validate_content_quality,
)
from telegram_notify import extract_site_domain, send_telegram, send_error_alert
from topic_generator import replenish_topics_csv
from product_selector import (
    load_product_catalog,
    normalize_catalog,
    pick_featured_image_url,
    select_products_for_topic,
    validate_product_urls,
)
from wp_client import WPClient

try:
    from google_indexing import submit_url as _gindex_submit_url
    GOOGLE_INDEXING_AVAILABLE = True
except ImportError:
    GOOGLE_INDEXING_AVAILABLE = False

try:
    from distribution_router import get_channels_for_brief, emit_distribution_event
    DISTRIBUTION_ROUTER_AVAILABLE = True
except ImportError:
    DISTRIBUTION_ROUTER_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

try:
    from openai_generator import OpenAIGenerator

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from gsc_client import GSCClient

    GSC_AVAILABLE = True
except ImportError:
    GSC_AVAILABLE = False

try:
    from topics_db import get_topics_db as _get_topics_db
    TOPICS_DB_AVAILABLE = True
except ImportError:
    TOPICS_DB_AVAILABLE = False

try:
    from shared.validator import SlotValidator as _SlotValidator
    _slot_validator = _SlotValidator()
    SLOT_VALIDATOR_AVAILABLE = True
except Exception:  # ImportError or FileNotFoundError if schema missing
    _slot_validator = None  # type: ignore[assignment]
    SLOT_VALIDATOR_AVAILABLE = False


NEW_POST_STATUSES = {"drafted", "published"}
COMPLETED_TOPIC_STATUSES = {"drafted", "published", "exists", "quality_blocked"}
REGISTRY_HOLD_STATUSES = {"drafted", "review_pending", "published", "monitored", "blocked"}
PUBLISH_APPROVED_STATUSES = {"approved", "published", "monitored"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Sweetsworld SEO automation workflow.")
    parser.add_argument(
        "--mode",
        choices=["batch", "daily"],
        default=None,
        help="Run all pending topics (batch) or only the daily quota (daily).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of topics to create this run. In daily mode this is the daily quota.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore local state and retry topics, while still skipping existing WordPress slugs.",
    )
    parser.add_argument(
        "--publish-created",
        action="store_true",
        help="Publish newly created drafts immediately after creating them.",
    )
    parser.add_argument(
        "--slug",
        action="append",
        default=None,
        help="Only process the specified slug. Can be passed multiple times for a narrow pilot run.",
    )
    parser.add_argument(
        "--only-approved",
        action="store_true",
        help="Only process topics whose page registry status is approved, bypassing local completion-state skips.",
    )
    parser.add_argument(
        "--generate-topics",
        action="store_true",
        help="Auto-generate and append new rows to topics.csv when the pending queue is below target.",
    )
    parser.add_argument(
        "--topic-source",
        choices=["auto", "seed", "gsc"],
        default=None,
        help="Source used when auto-generating topics into topics.csv.",
    )
    parser.add_argument(
        "--topic-seed",
        action="append",
        default=None,
        help="Seed topic area for auto-generated topics. Can be passed multiple times.",
    )
    parser.add_argument(
        "--target-pending",
        type=int,
        default=None,
        help="Maintain at least this many pending topics in topics.csv when auto-generation is enabled.",
    )
    parser.add_argument(
        "--revert-to-draft",
        action="store_true",
        help="Revert a published slug back to WordPress draft and reset registry status to 'approved'. Requires --slug.",
    )
    parser.add_argument(
        "--verify-registry",
        action="store_true",
        help=(
            "Cross-check every 'published' registry record against WordPress. "
            "Records whose post_id no longer exists in WP are marked 'orphaned'."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (use with --revert-to-draft).",
    )
    parser.add_argument(
        "--site",
        default=None,
        help=(
            "Site ID to run (e.g. sweetsworld, newcastlehub). "
            "When provided, loads SiteContext from sites/<site_id>/ for "
            "data-isolation and multi-site tracking. "
            "Omit for legacy single-site behaviour."
        ),
    )
    return parser.parse_args()


def _normalise_topic_row(row: Dict[str, str], line_number: int) -> Dict[str, str] | None:
    """Normalise a DictReader row. Accepts any superset of the 4 core columns."""
    if not any(v.strip() for v in row.values()):
        return None
    return {
        "slug": row.get("slug", "").strip(),
        "title": row.get("title", "").strip(),
        "primary_keyword": row.get("primary_keyword", "").strip(),
        "category_hint": row.get("category_hint", "").strip(),
        # New Spec columns — empty string if absent (backwards-compatible)
        "page_type": row.get("page_type", "").strip(),
        "cluster": row.get("cluster", "").strip(),
        "priority": row.get("priority", "").strip(),
        "_source_line": str(line_number),
    }


def read_topics(csv_path: Path) -> List[Dict[str, str]]:
    topics: List[Dict[str, str]] = []
    seen_slugs = set()

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for line_number, row in enumerate(reader, start=2):
            topic = _normalise_topic_row(dict(row), line_number)
            if not topic:
                continue

            slug = topic.get("slug", "").strip().lower()
            if slug and slug in seen_slugs:
                logger.warning(f"WARN: Skipping duplicate slug on line {line_number}: {slug}")
                continue
            if slug:
                seen_slugs.add(slug)

            topics.append(topic)

    return topics


def validate_topic(topic: Dict[str, str], ctx: Any = None) -> bool:
    slug = topic.get("slug", "").strip()
    title = topic.get("title", "").strip()
    line_number = topic.get("_source_line", "?")

    if not slug or not title:
        logger.warning(f"WARN: Skipping invalid topic on line {line_number}: missing slug or title")
        return False

    if not topic.get("primary_keyword", "").strip():
        topic["primary_keyword"] = title
        logger.warning(f"WARN: Topic on line {line_number} is missing primary_keyword; using title as fallback")

    if not topic.get("category_hint", "").strip():
        _default_hint = (
            getattr(ctx, "default_category_hint", None) or "Confectionery"
        ) if ctx is not None else "Confectionery"
        topic["category_hint"] = _default_hint

    return True


def default_state() -> Dict[str, Any]:
    return {"updated_at": None, "runs": [], "topics": {}}


def load_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        return default_state()

    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data.setdefault("runs", [])
            data.setdefault("topics", {})
            return data
    except json.JSONDecodeError:
        logger.warning(f"WARN: State file is invalid JSON, resetting: {state_path}")

    return default_state()


def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    tmp = state_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, state_path)


def load_json_file(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        logger.warning(f"WARN: Guardrail JSON is invalid, resetting in memory: {path}")

    return dict(default)


def save_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Strip private/computed keys (prefixed with "_") before persisting
    serialisable = {k: v for k, v in payload.items() if not k.startswith("_")}
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(serialisable, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def _warm_page_cache(url: str) -> None:
    """GET 请求新发布的页面，触发 LiteSpeed 缓存预热。失败不阻断主流程。"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SWCacheWarmer/1.0)"})
        urllib.request.urlopen(req, timeout=10)
        logger.info(f"  OK: 缓存预热完成: {url}")
    except Exception as exc:
        logger.debug(f"  缓存预热失败（不影响发布）: {exc}")


def _ping_google_sitemap(settings: Any) -> None:
    """发布后 ping Google 刷新 sitemap，确保新页面被发现。失败不阻断主流程。"""
    try:
        import urllib.request
        base = getattr(settings, "wp_base_url", "").rstrip("/")
        sitemap_url = f"{base}/sitemap_index.xml"
        urllib.request.urlopen(f"https://www.google.com/ping?sitemap={sitemap_url}", timeout=5)
        logger.info(f"  OK: Google sitemap ping 成功: {sitemap_url}")
    except Exception as exc:
        logger.debug(f"  Google sitemap ping 失败（不影响发布）: {exc}")


def _submit_to_google_indexing(url: str, settings: Any) -> None:
    """发布后立即通知 Google Indexing API，加速索引。失败不阻断主流程。"""
    if not GOOGLE_INDEXING_AVAILABLE:
        logger.debug("Google Indexing API 不可用（缺少 google-auth 依赖）")
        return
    if not getattr(settings, "indexing_api_enabled", True):
        logger.debug("跳过 Google Indexing API：indexing_api_enabled=false")
        return
    creds_file = getattr(
        settings,
        "indexing_credentials_file",
        getattr(settings, "gsc_credentials_file", ""),
    )
    if not creds_file or not Path(creds_file).exists():
        logger.debug("跳过 Google Indexing API：未配置 GSC_CREDENTIALS_FILE")
        return
    try:
        result = _gindex_submit_url(url, creds_file)
        if result.get("status") == "success":
            logger.info(f"  OK: Google Indexing API 提交成功: {url}")
        else:
            logger.warning(f"  WARN: Google Indexing API 提交失败: {result.get('message')}")
    except Exception as exc:
        logger.warning(f"  WARN: Google Indexing API 异常（不影响发布）: {exc}")


def _find_cluster_peer_links(
    topic: Dict[str, Any],
    registry: Dict[str, Any],
    all_topics: List[Dict[str, Any]],
    max_peers: int = 2,
) -> List[str]:
    """同 cluster 已发布页面的 URL 列表，排除自身，最多 max_peers 条。

    优先从 page_registry 取 post_link（已有真实 WP URL），
    其次从 all_topics 里找同 cluster 条目拼 slug 路径作为候选。
    """
    cluster = str(topic.get("cluster", "")).strip()
    self_slug = str(topic.get("slug", "")).strip().lower()
    if not cluster:
        return []

    peers: List[str] = []

    # 1. 从 registry 找同 cluster 已发布记录
    for record in registry.get("records", []):
        if str(record.get("status", "")).lower() != "published":
            continue
        rec_slug = str(record.get("slug", "")).strip().lower()
        if rec_slug == self_slug:
            continue
        # 找对应 topic 的 cluster
        matching_topic = next(
            (t for t in all_topics if str(t.get("slug", "")).strip().lower() == rec_slug),
            None,
        )
        if matching_topic and str(matching_topic.get("cluster", "")).strip() == cluster:
            link = str(record.get("post_link") or "").strip()
            if link:
                peers.append(link)
        if len(peers) >= max_peers:
            break

    return peers


_VALID_PAGE_TYPES = frozenset({
    "occasion_page", "category_page", "landing_page", "guide_page",
    "faq_page", "comparison_page", "best_of_page", "city_landing_page",
})


def resolve_page_type(topic: Dict[str, str]) -> str:
    """Return the page type for a topic.

    Priority:
    1. Explicit ``page_type`` column in topics.csv  ← Deterministic (Spec)
    2. Keyword-based heuristic fallback             ← Warn + infer (legacy)
    """
    explicit = str(topic.get("page_type", "")).strip().lower()
    if explicit in _VALID_PAGE_TYPES:
        return explicit
    if explicit:
        logger.warning(
            "WARN: topic '%s' has unknown page_type '%s'; falling back to heuristic",
            topic.get("slug", "?"),
            explicit,
        )

    # --- Heuristic fallback (only when page_type column is missing) ---
    logger.warning(
        "WARN: topic '%s' has no page_type in CSV — heuristic used. "
        "Add explicit page_type to topics.csv to follow Deterministic Layer spec.",
        topic.get("slug", "?"),
    )
    hint = str(topic.get("category_hint", "")).strip().lower()
    primary_keyword = str(topic.get("primary_keyword", "")).strip().lower()
    title = str(topic.get("title", "")).strip().lower()
    haystack = " ".join(part for part in [hint, primary_keyword, title] if part)

    if primary_keyword.startswith("best ") and " for " in primary_keyword:
        return "occasion_page"
    if "where to buy" in primary_keyword or primary_keyword.startswith(("buy ", "cheap ", "bulk ")) or " online " in f" {primary_keyword} ":
        return "landing_page"
    if primary_keyword.startswith(("what ", "how ", "why ", "when ", "which ", "are ", "is ", "can ", "do ", "does ")) or " vs " in haystack:
        return "guide_page"
    if "where to buy" in haystack or " online " in f" {haystack} ":
        return "landing_page"
    return "category_page"


# Keep old name as alias so existing call-sites don't break
infer_page_type = resolve_page_type


def _build_keyword_index(keyword_map: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build a keyword → record dict for O(1) lookups. Stored in keyword_map['_index']."""
    return {
        str(row.get("primary_keyword", "")).strip().lower(): row
        for row in keyword_map.get("records", [])
        if row.get("primary_keyword")
    }


def find_keyword_mapping(keyword_map: Dict[str, Any], primary_keyword: str) -> Optional[Dict[str, Any]]:
    keyword = primary_keyword.strip().lower()
    index = keyword_map.get("_index")
    if index is not None:
        return index.get(keyword)
    # Fallback to linear scan if index not built
    for row in keyword_map.get("records", []):
        mapped_keyword = str(row.get("primary_keyword", "")).strip().lower()
        if mapped_keyword and mapped_keyword == keyword:
            return row
    return None


def keyword_mapping_conflict(topic: Dict[str, str], keyword_map: Dict[str, Any]) -> Optional[str]:
    primary_keyword = topic.get("primary_keyword", "").strip()
    if not primary_keyword:
        return None

    mapping = find_keyword_mapping(keyword_map, primary_keyword)
    if not mapping:
        return None

    topic_slug = topic.get("slug", "").strip()
    topic_page_type = topic.get("page_type", "").strip()
    mapped_slug = str(mapping.get("canonical_slug", "")).strip()
    mapped_page_type = str(mapping.get("page_type", "")).strip()

    if mapped_slug and mapped_slug != topic_slug:
        return (
            f"Keyword ownership conflict: '{primary_keyword}' belongs to slug "
            f"'{mapped_slug}', not '{topic_slug}'"
        )
    if mapped_page_type and mapped_page_type != topic_page_type:
        return (
            f"Keyword ownership conflict: '{primary_keyword}' is mapped as "
            f"'{mapped_page_type}', not '{topic_page_type}'"
        )
    return None


def _build_registry_index(registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build a (slug, page_type) → record dict for O(1) lookups. Stored in registry['_index']."""
    return {
        f"{str(row.get('slug', '')).strip().lower()}|{str(row.get('page_type', '')).strip().lower()}": row
        for row in registry.get("records", [])
        if row.get("slug") and row.get("page_type")
    }


def find_registry_record(
    registry: Dict[str, Any],
    slug: str,
    page_type: str,
) -> Optional[Dict[str, Any]]:
    slug_normalised = slug.strip().lower()
    page_type_normalised = page_type.strip().lower()
    index = registry.get("_index")
    if index is not None:
        return index.get(f"{slug_normalised}|{page_type_normalised}")
    # Fallback to linear scan if index not built
    for row in registry.get("records", []):
        row_slug = str(row.get("slug", "")).strip().lower()
        row_page_type = str(row.get("page_type", "")).strip().lower()
        if row_slug == slug_normalised and row_page_type == page_type_normalised:
            return row
    return None


def ensure_registry_record(registry: Dict[str, Any], topic: Dict[str, str]) -> Dict[str, Any]:
    slug = topic.get("slug", "").strip()
    page_type = topic.get("page_type", "").strip()
    existing = find_registry_record(registry, slug=slug, page_type=page_type)
    if existing:
        return existing

    now = datetime.now().isoformat(timespec="seconds")
    record = {
        "keyword": topic.get("primary_keyword", ""),
        "slug": slug,
        "page_type": page_type,
        "status": "discovered",
        "intent": topic.get("intent", ""),
        "template_version": "pilot-v1",
        "product_rule_version": "pilot-v1",
        "brief_id": "",
        "created_at": now,
        "updated_at": now,
        "published_post_id": None,
        "published_at": None,
        "wp_date": None,
        "wp_date_gmt": None,
        "wp_modified": None,
        "wp_modified_gmt": None,
        "blocking_reason": None,
        "last_error": "",
        "notes": "",
    }
    registry.setdefault("records", []).append(record)
    # Keep the in-memory index in sync
    index = registry.get("_index")
    if index is not None and slug and page_type:
        index[f"{slug.lower()}|{page_type.lower()}"] = record
    return record


def save_registry_record(
    registry: Dict[str, Any],
    registry_path: Path,
    topic: Dict[str, str],
    status: Optional[str] = None,
    message: str = "",
    link: str = "",
    post_id: Optional[int] = None,
    wp_item: Optional[Dict[str, Any]] = None,
    word_count: Optional[int] = None,
) -> Dict[str, Any]:
    record = ensure_registry_record(registry, topic)
    now = datetime.now().isoformat(timespec="seconds")
    effective_status = status or str(record.get("status", "discovered"))

    record["keyword"] = topic.get("primary_keyword", "")
    record["slug"] = topic.get("slug", "")
    record["page_type"] = topic.get("page_type", "")
    if topic.get("brief_id"):
        record["brief_id"] = topic.get("brief_id")
    record["updated_at"] = now

    if effective_status == "exists":
        effective_status = "published" if post_id is not None or link else str(record.get("status", "discovered"))
    if effective_status == "error":
        effective_status = str(record.get("status", "discovered"))

    record["status"] = effective_status
    if post_id is not None:
        record["published_post_id"] = post_id
    if link:
        record["post_link"] = link

    wp_date = ""
    if isinstance(wp_item, dict):
        wp_date = str(wp_item.get("date") or "").strip()
        record["wp_date"] = wp_date or record.get("wp_date")
        record["wp_date_gmt"] = str(wp_item.get("date_gmt") or "").strip() or record.get("wp_date_gmt")
        record["wp_modified"] = str(wp_item.get("modified") or "").strip() or record.get("wp_modified")
        record["wp_modified_gmt"] = str(wp_item.get("modified_gmt") or "").strip() or record.get("wp_modified_gmt")

    if effective_status == "published":
        record["published_at"] = wp_date or record.get("published_at") or now
    if word_count is not None:
        record["word_count"] = word_count
    if effective_status == "blocked":
        record["blocking_reason"] = str(message)
    elif message:
        record["notes"] = str(message)

    record["last_error"] = message if status == "error" else ""
    save_json_file(registry_path, registry)
    return record


def registry_skip_reason(
    topic: Dict[str, str],
    registry: Dict[str, Any],
    force: bool = False,
) -> Optional[str]:
    record = find_registry_record(
        registry,
        slug=topic.get("slug", ""),
        page_type=topic.get("page_type", ""),
    )
    if not record:
        return None

    status = str(record.get("status", "")).strip().lower()
    # Always skip published — even with --force (registry is authoritative)
    if status == "published":
        return f"Page registry already marks this page as {status}"
    # --force bypasses other hold statuses (drafted, blocked, etc.)
    if not force and status in REGISTRY_HOLD_STATUSES:
        return f"Page registry already marks this page as {status}"
    return None


def _escape_markdown(text: str) -> str:
    return re.sub(r"([_\*\[\]()~`>#+\-=|{}.!])", r"\\\1", str(text or ""))


def count_new_posts_today(state: Dict[str, Any]) -> int:
    today = date.today().isoformat()
    count = 0
    for event in state.get("runs", []):
        timestamp = str(event.get("timestamp", ""))
        status = str(event.get("status", ""))
        if timestamp.startswith(today) and status in NEW_POST_STATUSES:
            count += 1
    return count


def build_pending_queue(topics: List[Dict[str, str]], state: Dict[str, Any], force: bool = False) -> List[Dict[str, str]]:
    queue: List[Dict[str, str]] = []
    topic_state = state.get("topics", {})

    for topic in topics:
        slug = topic.get("slug", "").strip()
        existing_status = str(topic_state.get(slug, {}).get("status", "")).lower()
        if not force and existing_status in COMPLETED_TOPIC_STATUSES:
            continue
        queue.append(topic)

    # Sort by priority ascending (1 = highest). Topics without priority sort last.
    def _priority_key(t: Dict[str, str]) -> int:
        raw = t.get("priority", "").strip()
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 999

    queue.sort(key=_priority_key)
    return queue


def _normalise_slug_filters(requested_slugs: Optional[List[str]]) -> set[str]:
    if not requested_slugs:
        return set()
    return {
        slug.strip().lower()
        for slug in requested_slugs
        if str(slug or "").strip()
    }


def build_targeted_queue(
    topics: List[Dict[str, str]],
    registry: Dict[str, Any],
    requested_slugs: Optional[List[str]] = None,
    only_approved: bool = False,
) -> tuple[List[Dict[str, str]], List[str]]:
    requested = _normalise_slug_filters(requested_slugs)
    matched: set[str] = set()
    queue: List[Dict[str, str]] = []

    for topic in topics:
        slug = topic.get("slug", "").strip().lower()
        if requested and slug not in requested:
            continue

        topic["page_type"] = topic.get("page_type", "") or resolve_page_type(topic)
        record = find_registry_record(
            registry,
            slug=topic.get("slug", ""),
            page_type=topic.get("page_type", ""),
        )
        registry_status = str(record.get("status", "")).strip().lower() if record else ""
        if only_approved and registry_status != "approved":
            continue

        if slug:
            matched.add(slug)
        queue.append(topic)

    missing = sorted(requested - matched)
    return queue, missing



def category_route_for_page_type(page_type: str, settings: Any, ctx: Any = None) -> Optional[Dict[str, str]]:
    page_type_key = str(page_type or "").strip().lower()

    # Multi-site: read directly from ctx.wp_categories (site.json) when available.
    # Falls through to settings-based lookup only for legacy single-site mode.
    if ctx is not None and hasattr(ctx, "wp_categories") and ctx.wp_categories:
        entry = ctx.wp_categories.get(page_type_key)
        if not entry:
            # Fallback: map unknown types to guide_page or landing_page equivalents
            fallback_key = "guide_page" if "guide" in page_type_key or "faq" in page_type_key or "comparison" in page_type_key or "best_of" in page_type_key else "landing_page"
            entry = ctx.wp_categories.get(fallback_key)
        if entry:
            slug = str(entry.get("slug") or "").strip()
            name = str(entry.get("name") or "").strip()
            if slug and name:
                return {"slug": slug, "name": name}

    routes = {
        "guide_page": {
            "slug": settings.wp_guide_category_slug,
            "name": settings.wp_guide_category_name,
        },
        "occasion_page": {
            "slug": settings.wp_occasion_category_slug,
            "name": settings.wp_occasion_category_name,
        },
        "landing_page": {
            "slug": settings.wp_landing_category_slug,
            "name": settings.wp_landing_category_name,
        },
        "category_page": {
            "slug": settings.wp_category_page_category_slug,
            "name": settings.wp_category_page_category_name,
        },
        "faq_page":          {"slug": settings.wp_guide_category_slug,   "name": settings.wp_guide_category_name},
        "comparison_page":   {"slug": settings.wp_guide_category_slug,   "name": settings.wp_guide_category_name},
        "best_of_page":      {"slug": settings.wp_guide_category_slug,   "name": settings.wp_guide_category_name},
        "city_landing_page": {"slug": settings.wp_landing_category_slug, "name": settings.wp_landing_category_name},
    }
    route = routes.get(page_type_key)
    if not route:
        return None
    slug = str(route.get("slug") or "").strip()
    name = str(route.get("name") or "").strip()
    if not slug or not name:
        return None
    return {"slug": slug, "name": name}



def resolve_post_category_id(wp_client: WPClient, settings: Any, page_type: str, ctx: Any = None) -> Optional[int]:
    route = category_route_for_page_type(page_type, settings, ctx=ctx)
    if not route:
        return None

    category = wp_client.ensure_category(slug=route["slug"], name=route["name"])
    category_id = category.get("id") if isinstance(category, dict) else None
    if category_id is None:
        raise RuntimeError(f"Failed to resolve WordPress category for page_type={page_type}")
    return int(category_id)


def build_gsc_context(gsc_client: Optional["GSCClient"], primary_keyword: str) -> Optional[Dict[str, Any]]:
    if not gsc_client or not primary_keyword:
        return None

    data = gsc_client.get_related_keywords(primary_keyword=primary_keyword, days=90, max_results=50)
    top_pages = gsc_client.get_top_pages(days=90, max_results=6)
    data["top_pages"] = top_pages
    data["internal_link_urls"] = [row.get("url", "") for row in top_pages if isinstance(row, dict) and row.get("url")]
    return data


def _title_from_wp_payload(payload: Dict[str, Any], fallback: str = "") -> str:
    title = payload.get("title")
    if isinstance(title, dict):
        return str(title.get("rendered") or title.get("raw") or fallback)
    if isinstance(title, str):
        return title
    return fallback


def find_existing_post(wp_client: WPClient, topic: Dict[str, str]) -> Optional[Dict[str, Any]]:
    slug = topic.get("slug", "").strip()
    title = topic.get("title", "").strip()

    existing = wp_client.find_post_by_slug(slug)
    if existing:
        post_id = existing.get("id")
        return {
            "id": post_id,
            "title": _title_from_wp_payload(existing, fallback=title),
            "link": existing.get("link") or f"{wp_client.base_url}/?p={post_id}",
            "status": existing.get("status", "unknown"),
            "date": existing.get("date", ""),
            "date_gmt": existing.get("date_gmt", ""),
            "modified": existing.get("modified", ""),
            "modified_gmt": existing.get("modified_gmt", ""),
        }

    for candidate in wp_client.find_similar_posts(title, max_results=3):
        candidate_title = str(candidate.get("title", "")).strip().lower()
        if title and candidate_title == title.lower():
            return candidate

    return None


def _take_pre_publish_snapshot(
    wp_client: WPClient,
    slug: str,
    project_root: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Snapshot the current WP post content before overwriting it.

    Saves to ``snapshots/pre_publish/{slug}_{timestamp}.json`` relative to
    *project_root*.  Only writes when a post with *slug* already exists in
    WordPress.  New posts are silently skipped (debug log only).

    This function is intentionally soft — any exception is caught, logged as a
    warning, and publication continues unaffected.
    """
    if dry_run:
        logger.debug("pre_publish_snapshot: dry_run=True, skipping for slug '%s'", slug)
        return

    try:
        existing = wp_client.find_post_by_slug(slug)
        if existing is None:
            logger.debug("New post, no pre-publish snapshot needed for slug '%s'", slug)
            return

        post_id = existing.get("id")
        title = (existing.get("title") or {}).get("rendered", "")
        content_rendered = (existing.get("content") or {}).get("rendered", "")
        excerpt_rendered = (existing.get("excerpt") or {}).get("rendered", "")
        wp_modified = existing.get("modified", "")

        content_bytes = content_rendered.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()[:8]

        snapshot: Dict[str, Any] = {
            "snapshot_type": "pre_publish",
            "slug": slug,
            "post_id": post_id,
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": title,
            "content_length": len(content_bytes),
            "content_hash": content_hash,
            "excerpt": excerpt_rendered,
            "wp_modified": wp_modified,
        }

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        snapshot_dir = project_root / "snapshots" / "pre_publish"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{slug}_{timestamp}.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("  pre_publish_snapshot: saved to %s (post_id=%s, len=%d)", snapshot_path, post_id, len(content_bytes))

    except Exception as exc:  # noqa: BLE001
        logger.warning("pre_publish_snapshot: failed for slug '%s' (non-blocking): %s", slug, exc)


def _attach_featured_image_from_products(
    wp_client: WPClient,
    post_id: int | None,
    selected_products: List[Dict[str, Any]],
) -> Optional[int]:
    if post_id is None:
        return None

    image_url = pick_featured_image_url(selected_products)
    if not image_url:
        return None

    media = wp_client.find_media_by_source_url(image_url)
    media_id = media.get("id") if isinstance(media, dict) else None
    if not media_id:
        logger.warning("WARN: No WordPress media match found for selected product image: %s", image_url)
        return None

    try:
        wp_client.set_featured_media(int(post_id), int(media_id))
        logger.info("  OK: Set featured image from site media ID %s", media_id)
        return int(media_id)
    except Exception as exc:
        logger.warning("WARN: Failed to set featured image on post %s: %s", post_id, exc)
        return None


def _upsert_product_image_gallery(
    html_content: str,
    selected_products: List[Dict[str, Any]],
) -> str:
    if not html_content:
        return html_content

    gallery_html = build_product_image_gallery(selected_products)
    if not gallery_html:
        return html_content

    existing_gallery_pattern = re.compile(
        r"<(?:section|aside) class=[\"']seo-product-gallery[\"'][^>]*>.*?</(?:section|aside)>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    had_existing_gallery = bool(existing_gallery_pattern.search(html_content))
    content_without_gallery = existing_gallery_pattern.sub("", html_content, count=1)

    if "<img" in content_without_gallery.lower() and not had_existing_gallery:
        return html_content

    heading_matches = [
        match
        for match in re.finditer(r"<h[23]\b[^>]*>(.*?)</h[23]>", content_without_gallery, flags=re.IGNORECASE | re.DOTALL)
        if "frequently asked questions" not in re.sub(r"<[^>]+>", " ", match.group(1)).strip().lower()
    ]
    if heading_matches:
        target_offset = int(len(content_without_gallery) * 0.4)
        anchor_matches = heading_matches[1:] if len(heading_matches) > 1 else heading_matches
        candidate_matches = [
            match for match in anchor_matches
            if match.start() >= int(len(content_without_gallery) * 0.22)
        ] or anchor_matches
        closest_match = min(candidate_matches, key=lambda match: abs(match.start() - target_offset))
        if closest_match.start() > 0:
            return (
                content_without_gallery[: closest_match.start()]
                + gallery_html
                + content_without_gallery[closest_match.start() :]
            )

    faq_match = re.search(
        r"(<section[^>]*class=[\"'][^\"']*faq-section[^\"']*[\"'][^>]*>|<h2[^>]*>\s*Frequently Asked Questions\s*</h2>)",
        content_without_gallery,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if faq_match:
        return content_without_gallery[: faq_match.start()] + gallery_html + content_without_gallery[faq_match.start() :]

    closing_article_matches = list(re.finditer(r"</article>", content_without_gallery, flags=re.IGNORECASE))
    if closing_article_matches:
        insert_at = closing_article_matches[-1].start()
        return content_without_gallery[:insert_at] + gallery_html + content_without_gallery[insert_at:]

    intro_match = re.search(r"(<p[^>]*class=[\"']intro[\"'][^>]*>.*?</p>)", content_without_gallery, flags=re.IGNORECASE | re.DOTALL)
    if intro_match:
        return content_without_gallery[: intro_match.end()] + gallery_html + content_without_gallery[intro_match.end() :]

    paragraph_match = re.search(r"(<p\b[^>]*>.*?</p>)", content_without_gallery, flags=re.IGNORECASE | re.DOTALL)
    if paragraph_match:
        return content_without_gallery[: paragraph_match.end()] + gallery_html + content_without_gallery[paragraph_match.end() :]

    article_match = re.search(r"(<article\b[^>]*>)", content_without_gallery, flags=re.IGNORECASE)
    if article_match:
        return content_without_gallery[: article_match.end()] + gallery_html + content_without_gallery[article_match.end() :]

    return gallery_html + content_without_gallery


def record_topic_result(
    state: Dict[str, Any],
    topic: Dict[str, str],
    status: str,
    message: str = "",
    link: str = "",
    post_id: Optional[int] = None,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    slug = topic.get("slug", "").strip()
    entry = dict(state.get("topics", {}).get(slug, {}))
    entry.update(
        {
            "slug": slug,
            "title": topic.get("title", ""),
            "status": status,
            "last_attempted_at": now,
            "post_link": link or entry.get("post_link", ""),
            "post_id": post_id if post_id is not None else entry.get("post_id"),
            "last_error": message if status == "error" else "",
        }
    )
    if status in COMPLETED_TOPIC_STATUSES:
        entry["last_success_at"] = now

    state.setdefault("topics", {})[slug] = entry
    state.setdefault("runs", []).append(
        {
            "timestamp": now,
            "slug": slug,
            "title": topic.get("title", ""),
            "status": status,
            "link": link,
            "post_id": post_id,
            "message": message,
        }
    )
    state["runs"] = state["runs"][-200:]


def build_telegram_message(results: List[Dict[str, Any]], mode: str, site_domain: str) -> str:
    created = [row for row in results if row["status"] in NEW_POST_STATUSES]
    existing = [row for row in results if row["status"] == "exists"]
    errors = [row for row in results if row["status"] == "error"]

    domain_suffix = f" — {site_domain}" if site_domain else ""
    lines = [f"✅ SEO {mode} run finished{domain_suffix}", ""]
    lines.append(f"Created or published: {len(created)}")
    lines.append(f"Already existed: {len(existing)}")
    lines.append(f"Errors: {len(errors)}")

    if created:
        lines.append("")
        lines.append("New content:")
        for row in created:
            lines.append(f"- {_escape_markdown(row['title'])}")
            if row.get("link"):
                lines.append(f"  {_escape_markdown(row['link'])}")

    if existing:
        lines.append("")
        lines.append("Skipped existing:")
        for row in existing[:5]:
            lines.append(f"- {_escape_markdown(row['title'])}")

    if errors:
        lines.append("")
        lines.append("Errors:")
        for row in errors[:5]:
            lines.append(f"- {_escape_markdown(row['title'])}: {_escape_markdown(row['message'])}")

    return "\n".join(lines)


def maybe_replenish_topics(
    csv_path: Path,
    topics: List[Dict[str, str]],
    pending_topics: List[Dict[str, str]],
    settings: Any,
    args: argparse.Namespace,
    gsc_client: Optional["GSCClient"],
) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    auto_generate_topics = args.generate_topics or settings.auto_generate_topics
    if not auto_generate_topics:
        return topics, pending_topics

    target_pending = args.target_pending if args.target_pending is not None else settings.topic_target_pending
    topic_source = args.topic_source or settings.topic_generation_source
    topic_seeds = list(settings.topic_seeds)
    if args.topic_seed:
        topic_seeds = args.topic_seed + topic_seeds

    logger.info(f"INFO: Auto topic generation enabled (source={topic_source}, target_pending={target_pending})")
    report = replenish_topics_csv(
        csv_path=csv_path,
        existing_topics=topics,
        pending_topics=pending_topics,
        target_pending=target_pending,
        source=topic_source,
        seed_topics=topic_seeds,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        gsc_client=gsc_client,
    )

    added = report.get("added", []) or []
    if added:
        logger.info(f"OK: Added {len(added)} new topic(s) to topics.csv")
        for topic in added[:5]:
            logger.info(f"   - {topic['title']} [{topic['slug']}]")
        topics = read_topics(csv_path)
        pending_topics = build_pending_queue(topics, default_state(), force=False)
    elif report.get("requested", 0) > 0:
        logger.warning(f"WARN: Topic generation ran but did not add unique rows ({report.get('reason', 'unknown')})")
    else:
        logger.info("INFO: Pending queue already meets topic target; no new rows added")

    return topics, pending_topics


def main() -> None:
    args = parse_args()
    setup_logging()

    logger.info("SEO Automation Agent - Starting...")

    # ── Multi-site: load SiteContext when --site is provided ──────────────────
    # This is an additive hook — existing logic is fully unchanged.
    # SiteContext gives us: data isolation, per-site DB, contamination guard.
    _site_ctx = None
    if getattr(args, "site", None):
        try:
            from site_context import load_site_context, apply_site_context_env
            from sites_registry import SitesRegistry
            _site_ctx = load_site_context(args.site)
            apply_site_context_env(_site_ctx)
            SitesRegistry().record_run(args.site)
            logger.info("Multi-site mode: site=%s  base_url=%s", args.site, _site_ctx.base_url)
        except Exception as _exc:
            logger.error("Failed to load SiteContext for --site %s: %s", args.site, _exc)
            sys.exit(1)
    # _site_ctx is available to future refactor phases; not yet wired into
    # existing code paths so all current behaviour is preserved.

    try:
        settings = get_settings()
        logger.info("INFO: Configuration loaded")
        logger.info(f"   WordPress: {settings.wp_base_url}")
        logger.info(f"   Username: {settings.wp_username}")
    except RuntimeError as exc:
        # In multi-site mode the root .env may be absent; SiteContext overrides
        # will supply all required credentials in the block below.
        if _site_ctx is None:
            logger.error(f"ERROR: Configuration error: {exc}")
            sys.exit(1)
        logger.warning("WARN: get_settings() raised RuntimeError in multi-site mode; "
                       "SiteContext overrides will supply credentials. (%s)", exc)
        from config import Settings
        _site_categories = _site_ctx.wp_categories or {}
        _seo_run_mode = (os.getenv("SEO_RUN_MODE", "batch").strip().lower() or "batch")
        if _seo_run_mode not in {"batch", "daily"}:
            _seo_run_mode = "batch"
        _topic_generation_source = (os.getenv("TOPIC_GENERATION_SOURCE", "auto").strip().lower() or "auto")
        if _topic_generation_source not in {"auto", "seed", "gsc"}:
            _topic_generation_source = "auto"
        try:
            _topic_target_pending = max(int(os.getenv("TOPIC_TARGET_PENDING", "5")), 1)
        except ValueError:
            _topic_target_pending = 5
        _topic_seeds = [item.strip() for item in os.getenv("TOPIC_SEEDS", "candy").split(",") if item.strip()] or ["candy"]
        _site_data_dir = Path(__file__).parent.parent / "sites" / _site_ctx.site_id / "data"

        settings = Settings(
            wp_base_url=_site_ctx.base_url,
            wp_username=_site_ctx.wp_username,
            wp_app_password=_site_ctx.wp_password,
            telegram_bot_token=_site_ctx.telegram_bot_token,
            telegram_chat_id=_site_ctx.telegram_chat_id,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o",
            use_ai_generation=os.getenv("USE_AI_GENERATION", "").strip().lower() in {"1", "true", "yes", "on"},
            gsc_property_url=_site_ctx.gsc_property_url or "",
            gsc_credentials_file=str(_site_ctx.gsc_credentials_file) if _site_ctx.gsc_credentials_file.exists() else "",
            use_gsc_data=bool(_site_ctx.gsc_property_url),
            seo_run_mode=_seo_run_mode,
            daily_limit=_site_ctx.daily_publish_limit,
            state_file=str(_site_data_dir / "seo_daily_state.json"),
            auto_publish_created_posts=bool(_site_ctx.auto_publish),
            auto_generate_topics=os.getenv("AUTO_GENERATE_TOPICS", "").strip().lower() in {"1", "true", "yes", "on"},
            topic_generation_source=_topic_generation_source,
            topic_target_pending=_topic_target_pending,
            topic_seeds=_topic_seeds,
            wp_guide_category_slug=_site_categories.get("guide_page", {}).get("slug", "candy-guides"),
            wp_guide_category_name=_site_categories.get("guide_page", {}).get("name", "Candy Guides"),
            wp_occasion_category_slug=_site_categories.get("occasion_page", {}).get("slug", "candy-guides"),
            wp_occasion_category_name=_site_categories.get("occasion_page", {}).get("name", "Candy Guides"),
            wp_landing_category_slug=_site_categories.get("landing_page", {}).get("slug", "where-to-buy"),
            wp_landing_category_name=_site_categories.get("landing_page", {}).get("name", "Where to Buy"),
            wp_category_page_category_slug=_site_categories.get("category_page", {}).get("slug", "products"),
            wp_category_page_category_name=_site_categories.get("category_page", {}).get("name", "Products"),
        )

    # ── When --site is provided, override settings with SiteContext values ────
    # This ensures WP credentials, Telegram, GSC, and daily limit all come
    # from the site-specific .env, never from the shared root .env.
    if _site_ctx:
        settings.indexing_api_enabled = bool(_site_ctx.indexing_api_enabled)
        settings.wp_base_url      = _site_ctx.base_url
        settings.wp_username      = _site_ctx.wp_username
        settings.wp_app_password  = _site_ctx.wp_password
        settings.telegram_bot_token = _site_ctx.telegram_bot_token
        settings.telegram_chat_id   = _site_ctx.telegram_chat_id
        settings.daily_limit        = _site_ctx.daily_publish_limit
        settings.auto_publish_created_posts = _site_ctx.auto_publish
        if _site_ctx.gsc_credentials_file.exists():
            settings.gsc_credentials_file = str(_site_ctx.gsc_credentials_file)
        else:
            settings.gsc_credentials_file = ""
        if _site_ctx.indexing_key_file and _site_ctx.indexing_key_file.exists():
            settings.indexing_credentials_file = str(_site_ctx.indexing_key_file)
        else:
            settings.indexing_credentials_file = settings.gsc_credentials_file
        # P1-4: wire GSC property URL and use_gsc_data from SiteContext
        if _site_ctx.gsc_property_url:
            settings.gsc_property_url = _site_ctx.gsc_property_url
            settings.use_gsc_data = True
        # Use site-specific state file to prevent quota cross-contamination
        _site_data_dir = Path(__file__).parent.parent / "sites" / _site_ctx.site_id / "data"
        _site_data_dir.mkdir(parents=True, exist_ok=True)
        settings.state_file = str(_site_data_dir / "seo_daily_state.json")
        # Propagate base_url override to os.environ so that helper functions
        # (content_brief_engine, openai_generator) that call get_settings() directly
        # also pick up the correct site URL instead of the sweetsworld default.
        os.environ["WP_BASE_URL"] = _site_ctx.base_url
        # Inject site-specific collection URLs into content_brief_engine so that
        # internal link candidates use the correct site paths (not sweetsworld candy paths).
        try:
            from content_brief_engine import set_site_collection_urls as _set_collection_urls
            _set_collection_urls(_site_ctx.collection_urls)
        except Exception as e:
            logging.warning("set_site_collection_urls failed for %s: %s", _site_ctx.site_id, e)
            pass
        logger.info(
            "   [multi-site] Overrode settings from SiteContext: site=%s base_url=%s limit=%d",
            _site_ctx.site_id, _site_ctx.base_url, _site_ctx.daily_publish_limit,
        )

    # --revert-to-draft: handled before normal publishing flow
    if getattr(args, "revert_to_draft", False):
        slug = args.slug[0].strip() if args.slug else None
        if not slug:
            logger.error("ERROR: --revert-to-draft requires --slug <slug>")
            sys.exit(1)

        data_dir = Path(__file__).parent.parent / "data"
        registry_path = data_dir / "page_registry.json"
        registry = load_json_file(registry_path, {"schema_version": 1, "records": []})
        registry["_index"] = _build_registry_index(registry)

        # Find any published record with this slug
        record = next(
            (r for r in registry.get("records", [])
             if str(r.get("slug", "")).strip().lower() == slug.lower()
             and str(r.get("status", "")).lower() == "published"),
            None,
        )
        if not record:
            logger.error(f"ERROR: No published registry record found for slug '{slug}'")
            sys.exit(1)

        post_id = record.get("published_post_id")
        post_link = record.get("post_link", "")
        if not post_id:
            logger.error(f"ERROR: Registry record for '{slug}' has no published_post_id")
            sys.exit(1)

        if not getattr(args, "yes", False):
            print(f"\nAbout to revert to draft:")
            print(f"  Slug:    {slug}")
            print(f"  Post ID: {post_id}")
            print(f"  URL:     {post_link}")
            confirm = input("\nProceed? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                sys.exit(0)

        wp_client = WPClient(
            base_url=settings.wp_base_url,
            username=settings.wp_username,
            app_password=settings.wp_app_password,
        )
        wp_client.revert_to_draft(int(post_id))
        record["status"] = "approved"
        record["published_post_id"] = None
        record["published_at"] = None
        record["post_link"] = ""
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        record["notes"] = str(record.get("notes") or "") + " | reverted to draft"
        save_json_file(registry_path, registry)
        logger.info(f"OK: '{slug}' reverted to draft. Registry status → approved.")
        sys.exit(0)

    # --verify-registry: cross-check published records against live WordPress
    if getattr(args, "verify_registry", False):
        data_dir = Path(__file__).parent.parent / "data"
        registry_path = data_dir / "page_registry.json"
        registry = load_json_file(registry_path, {"schema_version": 1, "records": []})
        registry["_index"] = _build_registry_index(registry)

        wp_client = WPClient(
            base_url=settings.wp_base_url,
            username=settings.wp_username,
            app_password=settings.wp_app_password,
        )

        published_records = [
            r for r in registry.get("records", [])
            if str(r.get("status", "")).lower() == "published"
        ]
        logger.info(f"INFO: Verifying {len(published_records)} published record(s) against WordPress...")

        orphaned, verified = 0, 0
        now = datetime.now().isoformat(timespec="seconds")
        for record in published_records:
            slug = str(record.get("slug") or "")
            post_id = record.get("published_post_id")
            wp_item = wp_client.find_post_by_slug(slug, statuses=["publish", "draft", "private"])
            if wp_item:
                verified += 1
                logger.info(f"  OK: {slug} — WP post {wp_item.get('id')} ({wp_item.get('status')})")
            else:
                orphaned += 1
                record["status"] = "orphaned"
                record["blocking_reason"] = "post no longer found in WordPress"
                record["updated_at"] = now
                logger.warning(f"  ORPHANED: {slug} — no matching WP post found (post_id={post_id})")

        if orphaned:
            save_json_file(registry_path, registry)
            logger.warning(f"WARN: {orphaned} orphaned record(s) written to registry.")
        logger.info(f"INFO: Verification complete — {verified} OK, {orphaned} orphaned.")
        print(json.dumps({"verified": verified, "orphaned": orphaned}))
        sys.exit(0)

    run_mode = args.mode or settings.seo_run_mode
    publish_created = args.publish_created or settings.auto_publish_created_posts
    requested_limit = args.limit if args.limit is not None else (settings.daily_limit if run_mode == "daily" else None)

    logger.info(f"   Run mode: {run_mode}")
    logger.info(f"   Daily limit: {settings.daily_limit}")
    logger.info(f"   Auto-publish: {'on' if publish_created else 'off'}")
    logger.info(f"   Auto-generate topics: {'on' if (args.generate_topics or settings.auto_generate_topics) else 'off'}\n")

    wp_client = WPClient(
        base_url=settings.wp_base_url,
        username=settings.wp_username,
        app_password=settings.wp_app_password,
    )

    logger.info("INFO: Testing WordPress connection...")
    if not wp_client.test_connection():
        err_msg = f"Cannot connect to WordPress REST API at {settings.wp_base_url}"
        logger.error(f"ERROR: {err_msg}")
        logger.info("   Please check your configuration and network connection.")
        logger.info(f"   Try accessing: {settings.wp_base_url}/wp-json/wp/v2/posts")
        send_error_alert(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            context="wp_client.test_connection",
            exc=ConnectionError(err_msg),
            site_id=getattr(settings, "site_id", ""),
        )
        sys.exit(1)
    logger.info("INFO: WordPress connection successful\n")

    openai_generator = None
    if settings.use_ai_generation:
        if not OPENAI_AVAILABLE:
            logger.warning("WARN: OpenAI requested but openai package not installed")
            logger.info("   Run: pip install openai")
            logger.info("   Falling back to template generation\n")
        elif not settings.openai_api_key:
            logger.warning("WARN: USE_AI_GENERATION=true but OPENAI_API_KEY not set")
            logger.info("   Falling back to template generation\n")
        else:
            try:
                _site_desc = (
                    f"{_site_ctx.display_name} ({_site_ctx.base_url}), {_site_ctx.audience}"
                    if _site_ctx else
                    "sweetsworld.com.au, an Australian candy and confectionery e-commerce store"
                )
                openai_generator = OpenAIGenerator(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    site_description=_site_desc,
                    base_url=settings.wp_base_url,
                    collection_urls=_site_ctx.collection_urls if _site_ctx else None,
                    prompt_config=_site_ctx.prompt_config if _site_ctx else None,
                )
                logger.info(f"INFO: OpenAI enabled (model: {settings.openai_model})\n")
            except Exception as exc:
                logger.warning(f"WARN: Failed to initialize OpenAI: {exc}")
                logger.info("   Falling back to template generation\n")

    gsc_client = None
    if settings.use_gsc_data:
        if not GSC_AVAILABLE:
            logger.warning("WARN: GSC requested but google-api-python-client not installed")
            logger.info("   Continuing without GSC data\n")
        elif not settings.gsc_property_url:
            logger.warning("WARN: USE_GSC_DATA=true but GSC_PROPERTY_URL not set")
            logger.info("   Continuing without GSC data\n")
        else:
            try:
                gsc_client = GSCClient(
                    property_url=settings.gsc_property_url,
                    credentials_file=settings.gsc_credentials_file,
                )
                logger.info("INFO: Google Search Console enabled\n")
            except Exception as exc:
                logger.warning(f"WARN: Failed to initialize GSC: {exc}")
                logger.info("   Continuing without GSC data\n")

    if _site_ctx:
        topics_csv_path = _site_ctx.site_dir / "topics.csv"
    else:
        topics_csv_path = Path(__file__).parent.parent / "topics.csv"
    auto_generate_topics = args.generate_topics or settings.auto_generate_topics
    if topics_csv_path.exists():
        topics = read_topics(topics_csv_path)
    elif auto_generate_topics:
        logger.info(f"INFO: topics.csv does not exist yet; it will be created at {topics_csv_path}")
        topics = []
    else:
        logger.error(f"ERROR: Topics file not found: {topics_csv_path}")
        sys.exit(1)

    state_path = Path(settings.state_file)
    state = load_state(state_path)

    # USE_TOPICS_DB: merge completed statuses from DB into state so build_pending_queue filters them
    _topics_db = None
    if _site_ctx and TOPICS_DB_AVAILABLE:
        # Multi-site: always use site-specific topics.db — no env var needed
        try:
            from topics_db import TopicsDB as _TopicsDB
            _topics_db = _TopicsDB(str(_site_ctx.site_dir / "data" / "topics.db"))
            logger.info("INFO: [multi-site] topics_db loaded from %s", _topics_db.db_path)
        except Exception as _site_db_exc:
            logger.warning("WARN: site topics_db init failed: %s", _site_db_exc)
    elif TOPICS_DB_AVAILABLE:
        try:
            _topics_db = _get_topics_db()
            if _topics_db:
                import sqlite3 as _sq
                with _sq.connect(_topics_db.db_path) as _c:
                    for _r in _c.execute("SELECT slug, status FROM topics WHERE status != 'pending'"):
                        state.setdefault("topics", {}).setdefault(_r[0], {})["status"] = _r[1]
                logger.info("INFO: topics_db active — completed slugs seeded into state filter")
        except Exception as _db_init_exc:
            logger.warning(f"WARN: topics_db init failed, falling back to state.json: {_db_init_exc}")
            _topics_db = None

    # P1-2: in site mode, scope data paths to the site directory
    data_dir = (_site_ctx.site_dir / "data") if _site_ctx else Path(__file__).parent.parent / "data"
    page_registry_path = data_dir / "page_registry.json"
    keyword_map_path = data_dir / "keyword_page_map.json"
    product_catalog_path = data_dir / "products.json"
    content_briefs_dir = (
        _site_ctx.site_dir / "content_briefs"
    ) if _site_ctx else Path(__file__).parent.parent / "content_briefs"
    page_registry = load_json_file(page_registry_path, {"schema_version": 1, "records": []})
    page_registry["_index"] = _build_registry_index(page_registry)

    keyword_page_map = load_json_file(keyword_map_path, {"schema_version": 1, "records": []})
    keyword_page_map["_index"] = _build_keyword_index(keyword_page_map)

    if _site_ctx:
        from catalog_loader import load_catalog as _load_catalog
        _site_items = _load_catalog(_site_ctx)
        # Convert CatalogItem → legacy dict format via .extra (preserves all original fields).
        # For services, .extra contains the raw services.json entry which downstream can use.
        product_catalog = normalize_catalog([item.extra for item in _site_items])
        logger.info("INFO: [multi-site] Loaded %d %s from catalog", len(product_catalog), _site_ctx.catalog_type)
    else:
        product_catalog = load_product_catalog(product_catalog_path)

    pending_topics = build_pending_queue(topics, state, force=args.force)
    topics, pending_topics = maybe_replenish_topics(
        csv_path=topics_csv_path,
        topics=topics,
        pending_topics=pending_topics,
        settings=settings,
        args=args,
        gsc_client=gsc_client,
    )
    pending_topics = build_pending_queue(topics, state, force=args.force)

    # USE_TOPICS_DB: if DB is active and no targeted filters, load queue directly from DB
    # (DB already filters status='pending' and sorts by priority ASC)
    if _topics_db is not None and not args.slug and not args.only_approved and not args.force:
        try:
            db_queue = _topics_db.get_pending_queue()
            if db_queue:
                pending_topics = db_queue
                logger.info(f"INFO: topics_db queue — {len(pending_topics)} pending topics loaded from DB")
            else:
                logger.info("INFO: topics_db queue empty, falling back to CSV-based queue")
        except Exception as _db_queue_exc:
            logger.warning(f"WARN: topics_db queue failed, using CSV queue: {_db_queue_exc}")

    if args.slug or args.only_approved:
        pending_topics, missing_requested_slugs = build_targeted_queue(
            topics,
            page_registry,
            requested_slugs=args.slug,
            only_approved=args.only_approved,
        )
        if args.slug:
            logger.info(f"INFO: Explicit slug filter selected {len(pending_topics)} topic(s)")
            if missing_requested_slugs:
                logger.warning(f"WARN: Requested slug(s) not found in topics.csv or registry scope: {', '.join(missing_requested_slugs)}")
        if args.only_approved:
            logger.info(f"INFO: Approved-only filter selected {len(pending_topics)} topic(s)")

    logger.info(f"INFO: Found {len(topics)} topics in topics.csv")
    if not topics:
        logger.warning("WARN: No topics to process")
        sys.exit(0)

    queue_label = "targeted filters" if (args.slug or args.only_approved) else "local state filter"
    logger.info(f"INFO: Pending topics after {queue_label}: {len(pending_topics)}")
    logger.info(f"INFO: State file: {state_path}\n")

    if not pending_topics:
        logger.info("INFO: No pending topics remain. Nothing to do.")
        sys.exit(0)

    daily_remaining = None
    if run_mode == "daily":
        daily_quota = max(requested_limit or settings.daily_limit, 1)
        already_created_today = count_new_posts_today(state)
        daily_remaining = daily_quota if args.force else max(daily_quota - already_created_today, 0)
        logger.info(f"INFO: Daily target for this run: {daily_remaining} new post(s)\n")
        if daily_remaining <= 0:
            logger.info("INFO: Daily quota already reached. Nothing to do.")
            sys.exit(0)
    elif requested_limit is not None:
        pending_topics = pending_topics[: max(requested_limit, 1)]

    results: List[Dict[str, Any]] = []
    new_posts_created = 0

    # Inject site-specific brand/locale profile into content generator
    if _site_ctx:
        from content_generator import SiteProfile, set_site_profile
        set_site_profile(SiteProfile.from_context(_site_ctx))
        logger.info("INFO: [multi-site] SiteProfile set for %s", _site_ctx.site_id)

    for topic in pending_topics:
        if run_mode == "daily" and daily_remaining is not None and new_posts_created >= daily_remaining:
            break

        title = topic.get("title", "Unknown")
        logger.info(f"Processing: {title}")

        if not validate_topic(topic, ctx=_site_ctx):
            record_topic_result(state, topic, status="error", message="Invalid topic row")
            save_state(state_path, state)
            results.append({"title": title, "status": "error", "message": "Invalid topic row"})
            continue

        topic["page_type"] = resolve_page_type(topic)
        registry_record = ensure_registry_record(page_registry, topic)
        save_json_file(page_registry_path, page_registry)

        ownership_conflict = keyword_mapping_conflict(topic, keyword_page_map)
        if ownership_conflict:
            logger.info(f"  BLOCK: {ownership_conflict}")
            save_registry_record(
                page_registry,
                page_registry_path,
                topic,
                status="blocked",
                message=ownership_conflict,
            )
            record_topic_result(state, topic, status="error", message=ownership_conflict)
            save_state(state_path, state)
            results.append({"title": title, "status": "error", "message": ownership_conflict})
            continue

        registry_reason = registry_skip_reason(topic, page_registry, force=args.force)
        if registry_reason:
            logger.info(f"  SKIP: {registry_reason}")
            save_registry_record(
                page_registry,
                page_registry_path,
                topic,
                message=registry_reason,
            )
            record_topic_result(state, topic, status="exists", message=registry_reason)
            save_state(state_path, state)
            if _topics_db:
                _topics_db.mark_status(topic.get("slug", ""), "exists")
            results.append({"title": title, "status": "exists", "message": registry_reason})
            continue

        try:
            selected_products = select_products_for_topic(topic, product_catalog)
            selected_products = validate_product_urls(selected_products)
            topic["selected_products"] = selected_products
            if selected_products:
                logger.info(f"  INFO: Selected {len(selected_products)} product(s) from catalog (URLs verified)")
            else:
                logger.info("  INFO: No deterministic product matches found; continuing without product recommendations")

            gsc_data = build_gsc_context(gsc_client, topic.get("primary_keyword", ""))
            if gsc_data and gsc_data.get("related_keywords"):
                logger.info(f"  INFO: Found {len(gsc_data['related_keywords'])} related keywords from GSC")

            # 注入同 cluster 已发布页面的 URL，供内链引擎优先选用
            topic["cluster_peer_links"] = _find_cluster_peer_links(
                topic, page_registry, all_topics=topics
            )
            # Multi-site: supplement with peers from site.db (DB may have more up-to-date records)
            if _site_ctx and topic.get("cluster"):
                _db_peers = _site_ctx.db.get_cluster_peers(topic["cluster"], topic.get("slug", ""))
                _existing_urls = {
                    p["url"] if isinstance(p, dict) else p
                    for p in topic["cluster_peer_links"]
                }
                for _p in _db_peers:
                    if _p.get("url") and _p["url"] not in _existing_urls:
                        topic["cluster_peer_links"].append(_p["url"])
                        _existing_urls.add(_p["url"])
            if topic["cluster_peer_links"]:
                logger.info(f"  INFO: Found {len(topic['cluster_peer_links'])} same-cluster peer link(s)")

            content_brief = build_content_brief(topic, gsc_data=gsc_data)
            topic["brief_id"] = content_brief.get("brief_id", "")
            brief_path = save_content_brief(content_briefs_dir, content_brief)
            logger.info(f"  INFO: Saved content brief: {brief_path}")

            category_id = resolve_post_category_id(wp_client, settings, topic.get("page_type", ""), ctx=_site_ctx)
            if category_id is not None:
                logger.info(f"  INFO: Using WordPress category ID {category_id} for {topic.get('page_type', '')}")

            # Construct expected permalink for Schema.org markup
            cat_route = category_route_for_page_type(topic.get("page_type", ""), settings, ctx=_site_ctx)
            expected_page_url = ""
            if cat_route:
                base = settings.wp_base_url.rstrip("/")
                expected_page_url = f"{base}/{cat_route['slug']}/{topic['slug']}/"

            html_content = generate_article_html(
                topic_dict=topic,
                use_ai=bool(openai_generator),
                openai_generator=openai_generator,
                gsc_data=gsc_data,
                content_brief=content_brief,
                page_url=expected_page_url,
            )
            html_content = _upsert_product_image_gallery(html_content, selected_products)
            excerpt = generate_post_excerpt(topic, gsc_data, content_brief=content_brief)
            generation_mode = "AI-powered" if openai_generator else "template"
            logger.info(f"  OK: Generated HTML content ({len(html_content)} characters, {generation_mode})")

            # Quality gate — block publish if content doesn't meet minimum thresholds
            quality_ok, quality_reasons = validate_content_quality(
                html_content,
                topic,
                title=title,
                excerpt=excerpt,
            )
            if not quality_ok:
                for reason in quality_reasons:
                    logger.error(f"  QUALITY BLOCK: {reason}")
                save_registry_record(
                    page_registry, page_registry_path, topic,
                    status="quality_blocked",
                    message="; ".join(quality_reasons),
                )
                record_topic_result(state, topic, status="quality_blocked", message="; ".join(quality_reasons))
                save_state(state_path, state)
                if _topics_db:
                    _topics_db.mark_status(topic.get("slug", ""), "quality_blocked",
                                           quality_reasons=quality_reasons)
                if _site_ctx:
                    _site_ctx.db.upsert_page({
                        "slug": topic.get("slug", ""), "page_type": topic.get("page_type", ""),
                        "status": "quality_blocked", "blocking_reason": "; ".join(quality_reasons),
                    })
                    _site_ctx.db.log_publish(topic.get("slug", ""), "quality_blocked", details={"reasons": quality_reasons})
                continue

            # Slot validation — soft gate: log warning but never block publish
            if SLOT_VALIDATOR_AVAILABLE and _slot_validator is not None:
                try:
                    _slot_result = _slot_validator.validate(
                        html_content, topic.get("page_type", "")
                    )
                    if not _slot_result.passed:
                        logger.warning(
                            "  SLOT VALIDATION: missing slots for '%s' (page_type=%s): %s",
                            topic.get("slug", ""),
                            topic.get("page_type", ""),
                            ", ".join(_slot_result.missing_slots),
                        )
                except Exception as _sv_exc:
                    logger.warning("  SLOT VALIDATION: error during validation, skipping: %s", _sv_exc)

            # Build RankMath SEO meta (written via DB after publish, not via REST API)
            _brand = _site_ctx.display_name if _site_ctx else "SweetsWorld"
            seo_title = f"{topic['title']} | {_brand}"
            plain_excerpt = re.sub(r"<[^>]+>", "", excerpt).strip()

            # Contamination guard: abort if content contains another site's domain
            if _site_ctx:
                from sites_registry import assert_no_cross_site_contamination, SitesRegistry as _SR
                assert_no_cross_site_contamination(
                    html_content, _site_ctx.site_id, _site_ctx.base_url, _SR()
                )

            # Snapshot existing WP content before overwriting (soft-fail, non-blocking)
            _take_pre_publish_snapshot(
                wp_client=wp_client,
                slug=topic["slug"],
                project_root=Path(__file__).parent.parent,
                dry_run=getattr(args, "dry_run", False),
            )

            created_post = wp_client.create_post_draft(
                title=topic["title"],
                slug=topic["slug"],
                html=html_content,
                excerpt=excerpt,
                category_id=category_id,
            )

            result_status = "drafted"
            post_link = created_post.get("link") or f"{settings.wp_base_url}/?p={created_post['id']}"
            post_id = created_post.get("id")
            _attach_featured_image_from_products(
                wp_client=wp_client,
                post_id=int(post_id) if post_id is not None else None,
                selected_products=selected_products,
            )
            registry_status = str(registry_record.get("status", "")).strip().lower()
            # When publish_created is requested (auto_publish in site.json OR --publish-created flag),
            # treat "discovered" as approved so new topics don't silently become drafts
            _effective_approved = PUBLISH_APPROVED_STATUSES | {"discovered"} if publish_created else PUBLISH_APPROVED_STATUSES
            can_publish_now = publish_created and registry_status in _effective_approved

            if publish_created and not can_publish_now:
                logger.info("  INFO: Auto-publish requested but page registry status is not approved; keeping draft for manual review")

            wp_result_item: Optional[Dict[str, Any]] = created_post
            if can_publish_now and post_id is not None:
                published_post = wp_client.publish_post(int(post_id))
                post_link = published_post.get("link") or post_link
                wp_result_item = published_post
                result_status = "published"
                logger.info(f"  OK: Published post: {post_link}")
                # Write RankMath meta directly via DB (REST API blocked by plugin permissions)
                wp_client.write_seo_meta_via_db(
                    post_id=int(post_id),
                    keyword=topic.get("primary_keyword", ""),
                    seo_title=seo_title,
                    seo_description=plain_excerpt,
                )
                # 发布成功后立即提交 Google Indexing API，加速索引
                _submit_to_google_indexing(post_link, settings)
                # 预热 LiteSpeed 缓存，确保 Google bot 首次访问拿到缓存页面
                _warm_page_cache(post_link)
                # Ping Google sitemap 确保 sitemap 缓存刷新
                _ping_google_sitemap(settings)
                # 触发社交分发 webhook（非阻塞）
                if DISTRIBUTION_ROUTER_AVAILABLE:
                    try:
                        _pt = topic.get("page_type", "landing_page")
                        _channels = get_channels_for_brief(content_brief, _pt)
                        emit_distribution_event(
                            post_url=post_link,
                            post_id=int(post_id),
                            brief=content_brief,
                            channels=_channels,
                            excerpt=plain_excerpt,
                            title=seo_title,
                            dry_run=getattr(settings, "dry_run", False),
                        )
                    except Exception as _dist_exc:
                        logger.warning(f"  WARN: Distribution event failed (non-blocking): {_dist_exc}")
            else:
                logger.info(f"  OK: Created draft: {post_link}")

            save_registry_record(
                page_registry,
                page_registry_path,
                topic,
                status=result_status,
                link=post_link,
                post_id=int(post_id) if post_id is not None else None,
                wp_item=wp_result_item,
                word_count=len(html_content.split()) if html_content else None,
            )
            record_topic_result(
                state,
                topic,
                status=result_status,
                link=post_link,
                post_id=int(post_id) if post_id is not None else None,
            )
            save_state(state_path, state)
            if _topics_db:
                _topics_db.mark_status(
                    topic.get("slug", ""), result_status,
                    wp_post_id=int(post_id) if post_id is not None else None,
                    wp_post_url=post_link if result_status == "published" else None,
                )
            if _site_ctx:
                from sites_registry import SitesRegistry as _SR2
                _site_ctx.db.upsert_page({
                    "slug":            topic.get("slug", ""),
                    "wp_post_id":      int(post_id) if post_id is not None else None,
                    "url":             post_link,
                    "title":           topic.get("title", ""),
                    "page_type":       topic.get("page_type", ""),
                    "cluster":         topic.get("cluster", ""),
                    "primary_keyword": topic.get("primary_keyword", ""),
                    "status":          result_status,
                    "published_at":    datetime.now().isoformat(timespec="seconds") if result_status == "published" else None,
                })
                _site_ctx.db.log_publish(
                    topic.get("slug", ""), result_status,
                    wp_post_id=int(post_id) if post_id is not None else None,
                    details={"url": post_link, "word_count": len(html_content.split())},
                )
                if result_status == "published":
                    _SR2().record_publish(_site_ctx.site_id, slug=topic.get("slug", ""), wp_post_id=int(post_id) if post_id is not None else None)
            results.append({"title": title, "status": result_status, "link": post_link})
            new_posts_created += 1
        except Exception as exc:
            logger.error(f"  ERROR processing '{title}': {exc}", exc_info=True)
            send_error_alert(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                context=f"topic={topic.get('slug', 'unknown')}",
                exc=exc,
                site_id=getattr(settings, "site_id", "") or getattr(_site_ctx, "site_id", ""),
            )
            save_registry_record(page_registry, page_registry_path, topic, status="error", message=str(exc))
            record_topic_result(state, topic, status="error", message=str(exc))
            save_state(state_path, state)
            results.append({"title": title, "status": "error", "message": str(exc)})

        logger.debug("")

    created_total = sum(1 for row in results if row["status"] in NEW_POST_STATUSES)
    existing_total = sum(1 for row in results if row["status"] == "exists")
    error_total = sum(1 for row in results if row["status"] == "error")

    logger.info("=" * 50)
    logger.info(f"Created or published: {created_total}")
    logger.info(f"Skipped existing: {existing_total}")
    logger.info(f"Errors: {error_total}")
    logger.info("=" * 50)

    if results:
        site_domain = extract_site_domain(settings.wp_base_url)
        message = build_telegram_message(results, mode=run_mode, site_domain=site_domain)
        try:
            logger.info("\nINFO: Sending Telegram notification...")
            send_telegram(settings.telegram_bot_token, settings.telegram_chat_id, message)
        except Exception as exc:
            logger.warning(f"WARN: Telegram notification failed: {exc}")

        # Obsidian vault sync — log publish results
        try:
            import sys as _sys
            _sys.path.insert(0, "/Users/michaelzhao/agents/obsidian-vault/ops")
            from obsidian_sync import log_event as _obs_log
            _obs_log(
                f"SEO {run_mode}: {created_total} published, {existing_total} skipped, {error_total} errors ({site_domain})",
                "sweetsworld-seo",
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
