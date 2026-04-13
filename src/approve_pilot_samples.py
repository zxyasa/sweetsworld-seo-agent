from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_REGISTRY = {"schema_version": 1, "records": []}
ALLOWED_STATUSES = {"approved", "review_pending", "blocked"}


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


def load_topic(sample_dir: Path) -> Dict[str, Any]:
    topic_path = sample_dir / "topic.json"
    if not topic_path.exists():
        raise SystemExit(f"Sample topic not found: {topic_path}")
    try:
        payload = json.loads(topic_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid sample topic JSON: {topic_path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Sample topic JSON must be an object: {topic_path}")
    return payload


def find_registry_record(registry: Dict[str, Any], slug: str, page_type: str) -> Optional[Dict[str, Any]]:
    slug_key = slug.strip().lower()
    page_type_key = page_type.strip().lower()
    for row in registry.get("records", []):
        if not isinstance(row, dict):
            continue
        if _clean_text(row.get("slug", "")).lower() == slug_key and _clean_text(row.get("page_type", "")).lower() == page_type_key:
            return row
    return None


def find_brief_id(sample_dir: Path) -> str:
    matches = sorted(sample_dir.glob("*_brief.json"))
    if not matches:
        return ""
    try:
        payload = json.loads(matches[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    if isinstance(payload, dict):
        return _clean_text(payload.get("brief_id", ""))
    return ""


def ensure_registry_record(registry: Dict[str, Any], topic: Dict[str, Any], sample_dir: Path) -> Dict[str, Any]:
    slug = _clean_text(topic.get("slug", ""))
    page_type = _clean_text(topic.get("page_type", ""))
    existing = find_registry_record(registry, slug, page_type)
    if existing:
        return existing

    now = datetime.now().isoformat(timespec="seconds")
    record = {
        "keyword": _clean_text(topic.get("primary_keyword", "")),
        "slug": slug,
        "page_type": page_type,
        "status": "review_pending",
        "intent": _clean_text(topic.get("intent", "")),
        "template_version": "pilot-v1",
        "product_rule_version": "pilot-v1",
        "brief_id": find_brief_id(sample_dir),
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
    return record


def update_record(record: Dict[str, Any], topic: Dict[str, Any], sample_dir: Path, status: str, note: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    record["keyword"] = _clean_text(topic.get("primary_keyword", ""))
    record["slug"] = _clean_text(topic.get("slug", ""))
    record["page_type"] = _clean_text(topic.get("page_type", ""))
    brief_id = find_brief_id(sample_dir)
    if brief_id:
        record["brief_id"] = brief_id
    record["sample_dir"] = str(sample_dir)
    record["updated_at"] = now
    record["reviewed_at"] = now
    record["status"] = status
    if status == "approved":
        record["approved_at"] = now
        record["blocking_reason"] = None
    elif status == "blocked":
        record["blocking_reason"] = note or record.get("blocking_reason") or "Blocked during pilot QA"
    else:
        record["blocking_reason"] = None

    if note:
        record["notes"] = note


def list_sample_statuses(repo_root: Path, registry: Dict[str, Any], sample_root: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for sample_dir in sorted(path for path in sample_root.iterdir() if path.is_dir()):
        topic = load_topic(sample_dir)
        slug = _clean_text(topic.get("slug", ""))
        page_type = _clean_text(topic.get("page_type", ""))
        record = find_registry_record(registry, slug, page_type)
        rows.append(
            {
                "slug": slug,
                "page_type": page_type,
                "status": _clean_text(record.get("status", "untracked")) if record else "untracked",
                "brief_id": _clean_text(record.get("brief_id", "")) if record else find_brief_id(sample_dir),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Approve or block exported pilot samples.")
    parser.add_argument("slugs", nargs="*", help="Sample slug(s) under pilot_samples/ to update.")
    parser.add_argument("--status", choices=sorted(ALLOWED_STATUSES), default="approved", help="Registry status to apply.")
    parser.add_argument("--note", default="", help="Optional QA note to save into the page registry.")
    parser.add_argument("--sample-dir", default="pilot_samples", help="Directory containing exported pilot samples.")
    parser.add_argument("--list", action="store_true", help="List current sample statuses instead of updating them.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    sample_root = repo_root / args.sample_dir
    registry_path = repo_root / "data/page_registry.json"
    registry = load_json(registry_path, DEFAULT_REGISTRY)

    if args.list:
        rows = list_sample_statuses(repo_root, registry, sample_root)
        print(json.dumps({"samples": rows}, indent=2, ensure_ascii=False))
        return 0

    if args.status == "blocked" and not _clean_text(args.note):
        raise SystemExit("--note is required when --status blocked")
    if not args.slugs:
        raise SystemExit("Provide at least one sample slug or use --list")

    updates: List[Dict[str, str]] = []
    for slug in args.slugs:
        sample_dir = sample_root / slug
        if not sample_dir.exists():
            raise SystemExit(f"Sample directory not found: {sample_dir}")
        topic = load_topic(sample_dir)
        record = ensure_registry_record(registry, topic, sample_dir)
        update_record(record, topic, sample_dir, args.status, _clean_text(args.note))
        updates.append(
            {
                "slug": _clean_text(record.get("slug", "")),
                "page_type": _clean_text(record.get("page_type", "")),
                "status": _clean_text(record.get("status", "")),
                "brief_id": _clean_text(record.get("brief_id", "")),
            }
        )

    save_json(registry_path, registry)
    print(json.dumps({"updated": updates, "registry_path": str(registry_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
