#!/usr/bin/env python3
"""Generate local JSON/Markdown AIO reports; Telegram is explicit opt-in."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aio_probe import load_basket, load_config
from aio_reporting import build_run_report, format_telegram, render_markdown
from aio_scoreboard import AIOScoreboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an AIO scoreboard report")
    parser.add_argument("--site", default="sweetsworld")
    parser.add_argument("--run-id", default="latest")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--telegram", action="store_true", help="Send the report summary to Telegram")
    args = parser.parse_args(argv)

    site_root = PROJECT_ROOT / "sites" / args.site
    scoreboard = AIOScoreboard(site_root / "data" / "site.db", site_root / "data" / "aio_raw")
    all_runs = scoreboard.runs(args.site, 50)
    if args.run_id == "latest":
        runs = all_runs[:1]
        if not runs:
            print("No AIO probe runs found. Run scripts/aio_probe.py --live first.")
            return 2
        run = runs[0]
    else:
        run = scoreboard.run_status(args.run_id)
        if not run:
            print(f"AIO run not found: {args.run_id}")
            return 2
    basket = load_basket(site_root / "aio_query_basket.json")
    rows = scoreboard.rows("run_id=?", (run["run_id"],))
    current_index = next((i for i, item in enumerate(all_runs) if item["run_id"] == run["run_id"]), -1)
    prior_run = next(
        (
            item for item in all_runs[current_index + 1:]
            if item["status"] in {"completed", "partial"}
            and item["basket_version"] == run["basket_version"]
        ),
        None,
    ) if current_index >= 0 else None
    prior_rows = scoreboard.rows("run_id=?", (prior_run["run_id"],)) if prior_run else None
    report = build_run_report(run, rows, len(basket["prompts"]), prior_run, prior_rows)

    output_dir = args.output_dir or PROJECT_ROOT / "reports" / "aio"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{stamp}_{run['run_id'][:8]}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")

    if args.telegram:
        config = load_config(args.site)
        token = config.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = config.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required for --telegram")
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": format_telegram(report)},
            timeout=30,
        )
        response.raise_for_status()
        print("Telegram summary sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
