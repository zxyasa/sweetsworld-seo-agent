"""CLI bridge for tg_agent → sweetsworld-seo-agent decoupling.

Accepts a single --action argument and optional --params JSON.
Writes a JSON result to stdout. Exit code 0 = success, 1 = error.

Actions:
  discover   Discover SEO opportunities (GSC or topic-based)
  plan       Plan SEO article parameters (3 suggestions)
  generate   Generate and publish an SEO article

Usage:
  python src/seo_cli.py --action discover --params '{"topic_area": "candy"}'
  python src/seo_cli.py --action plan     --params '{"keyword": "are nerds vegan"}'
  python src/seo_cli.py --action generate --params '{"slug": "are-nerds-vegan", ...}'
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SEO agent CLI bridge")
    parser.add_argument("--action", required=True, choices=["discover", "plan", "generate", "suggest"])
    parser.add_argument("--params", default="{}", help="JSON-encoded parameters")
    return parser.parse_args()


def _action_discover(params: dict) -> dict:
    from config import get_settings
    settings = get_settings()

    topic_area = params.get("topic_area", "")

    if topic_area:
        from seo_discovery import discover_from_topic
        suggestions = discover_from_topic(
            topic_area=topic_area,
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
        return {"type": "seo_suggestions", "mode": "topic", "topic_area": topic_area, "suggestions": suggestions}

    if not settings.use_gsc_data or not settings.gsc_property_url:
        return {"error": "GSC not configured; pass topic_area for non-GSC discovery"}

    from seo_discovery import discover_opportunities
    from gsc_client import GSCClient
    gsc = GSCClient(settings.gsc_property_url, settings.gsc_credentials_file)
    data = discover_opportunities(
        gsc_client=gsc,
        openai_api_key=settings.openai_api_key,
        model=settings.openai_model,
        days=int(params.get("days", 90)),
        min_impressions=int(params.get("min_impressions", 50)),
    )
    data["type"] = "seo_suggestions"
    data["mode"] = "gsc"
    return data


def _action_plan(params: dict) -> dict:
    from config import get_settings
    from seo_planner import plan_seo_article
    settings = get_settings()
    keyword = params.get("keyword") or params.get("primary_keyword", "")
    if not keyword:
        return {"error": "keyword is required"}
    suggestions = plan_seo_article(
        topic=keyword,
        openai_api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
    return {"suggestions": suggestions}


def _action_suggest(params: dict) -> dict:
    from config import get_settings
    from seo_planner import plan_seo_article
    from telegram_notify import format_topic_suggestions
    settings = get_settings()
    keyword = params.get("keyword") or params.get("topic", "candy")
    suggestions = plan_seo_article(
        topic=keyword,
        openai_api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
    return {"text": format_topic_suggestions(suggestions), "suggestions": suggestions}


def _action_generate(params: dict) -> dict:
    from autogen_integration import create_seo_article
    slug = params.get("slug", "")
    title = params.get("title", "")
    primary_keyword = params.get("primary_keyword", "")
    category_hint = params.get("category_hint", "")

    if not all([slug, title, primary_keyword]):
        return {"error": "slug, title, and primary_keyword are required"}

    result = create_seo_article(
        slug=slug,
        title=title,
        primary_keyword=primary_keyword,
        category_hint=category_hint,
    )
    return result if isinstance(result, dict) else {"result": str(result)}


def main() -> int:
    args = _parse_args()
    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid --params JSON: {exc}"}))
        return 1

    try:
        if args.action == "discover":
            result = _action_discover(params)
        elif args.action == "plan":
            result = _action_plan(params)
        elif args.action == "generate":
            result = _action_generate(params)
        elif args.action == "suggest":
            result = _action_suggest(params)
        else:
            result = {"error": f"unknown action: {args.action}"}

        print(json.dumps(result, ensure_ascii=False))
        return 0

    except Exception as exc:
        tb = traceback.format_exc()
        print(json.dumps({"error": str(exc), "traceback": tb[-800:]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
