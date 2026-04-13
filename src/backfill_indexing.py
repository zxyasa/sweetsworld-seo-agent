"""一次性脚本：把 page_registry 中所有 published 页面补提交到 Google Indexing API。

使用场景：
  - 系统上线前已经发布的页面，没有走自动提交流程
  - 需要强制通知 Google re-crawl 已更新的页面

用法：
    python src/backfill_indexing.py
    python src/backfill_indexing.py --dry-run
    python src/backfill_indexing.py --slug white-knight-chocolate-where-to-buy-australia
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_registry(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("records", []) if isinstance(data, dict) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="补提已发布页面到 Google Indexing API")
    parser.add_argument("--dry-run", action="store_true", help="只列出要提交的 URL，不实际提交")
    parser.add_argument("--slug", help="只提交指定 slug")
    parser.add_argument("--registry", default=str(PROJECT_ROOT / "data" / "page_registry.json"))
    args = parser.parse_args()

    # 动态 import，避免在无 google-auth 环境下 import 失败
    try:
        from google_indexing import submit_url
    except ImportError:
        print("ERROR: google-auth 未安装，无法使用 Indexing API", file=sys.stderr)
        print("       pip install google-auth google-auth-httplib2", file=sys.stderr)
        return 1

    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from config import get_settings
        settings = get_settings()
    except Exception as e:
        print(f"ERROR: 无法加载配置: {e}", file=sys.stderr)
        return 1

    creds_file = settings.gsc_credentials_file
    if not creds_file or not Path(creds_file).exists():
        print(f"ERROR: GSC_CREDENTIALS_FILE 未配置或文件不存在: {creds_file}", file=sys.stderr)
        return 1

    records = _load_registry(Path(args.registry))
    published = [
        r for r in records
        if str(r.get("status", "")).lower() == "published"
        and r.get("post_link")
    ]

    if args.slug:
        published = [r for r in published if r.get("slug") == args.slug]

    if not published:
        print("没有找到符合条件的已发布页面。")
        return 0

    print(f"共 {len(published)} 个已发布页面需要提交：\n")

    ok = 0
    failed = 0
    for record in published:
        url = record["post_link"]
        slug = record.get("slug", "?")
        if args.dry_run:
            print(f"  [dry-run] {slug}  →  {url}")
            continue
        result = submit_url(url, creds_file)
        if result.get("status") == "success":
            print(f"  ✓ {slug}  →  {url}")
            ok += 1
        else:
            print(f"  ✗ {slug}  →  {result.get('message')}")
            failed += 1

    if not args.dry_run:
        print(f"\n完成：{ok} 成功，{failed} 失败")
    else:
        print("\n(dry-run 模式，未实际提交)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
