#!/usr/bin/env python3
"""SW Blog Hero Image Generator — research-backed Jimeng T2I.

Workflow per post:
  1. Fetch post title + first 800 chars content (WP REST)
  2. Claude Sonnet + web_search tool researches AU context for the topic
     (avoids US-Easter-winter / wrong brand / wrong cultural cue mistakes)
  3. Claude synthesizes a Jimeng T2I prompt — AU-correct visual cues, no text,
     no faces, no logos, 1:1 photographic editorial
  4. Jimeng T2I generates 1024×1024 PNG
  5. Upload to WP media library → set featured_media on post

CLI:
  --post-id N           single post
  --recent N            last N posts with featured_media=0
  --dry-run             skip Jimeng + WP upload, just print prompt
  --json-out path

Cost: ~$0.07/post Jimeng + ~$0.04 Claude+web_search = ~$0.11/post.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SEO_AGENT = REPO_ROOT / "agents/sweetsworld-seo-agent"
VOLC_AGENT = REPO_ROOT / "agents/sweetsworld-volcengine-agent"

sys.path.insert(0, str(SEO_AGENT / "src"))
sys.path.insert(0, str(VOLC_AGENT))         # for `from layouts._kit import ...`
sys.path.insert(0, str(VOLC_AGENT / "src_py"))

import requests
from dotenv import dotenv_values
from requests.auth import HTTPBasicAuth


def load_creds() -> dict[str, str]:
    seo_env = {**dotenv_values(SEO_AGENT / ".env"),
               **dotenv_values(SEO_AGENT / "sites/sweetsworld/.env")}
    root_env = dotenv_values(REPO_ROOT / ".env")
    return {
        "WP_BASE_URL": seo_env.get("WP_BASE_URL"),
        "WP_USERNAME": seo_env.get("WP_USERNAME"),
        "WP_APP_PASSWORD": seo_env.get("WP_APP_PASSWORD"),
        "ANTHROPIC_API_KEY": root_env.get("ANTHROPIC_API_KEY") or seo_env.get("ANTHROPIC_API_KEY"),
    }


def fetch_post(creds: dict, post_id: int) -> dict:
    base = creds["WP_BASE_URL"].rstrip("/")
    auth = HTTPBasicAuth(creds["WP_USERNAME"], creds["WP_APP_PASSWORD"])
    r = requests.get(f"{base}/wp-json/wp/v2/posts/{post_id}?context=edit",
                      auth=auth, timeout=15)
    r.raise_for_status()
    p = r.json()
    title = p.get("title", {}).get("rendered", "")
    content_raw = p.get("content", {}).get("raw", "")
    # Strip HTML tags for synthesis context
    text = re.sub(r"<[^>]+>", " ", content_raw)
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "id": post_id,
        "title": title,
        "content_excerpt": text[:800],
        "featured_media": p.get("featured_media", 0),
    }


def research_and_synthesize_prompt(creds: dict, title: str, content_excerpt: str) -> dict:
    """Use Claude with web_search to research AU context + generate Jimeng prompt."""
    import anthropic
    client = anthropic.Anthropic(api_key=creds["ANTHROPIC_API_KEY"])

    system = """You are a hero-image-prompt writer for an Australian candy e-commerce blog
(SweetsWorld, sweetsworld.com.au, run under "Darrell Lea / Kards & Kandy" Newcastle NSW
umbrella brand).

Task: research the AU context for a blog topic, then write a Jimeng T2I prompt that
produces an on-brand hero image.

Visual rules (HARD):
- 1:1 square, photographic editorial style (think magazine food photography)
- NO text or letters in image (Jimeng can't render Latin reliably)
- NO faces, NO people (identity drift risk)
- NO logos, NO brand marks
- NO American visual cliches (no eagles, no US flag colors when AU subject; AU Easter is autumn not winter)
- Match AU season/climate when relevant (e.g. Christmas = beach/summer in AU; Easter = autumn April)
- Subject = candy/chocolate/sweets, real ingredients, natural light
- Avoid known-wrong: don't depict snow on Easter, don't use winter pumpkin spice on AU Mother's Day (May)

Output format: JSON {
  "research_findings": ["3-5 AU-context bullets you discovered or know"],
  "jimeng_prompt": "<200-300 char single-paragraph Jimeng prompt>"
}"""

    user = f"""Topic to write a hero image prompt for:

Title: {title}

Content excerpt:
{content_excerpt}

Use web_search to verify any AU-specific facts (seasons, brands, traditions, dates).
Then return the JSON described."""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        messages=[{"role": "user", "content": user}],
    )
    # Extract text from response
    text_blocks = [b.text for b in resp.content if hasattr(b, "text")]
    full_text = "\n".join(text_blocks)
    # Find JSON
    m = re.search(r'\{[^{}]*"research_findings"[^{}]*"jimeng_prompt".*?\}', full_text, re.DOTALL)
    if not m:
        # Fallback: try entire text
        try:
            return json.loads(full_text)
        except Exception:
            return {"research_findings": ["(parse failed)"], "jimeng_prompt": full_text[:300]}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"research_findings": [], "jimeng_prompt": m.group(0)}


def jimeng_t2i(prompt: str) -> Path:
    """Call existing volcengine Jimeng T2I (in layouts/_kit.py), return local PNG path."""
    from layouts._kit import jimeng_text_to_image
    img = jimeng_text_to_image(prompt, 1024, 1024)
    if img is None:
        raise RuntimeError("Jimeng T2I returned None")
    out_dir = VOLC_AGENT / "renders" / "blog_hero"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"blog_hero_{int(time.time())}.png"
    img.save(path, "PNG", optimize=True)
    return path


def upload_to_wp(creds: dict, local_path: Path, title: str) -> int | None:
    base = creds["WP_BASE_URL"].rstrip("/")
    auth = HTTPBasicAuth(creds["WP_USERNAME"], creds["WP_APP_PASSWORD"])
    with local_path.open("rb") as f:
        r = requests.post(
            f"{base}/wp-json/wp/v2/media",
            headers={
                "Content-Type": "image/png",
                "Content-Disposition": f'attachment; filename="{local_path.name}"',
            },
            data=f,
            auth=auth,
            timeout=120,
        )
    if r.status_code not in (200, 201):
        print(f"WP upload failed: HTTP {r.status_code} {r.text[:300]}", file=sys.stderr)
        return None
    return r.json().get("id")


def set_featured(creds: dict, post_id: int, media_id: int) -> bool:
    base = creds["WP_BASE_URL"].rstrip("/")
    auth = HTTPBasicAuth(creds["WP_USERNAME"], creds["WP_APP_PASSWORD"])
    r = requests.post(f"{base}/wp-json/wp/v2/posts/{post_id}",
                       json={"featured_media": media_id},
                       auth=auth, timeout=20)
    return r.status_code in (200, 201)


def process_one(creds: dict, post_id: int, dry_run: bool) -> dict:
    post = fetch_post(creds, post_id)
    research = research_and_synthesize_prompt(creds, post["title"], post["content_excerpt"])
    prompt = research.get("jimeng_prompt", "")
    findings = research.get("research_findings", [])

    result = {
        "post_id": post_id,
        "title": post["title"][:60],
        "research": findings,
        "prompt": prompt,
    }

    if dry_run:
        result["status"] = "dry_run"
        return result

    img_path = jimeng_t2i(prompt)
    result["image_path"] = str(img_path)
    result["bytes"] = img_path.stat().st_size

    media_id = upload_to_wp(creds, img_path, post["title"])
    if not media_id:
        result["status"] = "wp_upload_failed"
        return result
    result["media_id"] = media_id

    if set_featured(creds, post_id, media_id):
        result["status"] = "ok"
    else:
        result["status"] = "set_featured_failed"
    return result


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--post-id", type=int)
    g.add_argument("--recent", type=int, help="Process last N posts with featured_media=0 OR matching --force-redo")
    p.add_argument("--force-redo", action="store_true", help="With --recent, process posts regardless of featured_media (re-do hero)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json-out")
    p.add_argument("--limit", type=int, default=10)
    args = p.parse_args()

    creds = load_creds()
    if not creds.get("ANTHROPIC_API_KEY"):
        raise SystemExit("FAIL: ANTHROPIC_API_KEY missing")

    if args.post_id:
        out = process_one(creds, args.post_id, args.dry_run)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
        return

    # --recent path
    base = creds["WP_BASE_URL"].rstrip("/")
    auth = HTTPBasicAuth(creds["WP_USERNAME"], creds["WP_APP_PASSWORD"])
    r = requests.get(f"{base}/wp-json/wp/v2/posts",
                      params={"per_page": args.recent, "orderby": "date", "order": "desc"},
                      auth=auth, timeout=20)
    posts = r.json()
    if not args.force_redo:
        posts = [p for p in posts if p.get("featured_media") == 0]

    print(f"Processing {len(posts)} posts (limit {args.limit})", file=sys.stderr)
    results = []
    for p in posts[: args.limit]:
        out = process_one(creds, p["id"], args.dry_run)
        results.append(out)
        title = out.get("title", "?")
        status = out.get("status", "?")
        media = out.get("media_id", "—")
        print(f"  {status:<12} pid={p['id']} media={media} \"{title}\"", file=sys.stderr)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps({"processed": len(results), "ok": sum(1 for r in results if r.get("status") == "ok")}, indent=2))


if __name__ == "__main__":
    main()
