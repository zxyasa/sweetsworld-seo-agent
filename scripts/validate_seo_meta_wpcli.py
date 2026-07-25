#!/usr/bin/env python3
"""Staging validation for the wp-cli RankMath meta write path.

Exercises the REAL ``WPClient.write_seo_meta_via_wpcli()`` code path against a
DRAFT post, verifies write parity (incl. unicode / quotes / specials), then
restores the original values exactly. Safe: touches only the given draft post
and puts it back. Does NOT change production behaviour — run_mvp still defaults
to the bridge (SEO_META_WRITE_METHOD unset).

    python scripts/validate_seo_meta_wpcli.py [--post-id 72242]
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import dotenv_values  # noqa: E402

META_KEYS = ("rank_math_title", "rank_math_description", "rank_math_focus_keyword")


def load_wpcli_env(site: str = "sweetsworld") -> None:
    path = ROOT / "sites" / site / "wpcli.env"
    if not path.exists():
        sys.exit(f"missing {path}")
    for key, value in dotenv_values(path).items():
        if value and value.strip():
            os.environ[key] = value.strip()


def _ssh_base() -> list[str]:
    return [
        "ssh", "-i", os.path.expanduser(os.environ["WP_SSH_KEY"]),
        "-p", os.environ.get("WP_SSH_PORT", "22"),
        "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
        "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15", "-T",
        f'{os.environ["WP_SSH_USER"]}@{os.environ["WP_SSH_HOST"]}',
    ]


def _cd(wp_dir: str) -> str:
    if wp_dir == "~":
        return "cd ~"
    if wp_dir.startswith("~/"):
        return "cd ~/" + shlex.quote(wp_dir[2:])
    return "cd " + shlex.quote(wp_dir)


def meta_get(post_id: int, key: str) -> str:
    wp_dir = os.environ.get("WP_CLI_DIR", "~/public_html")
    remote = f"{_cd(wp_dir)} && wp post meta get {int(post_id)} {key}"
    result = subprocess.run(_ssh_base() + [remote], capture_output=True, text=True, timeout=60)
    return result.stdout.rstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", type=int, default=72242)
    args = parser.parse_args()
    pid = args.post_id
    load_wpcli_env()

    from wp_client import WPClient

    client = WPClient(
        base_url=os.environ.get("WP_BASE_URL", "https://sweetsworld.com.au"),
        username="validate",
        app_password="validate",
    )

    # 1) snapshot originals
    orig = {key: meta_get(pid, key) for key in META_KEYS}
    print(f"=== ORIGINALS (post {pid}) ===")
    for key in META_KEYS:
        print(f"  {key} = [{orig[key]}]")

    # 2) write distinctive test values THROUGH the real method
    test_title = "WPCLI-VALIDATE ✅ 糖果 | a\"b"
    test_desc = "wpcli validate — 测试 & 100% 'quoted' \"dquoted\""
    test_kw = "wpcli validate kw"
    wrote = client.write_seo_meta_via_wpcli(
        post_id=pid, keyword=test_kw, seo_title=test_title, seo_description=test_desc
    )
    print(f"\nwrite_seo_meta_via_wpcli() returned: {wrote}")

    expect = {
        "rank_math_title": test_title,
        "rank_math_description": test_desc,
        "rank_math_focus_keyword": test_kw,
    }
    after = {key: meta_get(pid, key) for key in META_KEYS}
    print("=== AFTER WRITE ===")
    for key in META_KEYS:
        print(f"  {key} = [{after[key]}]  match={after[key] == expect[key]}")
    write_pass = bool(wrote) and all(after[key] == expect[key] for key in META_KEYS)

    # 3) restore originals via the same method (round-trip realism)
    client.write_seo_meta_via_wpcli(
        post_id=pid,
        keyword=orig["rank_math_focus_keyword"],
        seo_title=orig["rank_math_title"],
        seo_description=orig["rank_math_description"],
    )
    restored = {key: meta_get(pid, key) for key in META_KEYS}
    print("=== AFTER RESTORE ===")
    for key in META_KEYS:
        print(f"  {key} = [{restored[key]}]  restored={restored[key] == orig[key]}")
    restore_pass = all(restored[key] == orig[key] for key in META_KEYS)

    print()
    print(f"WRITE_TEST:   {'PASS' if write_pass else 'FAIL'}")
    print(f"RESTORE_TEST: {'PASS' if restore_pass else 'FAIL'}")
    overall = write_pass and restore_pass
    print(f"OVERALL: {'PASS ✅' if overall else 'FAIL ❌'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
