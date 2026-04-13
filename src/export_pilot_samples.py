from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from content_brief_engine import build_content_brief, save_content_brief
from content_generator import generate_article_html, generate_post_excerpt
from product_selector import load_product_catalog, select_products_for_topic

SKIP_STATUSES = {"published", "blocked", "monitored"}
QA_CHECKLIST = """# Pilot Manual QA Checklist

Use this checklist before any page moves from `drafted` to `approved`.

## Intent
- [ ] The page type matches the keyword intent.
- [ ] `category_page` and `landing_page` intent are not mixed.
- [ ] The H1, excerpt, and CTA all point at the same search task.

## Content Quality
- [ ] The intro is specific to the keyword and not generic filler.
- [ ] The sections answer the query with concrete buying guidance.
- [ ] The FAQ handles realistic user questions, not vague SEO fluff.
- [ ] The page has enough substance to justify indexation.

## Product Fit
- [ ] Every recommended product is relevant to the keyword.
- [ ] No invented products or missing product URLs appear.
- [ ] If no products matched, the page still reads naturally without fake recommendations.

## Internal Links
- [ ] Internal links point to genuinely related pages or collections.
- [ ] Anchor text is specific and varied enough to avoid sitewide repetition.
- [ ] The CTA route makes sense for the page type.

## Safety
- [ ] The page should remain draft-only until manually approved.
- [ ] The keyword does not collide with an existing canonical page intent.
- [ ] The page is worth indexing before any scale-up decision.
"""

DEFAULT_REGISTRY = {"schema_version": 1, "records": []}
HOLD_STATUSES = {"approved", "published", "monitored", "blocked"}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalise_topic_row(row: List[str], line_number: int) -> Dict[str, str] | None:
    cleaned = [cell.strip() for cell in row]
    if not any(cleaned):
        return None

    if len(cleaned) >= 4:
        slug = cleaned[0]
        primary_keyword = cleaned[-2]
        category_hint = cleaned[-1]
        title_parts = cleaned[1:-2] if len(cleaned) > 4 else [cleaned[1]]
        title = ", ".join(part for part in title_parts if part)
    else:
        padded = cleaned + [""] * (4 - len(cleaned))
        slug, title, primary_keyword, category_hint = padded[:4]

    return {
        "slug": slug,
        "title": title,
        "primary_keyword": primary_keyword,
        "category_hint": category_hint,
        "_source_line": str(line_number),
    }


def read_topics(csv_path: Path) -> List[Dict[str, str]]:
    topics: List[Dict[str, str]] = []
    seen_slugs = set()
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for line_number, row in enumerate(reader, start=2):
            topic = _normalise_topic_row(row, line_number)
            if not topic:
                continue
            slug = topic.get("slug", "").strip().lower()
            if slug and slug in seen_slugs:
                continue
            if slug:
                seen_slugs.add(slug)
            topics.append(topic)
    return topics


def validate_topic(topic: Dict[str, str]) -> bool:
    slug = topic.get("slug", "").strip()
    title = topic.get("title", "").strip()
    if not slug or not title:
        return False
    if not topic.get("primary_keyword", "").strip():
        topic["primary_keyword"] = title
    if not topic.get("category_hint", "").strip():
        topic["category_hint"] = "Confectionery"
    return True


def infer_page_type(topic: Dict[str, str]) -> str:
    hint = str(topic.get("category_hint", "")).strip().lower()
    primary_keyword = str(topic.get("primary_keyword", "")).strip().lower()
    title = str(topic.get("title", "")).strip().lower()
    haystack = " ".join(part for part in [hint, primary_keyword, title] if part)

    if "landing" in hint:
        return "landing_page"
    if "category" in hint:
        return "category_page"
    if "guide" in hint:
        return "guide_page"
    if "occasion" in hint:
        return "occasion_page"

    if primary_keyword.startswith("best ") and " for " in primary_keyword:
        return "occasion_page"
    if " guide" in haystack and "where to buy" not in primary_keyword and not primary_keyword.startswith(("buy ", "cheap ", "bulk ")):
        return "guide_page"
    if "where to buy" in primary_keyword or primary_keyword.startswith(("buy ", "cheap ", "bulk ")) or " online " in f" {primary_keyword} ":
        return "landing_page"
    if primary_keyword.startswith(("what ", "how ", "why ", "when ", "which ", "are ", "is ", "can ", "do ", "does ")) or " vs " in haystack:
        return "guide_page"
    if "where to buy" in haystack or " online " in f" {haystack} ":
        return "landing_page"
    return "category_page"


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return dict(default)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def registry_status_map(path: Path) -> Dict[str, str]:
    payload = load_json(path, {"records": []})
    statuses: Dict[str, str] = {}
    for row in payload.get("records", []):
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug", "")).strip().lower()
        page_type = str(row.get("page_type", "")).strip().lower()
        status = str(row.get("status", "")).strip().lower()
        if slug and page_type:
            statuses[f"{slug}|{page_type}"] = status
    return statuses


def find_registry_record(registry: Dict[str, Any], slug: str, page_type: str) -> Optional[Dict[str, Any]]:
    slug_key = slug.strip().lower()
    page_type_key = page_type.strip().lower()
    for row in registry.get("records", []):
        if not isinstance(row, dict):
            continue
        if _clean_text(row.get("slug", "")).lower() == slug_key and _clean_text(row.get("page_type", "")).lower() == page_type_key:
            return row
    return None


def sync_registry_record(
    registry: Dict[str, Any],
    registry_path: Path,
    topic: Dict[str, Any],
    sample_dir: Path,
    brief_id: str,
) -> Dict[str, Any]:
    slug = _clean_text(topic.get("slug", ""))
    page_type = _clean_text(topic.get("page_type", ""))
    record = find_registry_record(registry, slug, page_type)
    now = datetime.now().isoformat(timespec="seconds")

    if not record:
        record = {
            "keyword": _clean_text(topic.get("primary_keyword", "")),
            "slug": slug,
            "page_type": page_type,
            "status": "review_pending",
            "intent": _clean_text(topic.get("intent", "")),
            "template_version": "pilot-v1",
            "product_rule_version": "pilot-v1",
            "brief_id": brief_id,
            "created_at": now,
            "updated_at": now,
            "published_post_id": None,
            "published_at": None,
            "blocking_reason": None,
            "last_error": "",
            "notes": "",
            "sample_dir": str(sample_dir),
        }
        registry.setdefault("records", []).append(record)
    else:
        record["keyword"] = _clean_text(topic.get("primary_keyword", ""))
        record["slug"] = slug
        record["page_type"] = page_type
        record["brief_id"] = brief_id or _clean_text(record.get("brief_id", ""))
        record["sample_dir"] = str(sample_dir)
        record["updated_at"] = now
        if _clean_text(record.get("status", "")).lower() not in HOLD_STATUSES:
            record["status"] = "review_pending"

    save_json(registry_path, registry)
    return record


def export_sample(topic: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    sample_dir = output_dir / topic["slug"]
    sample_dir.mkdir(parents=True, exist_ok=True)

    brief = build_content_brief(topic)
    save_content_brief(sample_dir, brief)

    html = generate_article_html(topic_dict=topic, content_brief=brief)
    excerpt = generate_post_excerpt(topic, content_brief=brief)
    (sample_dir / "page.html").write_text(html, encoding="utf-8")
    (sample_dir / "excerpt.txt").write_text(excerpt + "\n", encoding="utf-8")
    (sample_dir / "topic.json").write_text(json.dumps(topic, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "slug": topic["slug"],
        "title": topic["title"],
        "page_type": topic["page_type"],
        "brief_id": brief["brief_id"],
        "output_dir": str(sample_dir),
        "selected_products": len(topic.get("selected_products", [])),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export draft-only pilot samples for manual QA.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of sample pages to export.")
    parser.add_argument("--output-dir", default="pilot_samples", help="Directory for exported sample pages.")
    parser.add_argument("--topics-csv", default="topics.csv", help="Path to the topic CSV file.")
    parser.add_argument("--force", action="store_true", help="Export topics even if registry status suggests skipping.")
    parser.add_argument("--slug", action="append", default=None, help="Only export the specified slug. Can be passed multiple times.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    topics_csv = repo_root / args.topics_csv
    if not topics_csv.exists():
        raise SystemExit(f"Topics CSV not found: {topics_csv}")

    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manual_qa_checklist.md").write_text(QA_CHECKLIST + "\n", encoding="utf-8")

    topics = read_topics(topics_csv)
    product_catalog = load_product_catalog(repo_root / "data/products.json")
    registry_path = repo_root / "data/page_registry.json"
    registry = load_json(registry_path, DEFAULT_REGISTRY)
    registry_status = registry_status_map(registry_path)

    requested_slugs = {str(slug or "").strip().lower() for slug in (args.slug or []) if str(slug or "").strip()}

    exported: List[Dict[str, Any]] = []
    for topic in topics:
        if len(exported) >= max(args.limit, 1):
            break
        if requested_slugs and topic.get("slug", "").strip().lower() not in requested_slugs:
            continue
        if not validate_topic(topic):
            continue

        topic["page_type"] = infer_page_type(topic)
        status = registry_status.get(f"{topic['slug'].lower()}|{topic['page_type']}", "")
        if not args.force and status in SKIP_STATUSES:
            continue

        topic["selected_products"] = select_products_for_topic(topic, product_catalog)
        exported_sample = export_sample(topic, output_dir)
        sync_registry_record(
            registry,
            registry_path,
            topic,
            output_dir / topic["slug"],
            exported_sample["brief_id"],
        )
        exported.append(exported_sample)

    summary = {
        "count": len(exported),
        "output_dir": str(output_dir),
        "samples": exported,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
