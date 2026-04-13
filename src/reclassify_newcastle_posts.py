from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import requests

from config import get_settings
from wp_client import WPClient


COMMERCIAL_TOKENS = ["where to buy", "where-to-buy", "buy", "bulk", "wholesale", "shop", "shops", "online", "supplier"]
TRENDING_TOKENS = ["valentine", "valentines"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def fetch_posts_by_category(client: WPClient, category_id: int) -> List[Dict[str, Any]]:
    endpoint = f"{client.api_url}/posts"
    response = requests.get(
        endpoint,
        headers=client.headers,
        params={
            "categories": int(category_id),
            "per_page": 100,
            "context": "edit",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def looks_commercial(slug: str, title: str) -> bool:
    haystack = f"{slug} {title}".lower()
    return any(token in haystack for token in COMMERCIAL_TOKENS)


def looks_trending(slug: str, title: str) -> bool:
    haystack = f"{slug} {title}".lower()
    return any(token in haystack for token in TRENDING_TOKENS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reclassify posts currently assigned to the Newcastle category.")
    parser.add_argument("--write", action="store_true", help="Persist category changes to WordPress. Default is dry-run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    client = WPClient(settings.wp_base_url, settings.wp_username, settings.wp_app_password)

    newcastle = client.find_category_by_slug("newcastle")
    if not newcastle:
        raise SystemExit("Could not find the Newcastle category.")
    newcastle_id = int(newcastle["id"])

    guide_cat = client.ensure_category(settings.wp_guide_category_slug, settings.wp_guide_category_name)
    landing_cat = client.ensure_category(settings.wp_landing_category_slug, settings.wp_landing_category_name)
    trending_cat = client.find_category_by_slug("trending")

    posts = fetch_posts_by_category(client, newcastle_id)
    updates: List[Dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()

    for post in posts:
        post_id = int(post.get("id"))
        slug = _clean_text(post.get("slug"))
        title = _clean_text((post.get("title") or {}).get("rendered"))
        categories = [int(cat_id) for cat_id in (post.get("categories") or [])]
        remaining = [cat_id for cat_id in categories if cat_id != newcastle_id]

        if remaining:
            target_categories = remaining
            reason = "remove_newcastle_keep_existing"
        elif looks_trending(slug, title) and trending_cat:
            target_categories = [int(trending_cat["id"])]
            reason = "assign_trending"
        elif looks_commercial(slug, title):
            target_categories = [int(landing_cat["id"])]
            reason = "assign_where_to_buy"
        else:
            target_categories = [int(guide_cat["id"])]
            reason = "assign_candy_guides"

        changed = target_categories != categories
        update_row = {
            "post_id": post_id,
            "slug": slug,
            "title": title,
            "before_categories": categories,
            "after_categories": target_categories,
            "changed": changed,
            "reason": reason,
        }

        if args.write and changed:
            updated = client.update_post_categories(post_id, target_categories)
            update_row["post_link"] = updated.get("link")
            update_row["status"] = updated.get("status")
            update_row["after_categories"] = updated.get("categories") or target_categories

        updates.append(update_row)
        reason_counter[reason] += 1

    print(
        json.dumps(
            {
                "newcastle_category_id": newcastle_id,
                "count": len(updates),
                "dry_run": not args.write,
                "reasons": dict(reason_counter),
                "updates": updates,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
