#!/usr/bin/env python3
"""Bulk RankMath SEO-meta backfill over SSH + `wp eval-file` (one WP bootstrap).

Replacement for looping the wp-seo-meta.php bridge. Reads a JSON array of rows,
ships the DATA as a file (never interpolated into a shell), and applies it with a
fixed PHP script via `wp eval-file`. Files land in $HOME (NOT web root) and are
deleted afterwards. Safe: no per-post HTTP, no static token, no web exposure.

Input JSON (list):
    [{"post_id": 123, "title": "...", "description": "...", "keyword": "..."}, ...]
Only the keys present per row are written (title/description/keyword → the three
rank_math_* meta). Connection from env (loads sites/<site>/wpcli.env by default).

    python scripts/backfill_seo_meta_wpcli.py --json rows.json [--site sweetsworld] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from dotenv import dotenv_values  # noqa: E402

# Fixed PHP applier — reads a JSON data file (arg 0) and writes the three
# rank_math_* meta. Content lives in the JSON file, never in this string.
_PHP_APPLIER = r"""<?php
$path = isset($args[0]) ? $args[0] : '';
if (!$path || !file_exists($path)) { WP_CLI::error('data file not found'); }
$rows = json_decode(file_get_contents($path), true);
if (!is_array($rows)) { WP_CLI::error('bad json'); }
$n = 0;
foreach ($rows as $r) {
    $pid = isset($r['post_id']) ? intval($r['post_id']) : 0;
    if (!$pid) { continue; }
    if (array_key_exists('title', $r))       { update_post_meta($pid, 'rank_math_title', (string) $r['title']); }
    if (array_key_exists('description', $r)) { update_post_meta($pid, 'rank_math_description', (string) $r['description']); }
    if (array_key_exists('keyword', $r))     { update_post_meta($pid, 'rank_math_focus_keyword', (string) $r['keyword']); }
    $n++;
}
WP_CLI::success("updated {$n} posts");
"""


def load_wpcli_env(site: str) -> None:
    path = ROOT / "sites" / site / "wpcli.env"
    if not path.exists():
        sys.exit(f"missing {path}")
    for key, value in dotenv_values(path).items():
        if value and value.strip():
            os.environ[key] = value.strip()


def _ssh_target() -> tuple[str, list[str]]:
    key = os.path.expanduser(os.environ["WP_SSH_KEY"])
    user = os.environ["WP_SSH_USER"]
    host = os.environ["WP_SSH_HOST"]
    port = os.environ.get("WP_SSH_PORT", "22")
    common = ["-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
              "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15"]
    ssh = ["ssh", "-i", key, "-p", port, *common, "-T", f"{user}@{host}"]
    scp_prefix = ["scp", "-i", key, "-P", port, *common]
    return f"{user}@{host}", ssh, scp_prefix  # type: ignore[return-value]


def _cd(wp_dir: str) -> str:
    if wp_dir == "~":
        return "cd ~"
    if wp_dir.startswith("~/"):
        return "cd ~/" + shlex.quote(wp_dir[2:])
    return "cd " + shlex.quote(wp_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, type=Path, help="rows JSON file")
    parser.add_argument("--site", default="sweetsworld")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = json.loads(args.json.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        sys.exit("json must be a non-empty list")
    for row in rows:
        if not isinstance(row, dict) or not int(row.get("post_id", 0)):
            sys.exit(f"every row needs a numeric post_id: {row}")

    print(f"{len(rows)} rows to backfill (site={args.site})")
    if args.dry_run:
        for row in rows[:10]:
            fields = [k for k in ("title", "description", "keyword") if k in row]
            print(f"  post {row['post_id']}: would set {', '.join(fields) or '(nothing)'}")
        if len(rows) > 10:
            print(f"  ... +{len(rows) - 10} more")
        print("DRY-RUN: nothing sent. Drop --dry-run to apply.")
        return 0

    load_wpcli_env(args.site)
    _, ssh, scp_prefix = _ssh_target()
    host_spec = f'{os.environ["WP_SSH_USER"]}@{os.environ["WP_SSH_HOST"]}'
    wp_dir = os.environ.get("WP_CLI_DIR", "~/public_html")

    tag = uuid.uuid4().hex[:12]
    local_dir = Path(os.environ.get("TMPDIR", "/tmp"))
    local_json = local_dir / f"_seo_meta_{tag}.json"
    local_php = local_dir / f"_seo_meta_{tag}.php"
    remote_json = f"seo_meta_{tag}.json"   # relative to $HOME
    remote_php = f"seo_meta_{tag}.php"
    local_json.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    local_php.write_text(_PHP_APPLIER, encoding="utf-8")

    try:
        # ship data + applier into $HOME (scp default cwd = home; NOT web root)
        subprocess.run(scp_prefix + [str(local_json), f"{host_spec}:{remote_json}"],
                       check=True, timeout=90, capture_output=True, text=True)
        subprocess.run(scp_prefix + [str(local_php), f"{host_spec}:{remote_php}"],
                       check=True, timeout=90, capture_output=True, text=True)
        # run applier
        remote_cmd = f'{_cd(wp_dir)} && wp eval-file "$HOME/{remote_php}" "$HOME/{remote_json}"'
        result = subprocess.run(ssh + [remote_cmd], capture_output=True, text=True, timeout=300)
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"ERROR rc={result.returncode}: {result.stderr.strip()[:500]}", file=sys.stderr)
            return 1
        return 0
    finally:
        # always clean up remote + local temp files
        subprocess.run(ssh + [f'rm -f "$HOME/{remote_php}" "$HOME/{remote_json}"'],
                       capture_output=True, text=True, timeout=60)
        local_json.unlink(missing_ok=True)
        local_php.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
