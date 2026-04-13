#!/usr/bin/env python3
"""One-time migration: topics.csv → topics.db

Safe to run multiple times — skips existing slugs.

Usage:
    python src/migrate_topics_csv_to_db.py
    python src/migrate_topics_csv_to_db.py --csv topics.csv --db data/topics.db
    python src/migrate_topics_csv_to_db.py --export-csv data/topics_export.csv  # verify round-trip
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root or src/
sys.path.insert(0, str(Path(__file__).parent))

from topics_db import TopicsDB


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate topics.csv to SQLite topics.db")
    parser.add_argument("--csv", default="topics.csv", help="Input CSV path (default: topics.csv)")
    parser.add_argument("--db", default="data/topics.db", help="Output DB path (default: data/topics.db)")
    parser.add_argument("--export-csv", default=None, help="After migration, export to this CSV for verification")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without writing")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    db_path = Path(args.db)

    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        import csv
        count = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                print(f"  [{row.get('priority','?')}] {row.get('slug','?')} ({row.get('page_type','?')})")
        print(f"\nDry run: would migrate {count} topics from {csv_path} → {db_path}")
        return

    db = TopicsDB(str(db_path))
    result = db.migrate_from_csv(str(csv_path))
    print(f"Migration complete: inserted={result['inserted']}, skipped={result['skipped']}")

    counts = db.count_by_status()
    print(f"DB status breakdown: {counts}")
    print(f"Total pending: {db.count_pending()}")

    if args.export_csv:
        n = db.export_csv(args.export_csv)
        print(f"Exported {n} rows → {args.export_csv}")
        print("Run diff against original CSV to verify round-trip.")


if __name__ == "__main__":
    main()
