"""Thin orchestration wrapper for the pilot SEO dashboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from ranking_monitor import collect_pilot_report, write_markdown_report
    from site_context import apply_site_context_env, load_site_context
except ImportError:  # pragma: no cover - allows module-style imports
    from src.ranking_monitor import collect_pilot_report, write_markdown_report
    from src.site_context import apply_site_context_env, load_site_context


def generate_pilot_dashboard(
    days: int = 7,
    output_path: str = "reports/seo_dashboard.md",
    slugs: list[str] | None = None,
    registry_path: Path | None = None,
) -> dict:
    report = collect_pilot_report(days=days, slugs=slugs or [], registry_path=registry_path) if registry_path else collect_pilot_report(days=days, slugs=slugs or [])
    write_markdown_report(report, Path(output_path))
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the pilot SEO markdown dashboard.")
    parser.add_argument("--days", type=int, default=7, help="Lookback window for GSC metrics.")
    parser.add_argument("--slug", action="append", default=[], help="Limit dashboard generation to one or more slugs.")
    parser.add_argument("--output", default="reports/seo_dashboard.md", help="Markdown output path.")
    parser.add_argument("--site", default=None, help="Site ID (e.g. sweetsworld, newcastlehub).")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = args.output
    registry_path = None
    if args.site:
        ctx = load_site_context(args.site)
        apply_site_context_env(ctx)
        registry_path = ctx.site_dir / "data" / "page_registry.json"
        if output_path == "reports/seo_dashboard.md":
            output_path = str(ctx.site_dir / "reports" / "seo_dashboard.md")

    report = generate_pilot_dashboard(
        days=max(1, args.days),
        output_path=output_path,
        slugs=args.slug,
        registry_path=registry_path,
    )
    print(json.dumps({"output_path": output_path, "published_count": report["published_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
