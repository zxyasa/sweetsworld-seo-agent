"""Topic generation and topics.csv append helpers for the SEO workflow."""
from __future__ import annotations

import csv
import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from seo_discovery import discover_from_topic, discover_opportunities
from seo_planner import plan_seo_article

logger = logging.getLogger(__name__)


TOPIC_HEADERS = ["slug", "title", "primary_keyword", "category_hint", "page_type", "cluster", "priority"]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _clean_text(text).lower()).strip("-")
    return slug[:80] or "untitled-topic"


def _normalize_topic(raw: Dict[str, Any]) -> Dict[str, str] | None:
    title = _clean_text(raw.get("title", ""))
    primary_keyword = _clean_text(raw.get("primary_keyword", ""))
    category_hint = _clean_text(raw.get("category_hint", "")) or "Confectionery"
    slug = _slugify(_clean_text(raw.get("slug", "")) or title or primary_keyword)

    if not title or not primary_keyword or not slug:
        return None

    return {
        "slug": slug,
        "title": title,
        "primary_keyword": primary_keyword,
        "category_hint": category_hint,
        "page_type": _clean_text(raw.get("page_type", "")) or "landing_page",
        "cluster": _clean_text(raw.get("cluster", "")) or "general",
        "priority": str(raw.get("priority", "3")).strip() or "3",
    }


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_text(title).lower()).strip()


# Common words that carry no SEO signal — stripped before similarity comparison
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "for", "of", "in", "is", "are", "to",
    "where", "buy", "buying", "guide", "best", "australia", "australian",
    "how", "what", "can", "do", "i", "you", "it", "be", "get",
})


def _normalise_keyword(keyword: str) -> str:
    """Normalise a keyword for near-duplicate comparison.

    Steps: lowercase → strip punctuation → remove stop words → sort tokens.
    Sorting makes 'candy sour lollies' and 'sour lollies candy' equivalent.
    """
    tokens = re.split(r"[^a-z0-9]+", keyword.lower())
    meaningful = sorted(t for t in tokens if t and t not in _STOP_WORDS)
    return " ".join(meaningful)


def _is_near_duplicate(kw_a: str, kw_b: str, threshold: float = 0.85) -> bool:
    """Return True if two normalised keywords are semantically close.

    Catches three cases:
    1. High string similarity (SequenceMatcher >= threshold)
    2. One keyword's tokens are a subset of the other's
       (e.g. "twirl chocolate" vs "twirl chocolate bar")
    3. Identical normalised forms
    """
    norm_a = _normalise_keyword(kw_a)
    norm_b = _normalise_keyword(kw_b)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    # Subset check: if one keyword's tokens fully contain the other's
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if tokens_a and tokens_b and (tokens_a <= tokens_b or tokens_b <= tokens_a):
        return True
    return SequenceMatcher(None, norm_a, norm_b).ratio() >= threshold


def _dedupe_topics(candidates: Iterable[Dict[str, Any]], existing_topics: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen_slugs = {str(topic.get("slug", "")).strip().lower() for topic in existing_topics if topic.get("slug")}
    seen_titles = {_title_key(str(topic.get("title", ""))) for topic in existing_topics if topic.get("title")}
    # Keep normalised keywords from existing topics for near-duplicate check
    seen_keywords: List[str] = [
        str(topic.get("primary_keyword", ""))
        for topic in existing_topics
        if topic.get("primary_keyword")
    ]

    unique_topics: List[Dict[str, str]] = []
    for raw in candidates:
        topic = _normalize_topic(raw)
        if not topic:
            continue

        slug = topic["slug"].lower()
        title_key = _title_key(topic["title"])
        if slug in seen_slugs or title_key in seen_titles:
            continue

        # Semantic near-duplicate check against every already-accepted keyword
        candidate_kw = topic["primary_keyword"]
        if any(_is_near_duplicate(candidate_kw, existing_kw) for existing_kw in seen_keywords):
            continue

        seen_slugs.add(slug)
        seen_titles.add(title_key)
        seen_keywords.append(candidate_kw)
        unique_topics.append(topic)

    return unique_topics


def _derive_seeds(explicit_seeds: Sequence[str], existing_topics: Sequence[Dict[str, Any]]) -> List[str]:
    seeds: List[str] = []

    for seed in explicit_seeds:
        cleaned = _clean_text(seed)
        if cleaned:
            seeds.append(cleaned)

    if seeds:
        return list(dict.fromkeys(seeds))

    for topic in existing_topics:
        for key in ("category_hint", "primary_keyword"):
            cleaned = _clean_text(topic.get(key, ""))
            if cleaned:
                seeds.append(cleaned)
            if len(seeds) >= 5:
                break
        if len(seeds) >= 5:
            break

    if not seeds:
        seeds = ["candy"]

    return list(dict.fromkeys(seeds))


def generate_topic_candidates(
    source: str,
    seed_topics: Sequence[str],
    existing_topics: Sequence[Dict[str, Any]],
    openai_api_key: str,
    openai_model: str,
    desired_count: int,
    gsc_client: Any = None,
) -> List[Dict[str, str]]:
    normalized_source = (source or "auto").strip().lower()
    if normalized_source not in {"auto", "seed", "gsc"}:
        normalized_source = "auto"

    desired_count = max(int(desired_count), 1)
    seeds = _derive_seeds(seed_topics, existing_topics)
    candidates: List[Dict[str, Any]] = []

    if normalized_source in {"auto", "gsc"} and gsc_client is not None:
        discovery = discover_opportunities(
            gsc_client=gsc_client,
            openai_api_key=openai_api_key,
            model=openai_model,
        )
        candidates.extend(discovery.get("suggestions", []))

    if normalized_source in {"auto", "seed"}:
        for seed in seeds:
            candidates.extend(discover_from_topic(seed, openai_api_key=openai_api_key, model=openai_model))
            candidates.extend(plan_seo_article(seed, openai_api_key=openai_api_key, model=openai_model))
            if len(_dedupe_topics(candidates, existing_topics)) >= desired_count:
                break

    return _dedupe_topics(candidates, existing_topics)[:desired_count]


def append_topics_to_csv(csv_path: Path, topics: Sequence[Dict[str, str]]) -> int:
    normalized_topics = [_normalize_topic(topic) for topic in topics]
    rows = [topic for topic in normalized_topics if topic]
    if not rows:
        return 0

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    with open(csv_path, "a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TOPIC_HEADERS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in TOPIC_HEADERS})

    return len(rows)


def replenish_from_gaps(
    csv_path: Path,
    existing_topics: Sequence[Dict[str, Any]],
    graph_db_path: Optional[str] = None,
    registry_path: Optional[str] = None,
    max_gap_topics: int = 10,
    site_id: str = "sweetsworld",
) -> Dict[str, Any]:
    """Seed new topics from entity graph gaps.

    Uses GapFinder to identify content gaps (missing page types, uncovered occasions,
    clusters without hubs) and converts them into topic candidates that are appended
    to topics.csv if they don't already exist.

    Safe to call even if growth-graph is not installed — returns empty result.
    """
    try:
        import sys
        from pathlib import Path as _Path
        growth_graph_src = str(_Path(__file__).parent.parent.parent.parent / "apps" / "growth-graph" / "src")
        if growth_graph_src not in sys.path:
            sys.path.insert(0, growth_graph_src)
        from growth_graph.entity_graph import EntityGraph
        from growth_graph.gap_finder import GapFinder
        from growth_graph.site_registry import load_registry
    except ImportError:
        logger.debug("growth-graph not available — skipping gap-based replenishment")
        return {"added": [], "reason": "growth_graph_not_available", "source": "gaps"}

    try:
        # Resolve graph DB path
        if graph_db_path is None:
            registry = load_registry(registry_path)
            profile = registry.get(site_id)
            graph_db_path = profile.growth_graph_db if profile else None

        if not graph_db_path or not Path(graph_db_path).exists():
            return {"added": [], "reason": "graph_db_not_found", "source": "gaps"}

        graph = EntityGraph(graph_db_path)
        finder = GapFinder(graph)
        report = finder.full_gap_report()

        # Convert gap opportunities into topic candidates
        candidates: List[Dict[str, Any]] = []
        for gap_list in report.values():
            for gap in gap_list:
                if not hasattr(gap, "suggested_slug") or not gap.suggested_slug:
                    continue
                candidates.append({
                    "slug": gap.suggested_slug,
                    "title": gap.entity_name + (f" — {gap.suggested_page_type.replace('_', ' ').title()}" if gap.suggested_page_type else ""),
                    "primary_keyword": gap.suggested_slug.replace("-", " "),
                    "category_hint": "Confectionery",
                    "page_type": gap.suggested_page_type or "landing_page",
                    "cluster": gap.suggested_cluster or "general",
                    "priority": "3",
                })
                if len(candidates) >= max_gap_topics:
                    break
            if len(candidates) >= max_gap_topics:
                break

        unique = _dedupe_topics(candidates, existing_topics)
        added_count = append_topics_to_csv(csv_path, unique)
        logger.info(f"Gap replenishment: {len(candidates)} gap candidates → {added_count} new topics added")
        return {"added": unique[:added_count], "reason": "ok", "source": "gaps"}

    except Exception as exc:
        logger.warning(f"Gap-based replenishment failed: {exc}")
        return {"added": [], "reason": str(exc), "source": "gaps"}


def replenish_topics_csv(
    csv_path: Path,
    existing_topics: Sequence[Dict[str, Any]],
    pending_topics: Sequence[Dict[str, Any]],
    target_pending: int,
    source: str,
    seed_topics: Sequence[str],
    openai_api_key: str,
    openai_model: str,
    gsc_client: Any = None,
    topics_db: Any = None,
) -> Dict[str, Any]:
    desired_pending = max(int(target_pending), 1)
    deficit = max(desired_pending - len(pending_topics), 0)
    if deficit <= 0:
        return {
            "requested": 0,
            "added": [],
            "source": source,
            "reason": "pending queue already meets target",
        }

    generated_topics = generate_topic_candidates(
        source=source,
        seed_topics=seed_topics,
        existing_topics=existing_topics,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        desired_count=deficit,
        gsc_client=gsc_client,
    )

    added_count = append_topics_to_csv(csv_path, generated_topics)
    # Also write to topics.db if available
    if topics_db is not None and added_count:
        try:
            topics_db.add_topics_bulk(generated_topics[:added_count], source="auto_generated")
        except Exception as exc:
            logger.warning(f"Failed to sync generated topics to topics.db: {exc}")
    return {
        "requested": deficit,
        "added": generated_topics[:added_count],
        "source": source,
        "reason": "ok" if added_count else "no unique suggestions generated",
    }
