from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import get_settings
from wp_client import WPClient


DEFAULT_REGISTRY = {"schema_version": 1, "records": []}
SYNCABLE_STATUSES = {"published", "drafted", "approved", "monitored"}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    return data if isinstance(data, dict) else dict(default)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def infer_registry_status(wp_status: str, existing_status: str) -> str:
    wp_status_key = _clean_text(wp_status).lower()
    existing_key = _clean_text(existing_status).lower()
    if wp_status_key in {"publish", "published"}:
        return "published"
    if wp_status_key in {"draft", "pending", "future", "private"}:
        return "drafted"
    return existing_key or "discovered"


def build_sync_payload(record: Dict[str, Any], wp_item: Dict[str, Any], note: str) -> Dict[str, Any]:
    updated = dict(record)
    wp_status = _clean_text(wp_item.get("status", ""))
    updated["status"] = infer_registry_status(wp_status, _clean_text(record.get("status", "")))
    updated["published_post_id"] = wp_item.get("id") or record.get("published_post_id")
    updated["post_link"] = _clean_text(wp_item.get("link", "")) or record.get("post_link")
    updated["wp_date"] = _clean_text(wp_item.get("date", "")) or record.get("wp_date")
    updated["wp_date_gmt"] = _clean_text(wp_item.get("date_gmt", "")) or record.get("wp_date_gmt")
    updated["wp_modified"] = _clean_text(wp_item.get("modified", "")) or record.get("wp_modified")
    updated["wp_modified_gmt"] = _clean_text(wp_item.get("modified_gmt", "")) or record.get("wp_modified_gmt")
    if updated["status"] == "published":
        updated["published_at"] = updated["wp_date"] or record.get("published_at")
    if note:
        updated["notes"] = note
    return updated


def summarise_changes(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    changes: Dict[str, Dict[str, Any]] = {}
    keys = [
        "status",
        "published_post_id",
        "post_link",
        "published_at",
        "wp_date",
        "wp_date_gmt",
        "wp_modified",
        "wp_modified_gmt",
        "notes",
    ]
    for key in keys:
        if before.get(key) != after.get(key):
            changes[key] = {"before": before.get(key), "after": after.get(key)}
    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill page_registry.json from live WordPress post metadata.")
    parser.add_argument("slugs", nargs="*", help="Specific registry slugs to sync.")
    parser.add_argument("--all-published", action="store_true", help="Sync every registry record currently marked published.")
    parser.add_argument("--all-syncable", action="store_true", help="Sync every registry record in a syncable status.")
    parser.add_argument("--write", action="store_true", help="Persist changes to data/page_registry.json. Default is dry-run.")
    parser.add_argument("--note", default="", help="Optional note stored in registry for updated rows.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.slugs and not args.all_published and not args.all_syncable:
        raise SystemExit("Provide at least one slug, or use --all-published / --all-syncable")

    repo_root = Path(__file__).resolve().parent.parent
    registry_path = repo_root / "data/page_registry.json"
    registry = load_json(registry_path, DEFAULT_REGISTRY)
    records = registry.get("records", [])
    if not isinstance(records, list):
        raise SystemExit(f"Invalid registry records payload: {registry_path}")

    requested_slugs = {_clean_text(slug).lower() for slug in args.slugs if _clean_text(slug)}
    candidates: List[Dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        slug = _clean_text(row.get("slug", "")).lower()
        status = _clean_text(row.get("status", "")).lower()
        if requested_slugs and slug in requested_slugs:
            candidates.append(row)
            continue
        if args.all_syncable and status in SYNCABLE_STATUSES:
            candidates.append(row)
            continue
        if args.all_published and status == "published":
            candidates.append(row)

    if not candidates:
        print(json.dumps({"updated": [], "dry_run": not args.write, "message": "No matching registry rows found."}, indent=2, ensure_ascii=False))
        return 0

    settings = get_settings()
    wp_client = WPClient(
        base_url=settings.wp_base_url,
        username=settings.wp_username,
        app_password=settings.wp_app_password,
    )

    updates: List[Dict[str, Any]] = []
    for record in candidates:
        slug = _clean_text(record.get("slug", ""))
        page_type = _clean_text(record.get("page_type", ""))
        wp_item = wp_client.find_post_by_slug(slug)
        if not wp_item:
            updates.append(
                {
                    "slug": slug,
                    "page_type": page_type,
                    "status": _clean_text(record.get("status", "")),
                    "found": False,
                }
            )
            continue

        updated = build_sync_payload(record, wp_item, _clean_text(args.note))
        changes = summarise_changes(record, updated)
        if args.write and changes:
            updated["updated_at"] = datetime.now().isoformat(timespec="seconds")
            record.update(updated)
        updates.append(
            {
                "slug": slug,
                "page_type": page_type,
                "status": updated.get("status"),
                "found": True,
                "changes": changes,
            }
        )

    if args.write:
        save_json(registry_path, registry)

    print(
        json.dumps(
            {
                "updated": updates,
                "dry_run": not args.write,
                "registry_path": str(registry_path),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
