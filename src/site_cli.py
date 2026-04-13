"""site_cli.py — multi-site management CLI.

Commands:
  status                     Show all registered sites
  register  --site <id>      Register / re-sync a site into sites.db
  import-topics --site <id>  Import topics.csv → topics table (idempotent)
  migrate   --site <id>      Migrate page_registry.json → pages table (one-time)
  migrate-aio --site <id>    Migrate aio_observations.db → site.db (one-time)
  topics    --site <id>      List topics with optional --status filter
  jobs      --site <id>      List recent job_runs

Usage:
    python src/site_cli.py status
    python src/site_cli.py import-topics --site sweetsworld
    python src/site_cli.py migrate --site sweetsworld
    python src/site_cli.py topics --site sweetsworld --status pending --limit 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python src/site_cli.py` from project root
sys.path.insert(0, str(Path(__file__).parent))


def _require_site(args: argparse.Namespace) -> "SiteContext":  # type: ignore[name-defined]
    from site_context import load_site_context
    if not args.site:
        print("ERROR: --site <site_id> is required for this command.", file=sys.stderr)
        sys.exit(1)
    return load_site_context(args.site)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status(_args: argparse.Namespace) -> None:
    from sites_registry import SitesRegistry, sync_from_disk
    sync_from_disk()
    reg = SitesRegistry()
    print(reg.status_table())


def cmd_register(args: argparse.Namespace) -> None:
    ctx = _require_site(args)
    from sites_registry import SitesRegistry
    reg = SitesRegistry()
    inserted = reg.register_from_context(ctx)
    print(f"{'Registered' if inserted else 'Already registered'}: {ctx.site_id} ({ctx.base_url})")


def cmd_import_topics(args: argparse.Namespace) -> None:
    ctx = _require_site(args)
    from topics_db import TopicsDB

    # Topics for each site live in sites/<site_id>/data/topics.db (future home).
    # The source CSV is sites/<site_id>/topics.csv if it exists,
    # otherwise fall back to the project-root topics.csv.
    site_csv = ctx.site_dir / "topics.csv"
    root_csv = Path(__file__).parent.parent / "topics.csv"
    csv_path = site_csv if site_csv.exists() else root_csv

    if not csv_path.exists():
        print(f"ERROR: topics.csv not found at {site_csv} or {root_csv}", file=sys.stderr)
        sys.exit(1)

    db_path = str(ctx.site_dir / "data" / "topics.db")
    db = TopicsDB(db_path)
    result = db.migrate_from_csv(str(csv_path))

    print(f"[{ctx.site_id}] import-topics from {csv_path.name}")
    print(f"  Inserted: {result['inserted']}")
    print(f"  Skipped:  {result.get('skipped', 0)}  (already in DB)")
    print(f"  DB path:  {db_path}")


def cmd_migrate(args: argparse.Namespace) -> None:
    ctx = _require_site(args)

    # page_registry.json — prefer sites/<site_id>/page_registry.json,
    # fall back to data/page_registry.json at project root.
    site_reg = ctx.site_dir / "page_registry.json"
    root_reg = Path(__file__).parent.parent / "data" / "page_registry.json"
    reg_path = site_reg if site_reg.exists() else root_reg

    if not reg_path.exists():
        print(f"ERROR: page_registry.json not found at {site_reg} or {root_reg}", file=sys.stderr)
        sys.exit(1)

    n = ctx.db.migrate_page_registry(reg_path)
    stats = ctx.db.count_by_status()
    print(f"[{ctx.site_id}] migrate page_registry from {reg_path.name}")
    print(f"  Migrated: {n} records")
    print(f"  Status breakdown: {stats}")
    print(f"  DB path: {ctx.db._path}")


def cmd_migrate_aio(args: argparse.Namespace) -> None:
    ctx = _require_site(args)

    # aio_observations.db — prefer sites/<site_id>/data/aio_observations.db,
    # fall back to data/aio_observations.db at project root.
    site_aio = ctx.site_dir / "data" / "aio_observations.db"
    root_aio = Path(__file__).parent.parent / "data" / "aio_observations.db"
    aio_path = site_aio if site_aio.exists() else root_aio

    n = ctx.db.migrate_aio_from_db(aio_path)
    rates = ctx.db.get_aio_citation_rate()
    print(f"[{ctx.site_id}] migrate AIO observations from {aio_path.name}")
    print(f"  Migrated: {n} rows")
    print(f"  Engines:  {list(rates.keys())}")


def cmd_topics(args: argparse.Namespace) -> None:
    ctx = _require_site(args)
    from topics_db import TopicsDB

    db_path = str(ctx.site_dir / "data" / "topics.db")
    db = TopicsDB(db_path)

    status_filter = args.status or None
    limit = args.limit or 20

    if status_filter == "pending":
        rows = db.get_pending_queue(limit=limit)
    elif status_filter:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows_raw = conn.execute(
            "SELECT * FROM topics WHERE status=? ORDER BY priority, id LIMIT ?",
            (status_filter, limit),
        ).fetchall()
        conn.close()
        rows = [dict(r) for r in rows_raw]
    else:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows_raw = conn.execute(
            "SELECT * FROM topics ORDER BY priority, id LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        rows = [dict(r) for r in rows_raw]

    counts = db.count_by_status()
    print(f"[{ctx.site_id}] topics  filter={status_filter or 'all'}  showing {len(rows)}/{sum(counts.values())}")
    print(f"  Counts: {counts}")
    print()
    for r in rows:
        print(f"  [{r['status']:15}] {r['slug']:45} {r.get('page_type',''):20} pri={r.get('priority','')}")


def cmd_jobs(args: argparse.Namespace) -> None:
    ctx = _require_site(args)
    jobs = ctx.db.list_jobs(limit=args.limit or 10)
    print(f"[{ctx.site_id}] recent job_runs ({len(jobs)})")
    print(f"  {'ID':>4} {'JOB':30} {'STATUS':10} {'PROCESSED':>9} {'FAILED':>6} CHECKPOINT")
    for j in jobs:
        print(
            f"  {j['id']:>4} {j['job_name']:30} {j['status']:10} "
            f"{j['processed_items']:>9} {j['failed_items']:>6} "
            f"{j.get('checkpoint_slug') or '—'}"
        )


def cmd_pages(args: argparse.Namespace) -> None:
    ctx = _require_site(args)
    stats = ctx.db.count_by_status()
    limit = args.limit or 20
    pages = ctx.db.get_published_pages(limit=limit)
    print(f"[{ctx.site_id}] pages  status breakdown: {stats}")
    print()
    for p in pages:
        print(f"  [{p['status']:12}] {p['slug']:45} wp_id={p.get('wp_post_id') or '—'}")


# ── Argument parsing ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site_cli",
        description="Multi-site SEO agent management CLI",
    )
    parser.add_argument("--site", help="Site ID (e.g. sweetsworld, newcastlehub)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show all registered sites")
    sub.add_parser("register", help="Register/re-sync a site into sites.db")

    sub.add_parser("import-topics", help="Import topics.csv into topics.db (idempotent)")

    sub.add_parser("migrate", help="Migrate page_registry.json → pages table (one-time)")
    sub.add_parser("migrate-aio", help="Migrate aio_observations.db → site.db (one-time)")

    p_topics = sub.add_parser("topics", help="List topics")
    p_topics.add_argument("--status", help="Filter by status (pending/published/etc)")
    p_topics.add_argument("--limit", type=int, default=20)

    p_jobs = sub.add_parser("jobs", help="List recent job_runs")
    p_jobs.add_argument("--limit", type=int, default=10)

    p_pages = sub.add_parser("pages", help="List pages from site.db")
    p_pages.add_argument("--limit", type=int, default=20)

    return parser


_COMMANDS = {
    "status":        cmd_status,
    "register":      cmd_register,
    "import-topics": cmd_import_topics,
    "migrate":       cmd_migrate,
    "migrate-aio":   cmd_migrate_aio,
    "topics":        cmd_topics,
    "jobs":          cmd_jobs,
    "pages":         cmd_pages,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
