"""Growth automation helpers for SEO stage-2 commands."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import csv
import html
import json
import re


def _slug_to_words(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else "home"
    tokens = [t for t in re.split(r"[-_]+", slug) if t]
    if not tokens:
        return "homepage"
    return " ".join(tokens[:8])


def generate_keyword_opportunities(
    gsc_client,
    days: int = 28,
    min_impressions: int = 80,
    min_position: float = 8.0,
    max_position: float = 20.0,
    max_items: int = 10,
    output_path: str | None = None,
) -> Dict:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    request = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "dimensions": ["query"],
        "rowLimit": 500,
        "startRow": 0,
    }

    response = gsc_client.service.searchanalytics().query(
        siteUrl=gsc_client.property_url,
        body=request,
    ).execute()

    rows = response.get("rows", []) or []
    candidates: List[Dict] = []
    for row in rows:
        query = (row.get("keys") or [""])[0].strip().lower()
        impressions = int(row.get("impressions", 0) or 0)
        clicks = int(row.get("clicks", 0) or 0)
        ctr = float(row.get("ctr", 0.0) or 0.0) * 100.0
        position = float(row.get("position", 0.0) or 0.0)

        if not query or len(query) < 3:
            continue
        if impressions < min_impressions:
            continue
        if position < min_position or position > max_position:
            continue

        score = impressions * max(0.1, (1.2 - ctr / 10.0)) * max(0.5, (22.0 - position) / 14.0)

        candidates.append(
            {
                "query": query,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": round(ctr, 2),
                "position": round(position, 2),
                "opportunity_score": round(score, 2),
                "suggested_title": f"{query.title()} in Australia: 2026 Guide",
                "suggested_slug": re.sub(r"[^a-z0-9]+", "-", query).strip("-")[:80],
            }
        )

    candidates = sorted(candidates, key=lambda x: x["opportunity_score"], reverse=True)[:max_items]

    markdown_lines = [
        "# Next 10 SEO Articles",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Window: {days} days",
        "",
    ]

    if not candidates:
        markdown_lines.append("No opportunities found with current filters.")
    else:
        for i, item in enumerate(candidates, 1):
            markdown_lines.append(f"## {i}. {item['query']}")
            markdown_lines.append(f"- impressions: {item['impressions']}")
            markdown_lines.append(f"- clicks: {item['clicks']}")
            markdown_lines.append(f"- ctr: {item['ctr']}%")
            markdown_lines.append(f"- position: {item['position']}")
            markdown_lines.append(f"- score: {item['opportunity_score']}")
            markdown_lines.append(f"- suggested title: {item['suggested_title']}")
            markdown_lines.append(f"- suggested slug: {item['suggested_slug']}")
            markdown_lines.append("")

    markdown_text = "\n".join(markdown_lines)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown_text, encoding="utf-8")

    return {
        "count": len(candidates),
        "items": candidates,
        "markdown": markdown_text,
        "output_path": output_path,
    }


def _extract_internal_links(base_host: str, html_content: str) -> List[str]:
    urls = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html_content or "", flags=re.IGNORECASE):
        u = m.group(1).strip()
        parsed = urlparse(u)
        if parsed.scheme in {"http", "https"} and parsed.netloc == base_host:
            urls.append(u.split("#", 1)[0])
    return urls


def _insert_first_link(html_content: str, keyword: str, target_url: str) -> Tuple[str, bool]:
    if not html_content or not keyword or not target_url:
        return html_content, False
    if target_url in html_content:
        return html_content, False

    pattern = re.compile(rf"\b({re.escape(keyword)})\b", flags=re.IGNORECASE)
    replacement = f'<a href="{html.escape(target_url)}">\\1</a>'
    new_html, n = pattern.subn(replacement, html_content, count=1)
    return new_html, n > 0


def sync_internal_links(
    wp_client,
    base_url: str,
    max_posts: int = 80,
    output_orphan_csv: str | None = None,
) -> Dict:
    base_host = urlparse(base_url).netloc
    categories = wp_client.get_categories()

    # keyword -> target url map from categories
    keyword_targets: List[Tuple[str, str]] = []
    for c in categories:
        name = str(c.get("name") or "").strip()
        slug = str(c.get("slug") or "").strip()
        if not name or not slug:
            continue
        keyword_targets.append((name, f"{base_url.rstrip('/')}/category/{slug}/"))

    posts = wp_client.list_posts(status="publish", per_page=max_posts)
    pages = wp_client.list_pages(status="publish", per_page=max_posts)
    docs = posts + pages

    updated = 0
    touched_urls: List[str] = []
    inbound_count: Dict[str, int] = {}
    known_urls = set()

    for d in docs:
        link = d.get("link", "")
        if link:
            known_urls.add(link.split("#", 1)[0])

    for d in docs:
        content = ((d.get("content") or {}).get("raw") or (d.get("content") or {}).get("rendered") or "")
        if not content:
            continue

        for href in _extract_internal_links(base_host, content):
            inbound_count[href] = inbound_count.get(href, 0) + 1

        changed = False
        for keyword, target in keyword_targets[:30]:
            if keyword.lower() in (content or "").lower() and target != d.get("link"):
                new_content, ok = _insert_first_link(content, keyword, target)
                if ok:
                    content = new_content
                    changed = True
                    break

        if changed:
            item_id = int(d.get("id"))
            item_type = "posts" if d.get("type") == "post" else "pages"
            wp_client.update_item_content(item_type=item_type, item_id=item_id, html_content=content)
            updated += 1
            if d.get("link"):
                touched_urls.append(d.get("link"))

    orphans = []
    for url in sorted(known_urls):
        if inbound_count.get(url, 0) == 0:
            orphans.append(url)

    if output_orphan_csv:
        out = Path(output_orphan_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["url", "inbound_links", "slug_hint"])
            for u in orphans:
                writer.writerow([u, 0, _slug_to_words(u)])

    return {
        "updated_count": updated,
        "touched_urls": touched_urls,
        "orphans_count": len(orphans),
        "orphans": orphans[:50],
        "orphan_csv": output_orphan_csv,
    }


def _build_faq_items(category_name: str) -> List[Tuple[str, str]]:
    return [
        (f"What is the best way to choose {category_name}?", f"Compare flavor profile, pack size, and event type before choosing {category_name} products."),
        (f"Do you offer bulk {category_name} options?", f"Yes, bulk {category_name} packs are available for events and wholesale buyers."),
        (f"How should {category_name} be stored?", f"Store {category_name} in a cool, dry place away from direct sunlight."),
        (f"Is Australia-wide shipping available for {category_name}?", f"Shipping options vary by location and order size, including most Australian metro areas."),
        (f"Can I mix different {category_name} products in one order?", f"Mixed orders are usually possible and often helpful for variety packs or events."),
    ]


def _faq_html_block(category_name: str) -> str:
    items = _build_faq_items(category_name)
    faq_list_html = "\n".join([f"<h3>{html.escape(q)}</h3>\n<p>{html.escape(a)}</p>" for q, a in items])
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in items
        ],
    }
    return (
        f"\n<h2>{html.escape(category_name)} FAQs</h2>\n"
        f"{faq_list_html}\n"
        f"<script type=\"application/ld+json\">{json.dumps(schema, ensure_ascii=False)}</script>\n"
    )


def enrich_category_faq(wp_client, max_categories: int = 30) -> Dict:
    categories = wp_client.get_categories()[:max_categories]
    updated = []

    for cat in categories:
        cat_id = int(cat.get("id"))
        cat_name = str(cat.get("name") or "Category")
        desc = str(cat.get("description") or "")
        if "application/ld+json" in desc.lower() and "faqpage" in desc.lower():
            continue

        new_desc = (desc + "\n" + _faq_html_block(cat_name)).strip()
        ok = wp_client.update_category_description(cat_id=cat_id, description_html=new_desc)
        if ok:
            updated.append({"id": cat_id, "name": cat_name, "slug": cat.get("slug", "")})

    return {
        "updated_count": len(updated),
        "updated_categories": updated[:50],
    }
