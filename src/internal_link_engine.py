"""Build a lightweight internal link graph from approved or published SEO briefs."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "data" / "page_registry.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "internal_links.json"


def _load_registry_records(registry_path: Path) -> List[Dict]:
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("page_registry.json records must be a list")
    return records


def _iter_target_records(
    records: Iterable[Dict],
    statuses: Optional[set[str]] = None,
    slugs: Optional[set[str]] = None,
) -> Iterable[Dict]:
    for record in records:
        slug = str(record.get("slug") or "").strip()
        status = str(record.get("status") or "").strip().lower()
        if not slug:
            continue
        if statuses and status not in statuses:
            continue
        if slugs and slug not in slugs:
            continue
        yield record


def _resolve_brief_path(record: Dict) -> Optional[Path]:
    sample_dir = str(record.get("sample_dir") or "").strip()
    slug = str(record.get("slug") or "").strip()
    if not sample_dir or not slug:
        return None

    candidate = Path(sample_dir) / f"{slug}_brief.json"
    if candidate.exists():
        return candidate
    return None


def _load_brief(record: Dict) -> Dict:
    brief_path = _resolve_brief_path(record)
    if not brief_path or not brief_path.exists():
        return {}
    return json.loads(brief_path.read_text(encoding="utf-8"))


def build_backlink_suggestions(items: List[Dict]) -> List[Dict]:
    """Find published/approved pages that are linked TO but don't link back.

    For each page A that links to page B's canonical URL, check whether B
    also contains a link pointing to A. If not, suggest adding one.

    Only examines links between pages in our own pilot graph (not product /
    collection links to external WooCommerce URLs).

    Returns a list of dicts: {from_slug, to_slug, to_url, suggested_anchor}.
    """
    # Build slug → canonical URL and slug → set of outbound URLs
    slug_to_url: Dict[str, str] = {}
    slug_to_outbound: Dict[str, set] = {}

    for item in items:
        slug = str(item.get("slug") or "").strip()
        post_link = str(item.get("post_link") or "").strip().rstrip("/")
        if slug and post_link:
            slug_to_url[slug] = post_link

        outbound = {
            str(link.get("url") or "").strip().rstrip("/")
            for link in (item.get("internal_links") or [])
            if link.get("url")
        }
        if slug:
            slug_to_outbound[slug] = outbound

    # For each page A whose canonical URL appears in B's outbound links,
    # check whether A's outbound links also contain B's canonical URL.
    suggestions: List[Dict] = []
    slugs = list(slug_to_url.keys())

    for slug_a in slugs:
        url_a = slug_to_url[slug_a]
        keyword_a = ""
        for item in items:
            if item.get("slug") == slug_a:
                keyword_a = str(item.get("keyword") or slug_a.replace("-", " "))
                break

        for slug_b in slugs:
            if slug_a == slug_b:
                continue
            url_b = slug_to_url.get(slug_b, "")
            outbound_b = slug_to_outbound.get(slug_b, set())

            # B links to A — does A link back to B?
            if url_a in outbound_b:
                outbound_a = slug_to_outbound.get(slug_a, set())
                if url_b not in outbound_a:
                    suggestions.append({
                        "from_slug": slug_a,
                        "to_slug": slug_b,
                        "to_url": url_b,
                        "suggested_anchor": keyword_a,
                    })

    return suggestions


def build_internal_link_graph(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    output_path: Optional[Path] = DEFAULT_OUTPUT_PATH,
    statuses: Optional[set[str]] = None,
    slugs: Optional[set[str]] = None,
) -> Dict:
    records = _load_registry_records(registry_path)
    items: List[Dict] = []
    anchor_counter: Counter[str] = Counter()
    link_kind_counter: Counter[str] = Counter()

    for record in _iter_target_records(records, statuses=statuses, slugs=slugs):
        brief = _load_brief(record)
        internal_links = brief.get("internal_links") or []
        if not isinstance(internal_links, list):
            internal_links = []

        normalized_links = []
        for link in internal_links:
            if not isinstance(link, dict):
                continue
            url = str(link.get("url") or "").strip()
            label = str(link.get("label") or "").strip()
            anchor_text = str(link.get("anchor_text") or "").strip()
            link_kind = str(link.get("link_kind") or "unknown").strip().lower()
            if not url:
                continue
            normalized_links.append(
                {
                    "url": url,
                    "label": label,
                    "anchor_text": anchor_text,
                    "link_kind": link_kind,
                }
            )
            if anchor_text:
                anchor_counter[anchor_text] += 1
            link_kind_counter[link_kind] += 1

        items.append(
            {
                "slug": record.get("slug"),
                "keyword": record.get("keyword"),
                "status": record.get("status"),
                "page_type": record.get("page_type"),
                "post_link": record.get("post_link"),
                "internal_links": normalized_links,
            }
        )

    missing_backlinks = build_backlink_suggestions(items)

    payload = {
        "schema_version": 1,
        "description": "Internal links exported from pilot SEO content briefs.",
        "record_count": len(items),
        "generated_from_statuses": sorted(statuses) if statuses else [],
        "slugs": sorted(slugs) if slugs else [],
        "summary": {
            "anchors": dict(anchor_counter),
            "link_kinds": dict(link_kind_counter),
            "missing_backlink_count": len(missing_backlinks),
        },
        "missing_backlinks": missing_backlinks,
        "records": items,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, output_path)

    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a lightweight internal link graph from pilot briefs.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH), help="Path to page_registry.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path to write internal_links.json")
    parser.add_argument(
        "--status",
        action="append",
        default=[],
        help="Filter by page registry status. Repeatable. Defaults to approved + published.",
    )
    parser.add_argument(
        "--slug",
        action="append",
        default=[],
        help="Filter to one or more specific slugs.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    statuses = {item.strip().lower() for item in args.status if item.strip()}
    if not statuses:
        statuses = {"approved", "published"}
    slugs = {item.strip() for item in args.slug if item.strip()} or None

    payload = build_internal_link_graph(
        registry_path=Path(args.registry),
        output_path=Path(args.output),
        statuses=statuses,
        slugs=slugs,
    )
    print(json.dumps({"record_count": payload["record_count"], "output_path": args.output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
