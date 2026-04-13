#!/usr/bin/env python3
"""Append a structured entry to CHANGELOG.md."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a change record to CHANGELOG.md")
    parser.add_argument("--type", required=True, help="Change type, e.g. code, config, content, manual, infra")
    parser.add_argument("--scope", required=True, help="Short scope label, e.g. Rank Math sitemap")
    parser.add_argument("--summary", required=True, help="One-line summary of the change")
    parser.add_argument("--details", default="", help="What changed")
    parser.add_argument("--verification", default="", help="How the change was verified")
    parser.add_argument("--actor", default="codex", help="Who made or coordinated the change")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_CHANGELOG_PATH),
        help="Path to the changelog file",
    )
    return parser


def _ensure_file(path: Path) -> None:
    if path.exists():
        return
    path.write_text(
        "# Change Log\n\n"
        "All code, config, content, and manual WordPress operations that affect this project should be recorded here.\n\n"
        "Entries are appended in chronological order.\n",
        encoding="utf-8",
    )


def _render_entry(args: argparse.Namespace) -> str:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "",
        f"## {timestamp} | {args.type.strip()} | {args.scope.strip()}",
        f"- Actor: {args.actor.strip()}",
        f"- Summary: {args.summary.strip()}",
    ]
    if args.details.strip():
        lines.append(f"- Details: {args.details.strip()}")
    if args.verification.strip():
        lines.append(f"- Verification: {args.verification.strip()}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    changelog_path = Path(args.path).expanduser().resolve()
    _ensure_file(changelog_path)
    with changelog_path.open("a", encoding="utf-8") as fh:
        fh.write(_render_entry(args))
    print(f"Appended change record to {changelog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
