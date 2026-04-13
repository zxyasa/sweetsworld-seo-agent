"""One-time script: deduplicate existing topics.csv using semantic near-duplicate detection.

Usage:
    python src/run_topics_dedup.py
    python src/run_topics_dedup.py --csv /path/to/topics.csv --dry-run

Prints a summary of removed rows and writes the cleaned CSV in-place (atomic).
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Copied inline so this script can run standalone without importing the full
# topic_generator module (which may pull in heavy optional deps).
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset(
    {
        "australia", "australian", "where", "to", "buy", "are", "is", "a", "an",
        "the", "in", "and", "or", "of", "for", "guide", "best", "top", "how",
        "what", "which", "vs", "vs.", "review", "reviews", "online",
    }
)


def _normalise(keyword: str) -> str:
    import re
    tokens = re.sub(r"[^\w\s]", "", keyword.lower()).split()
    meaningful = sorted(t for t in tokens if t not in _STOP_WORDS)
    return " ".join(meaningful)


def _is_near_duplicate(kw_a: str, kw_b: str, threshold: float = 0.85) -> bool:
    norm_a = _normalise(kw_a)
    norm_b = _normalise(kw_b)
    if not norm_a or not norm_b:
        return False
    return SequenceMatcher(None, norm_a, norm_b).ratio() >= threshold


# ---------------------------------------------------------------------------


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    os.replace(tmp, path)


def deduplicate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (kept, removed) row lists."""
    kept: list[dict] = []
    removed: list[dict] = []
    seen_slugs: set[str] = set()
    seen_keywords: list[str] = []

    for row in rows:
        slug = str(row.get("slug", "")).strip().lower()
        keyword = str(row.get("primary_keyword", row.get("title", ""))).strip()

        # Exact slug duplicate
        if slug in seen_slugs:
            removed.append({**row, "_reason": "exact slug duplicate"})
            continue

        # Near-duplicate keyword check
        duplicate_of = next(
            (sk for sk in seen_keywords if _is_near_duplicate(keyword, sk)), None
        )
        if duplicate_of:
            removed.append({**row, "_reason": f"near-duplicate of keyword '{duplicate_of}'"})
            continue

        seen_slugs.add(slug)
        seen_keywords.append(keyword)
        kept.append(row)

    return kept, removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicate topics.csv")
    parser.add_argument(
        "--csv",
        default=str(Path(__file__).resolve().parent.parent / "topics.csv"),
        help="Path to topics.csv (default: project root)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without writing")
    parser.add_argument("--threshold", type=float, default=0.85, help="SequenceMatcher threshold (default 0.85)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}", file=sys.stderr)
        return 1

    rows = load_csv(csv_path)
    if not rows:
        print("topics.csv is empty — nothing to do.")
        return 0

    fieldnames = list(rows[0].keys())
    kept, removed = deduplicate(rows)

    print(f"topics.csv: {len(rows)} rows → {len(kept)} kept, {len(removed)} removed")

    if removed:
        print("\nRemoved rows:")
        for r in removed:
            print(f"  - [{r.get('slug')}]  {r.get('title', '')[:60]}")
            print(f"    reason: {r.get('_reason', '')}")

    if not removed:
        print("No duplicates found.")
        return 0

    if args.dry_run:
        print("\n(dry-run) — topics.csv NOT modified.")
        return 0

    save_csv(csv_path, kept, fieldnames)
    print(f"\nSaved cleaned topics.csv ({len(kept)} rows).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
