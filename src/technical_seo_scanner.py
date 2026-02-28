"""Technical SEO scanner utilities with weighted scan levels."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import time

import requests


SCAN_LEVELS: Dict[str, Dict[str, float]] = {
    "light": {"max_pages": 12, "request_delay": 0.8, "timeout": 12},
    "standard": {"max_pages": 30, "request_delay": 0.5, "timeout": 15},
    "deep": {"max_pages": 80, "request_delay": 0.35, "timeout": 20},
    "full": {"max_pages": 200, "request_delay": 0.25, "timeout": 20},
}


@dataclass
class PageCheck:
    url: str
    status_code: int
    title: str
    meta_description: str
    canonical: str
    h1_count: int
    noindex: bool


class _SimpleSeoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: List[str] = []
        self.h1_count = 0
        self.meta_description = ""
        self.meta_robots = ""
        self.canonical = ""
        self.links: Set[str] = set()

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        t = tag.lower()

        if t == "title":
            self.in_title = True
        elif t == "h1":
            self.h1_count += 1
        elif t == "meta":
            name = attr_map.get("name", "").lower()
            content = attr_map.get("content", "").strip()
            if name == "description" and not self.meta_description:
                self.meta_description = content
            if name == "robots" and not self.meta_robots:
                self.meta_robots = content.lower()
        elif t == "link":
            rel = attr_map.get("rel", "").lower()
            href = attr_map.get("href", "").strip()
            if "canonical" in rel and href and not self.canonical:
                self.canonical = href
        elif t == "a":
            href = attr_map.get("href", "").strip()
            if href:
                self.links.add(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(x.strip() for x in self.title_parts if x.strip()).strip()


class _RequestGate:
    def __init__(self, request_delay: float) -> None:
        self.request_delay = max(0.0, request_delay)
        self._last_at = 0.0

    def wait(self) -> None:
        if self.request_delay <= 0:
            return
        now = time.time()
        sleep_for = self.request_delay - (now - self._last_at)
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last_at = time.time()


def _normalize_base_url(url: str) -> str:
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u.rstrip("/")


def _is_internal_link(base_url: str, candidate: str) -> bool:
    if not candidate or candidate.startswith(("mailto:", "tel:", "javascript:")):
        return False
    absolute = urljoin(base_url + "/", candidate)
    return urlparse(absolute).netloc == urlparse(base_url).netloc


def _to_internal_url(base_url: str, candidate: str) -> str:
    return urljoin(base_url + "/", candidate).split("#", 1)[0]


def _fetch_text(url: str, timeout: int, gate: _RequestGate) -> Tuple[int, str, str]:
    gate.wait()
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "seo-technical-scanner/2.0"},
        allow_redirects=True,
    )
    return response.status_code, response.url, response.text or ""


def _extract_sitemap_urls(xml_text: str, max_urls: int) -> List[str]:
    urls: List[str] = []
    try:
        root = ET.fromstring(xml_text)
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

        if root.tag.endswith("sitemapindex"):
            for loc in root.findall(f".//{ns}loc"):
                if loc.text:
                    urls.append(loc.text.strip())
                    if len(urls) >= max_urls:
                        break
            return urls

        for loc in root.findall(f".//{ns}loc"):
            if loc.text:
                urls.append(loc.text.strip())
                if len(urls) >= max_urls:
                    break
    except Exception:
        return []
    return urls


def _score_url(url: str, base_host: str) -> int:
    parsed = urlparse(url)
    if parsed.netloc != base_host:
        return -1000

    path = (parsed.path or "/").lower()
    score = 0

    if path in ("", "/"):
        score += 200
    if "/product" in path or "/products" in path:
        score += 140
    if "/category" in path or "/collections" in path:
        score += 120
    if "/blog" in path or "/news" in path:
        score += 100
    if "/tag/" in path or "?" in url:
        score -= 40
    if any(ext in path for ext in [".jpg", ".png", ".pdf", ".webp", ".svg", ".xml"]):
        score -= 300

    depth = len([x for x in path.split("/") if x])
    score -= depth * 5
    return score


def _check_page(url: str, timeout: int, gate: _RequestGate) -> Tuple[PageCheck, Set[str]]:
    status_code, final_url, html_text = _fetch_text(url, timeout=timeout, gate=gate)
    parser = _SimpleSeoParser()
    parser.feed(html_text)

    page = PageCheck(
        url=final_url,
        status_code=status_code,
        title=parser.title,
        meta_description=parser.meta_description,
        canonical=parser.canonical,
        h1_count=parser.h1_count,
        noindex=("noindex" in parser.meta_robots),
    )

    links: Set[str] = set()
    for raw in parser.links:
        if _is_internal_link(final_url, raw):
            links.add(_to_internal_url(final_url, raw))
    return page, links


def run_technical_scan(
    base_url: str,
    scan_level: str = "light",
    max_pages: int | None = None,
    timeout: int | None = None,
) -> Dict:
    base_url = _normalize_base_url(base_url)
    level = (scan_level or "light").strip().lower()
    if level not in SCAN_LEVELS:
        level = "light"

    profile = SCAN_LEVELS[level]
    resolved_max_pages = int(max_pages) if max_pages else int(profile["max_pages"])
    resolved_timeout = int(timeout) if timeout else int(profile["timeout"])
    request_delay = float(profile["request_delay"])
    resolved_max_pages = max(5, min(resolved_max_pages, 300))

    gate = _RequestGate(request_delay=request_delay)

    result: Dict = {
        "base_url": base_url,
        "scan_level": level,
        "scan_profile": {
            "max_pages": resolved_max_pages,
            "request_delay": request_delay,
            "timeout": resolved_timeout,
        },
        "robots": {"url": f"{base_url}/robots.txt", "status": "missing"},
        "sitemap": {"url": f"{base_url}/sitemap.xml", "status": "missing", "url_count": 0},
        "scanned_pages": [],
        "issues": [],
        "stats": {},
    }

    try:
        robots_status, _, robots_text = _fetch_text(f"{base_url}/robots.txt", timeout=resolved_timeout, gate=gate)
        if robots_status == 200 and robots_text.strip():
            result["robots"] = {"url": f"{base_url}/robots.txt", "status": "ok"}
        else:
            result["issues"].append("robots.txt is missing or inaccessible")
    except Exception as exc:
        result["issues"].append(f"robots.txt check failed: {exc}")

    sitemap_urls: List[str] = []
    try:
        sitemap_status, _, sitemap_text = _fetch_text(f"{base_url}/sitemap.xml", timeout=resolved_timeout, gate=gate)
        if sitemap_status == 200 and sitemap_text.strip():
            sitemap_urls = _extract_sitemap_urls(sitemap_text, max_urls=resolved_max_pages * 3)
            result["sitemap"] = {
                "url": f"{base_url}/sitemap.xml",
                "status": "ok",
                "url_count": len(sitemap_urls),
            }
        else:
            result["issues"].append("sitemap.xml is missing or inaccessible")
    except Exception as exc:
        result["issues"].append(f"sitemap.xml check failed: {exc}")

    home_links: Set[str] = set()
    try:
        _, final_home, home_html = _fetch_text(base_url + "/", timeout=resolved_timeout, gate=gate)
        parser = _SimpleSeoParser()
        parser.feed(home_html)
        for raw in parser.links:
            if _is_internal_link(final_home, raw):
                home_links.add(_to_internal_url(final_home, raw))
    except Exception as exc:
        result["issues"].append(f"Home page seed extraction failed: {exc}")

    seeds = set([base_url + "/"]) | set(sitemap_urls) | home_links
    base_host = urlparse(base_url).netloc
    weighted_urls = sorted(
        seeds,
        key=lambda u: _score_url(u, base_host),
        reverse=True,
    )

    to_scan = weighted_urls[:resolved_max_pages]
    seen: Set[str] = set()
    pages: List[PageCheck] = []

    for page_url in to_scan:
        if page_url in seen:
            continue
        seen.add(page_url)
        try:
            page, _ = _check_page(page_url, timeout=resolved_timeout, gate=gate)
            pages.append(page)
        except Exception as exc:
            result["issues"].append(f"Failed to scan {page_url}: {exc}")

    title_count: Dict[str, int] = {}
    for p in pages:
        if p.title:
            title_count[p.title] = title_count.get(p.title, 0) + 1
    duplicate_titles = {t for t, c in title_count.items() if c > 1}

    missing_title = 0
    missing_description = 0
    missing_canonical = 0
    missing_h1 = 0
    noindex_count = 0
    non_200 = 0

    for p in pages:
        if p.status_code != 200:
            non_200 += 1
        if not p.title:
            missing_title += 1
            result["issues"].append(f"Missing <title>: {p.url}")
        if p.title in duplicate_titles:
            result["issues"].append(f"Duplicate <title>: {p.url}")
        if not p.meta_description:
            missing_description += 1
            result["issues"].append(f"Missing meta description: {p.url}")
        if not p.canonical:
            missing_canonical += 1
            result["issues"].append(f"Missing canonical link: {p.url}")
        if p.h1_count == 0:
            missing_h1 += 1
            result["issues"].append(f"Missing H1: {p.url}")
        if p.noindex:
            noindex_count += 1
            result["issues"].append(f"Page is noindex: {p.url}")

        result["scanned_pages"].append(
            {
                "url": p.url,
                "status_code": p.status_code,
                "title": p.title,
                "has_meta_description": bool(p.meta_description),
                "has_canonical": bool(p.canonical),
                "h1_count": p.h1_count,
                "noindex": p.noindex,
            }
        )

    result["stats"] = {
        "pages_scanned": len(pages),
        "candidate_urls_found": len(weighted_urls),
        "non_200_pages": non_200,
        "missing_title": missing_title,
        "duplicate_title_count": len(duplicate_titles),
        "missing_meta_description": missing_description,
        "missing_canonical": missing_canonical,
        "missing_h1": missing_h1,
        "noindex_pages": noindex_count,
    }
    return result


def format_technical_scan_report(scan: Dict) -> str:
    stats = scan.get("stats", {})
    robots = scan.get("robots", {})
    sitemap = scan.get("sitemap", {})
    profile = scan.get("scan_profile", {})
    issues = scan.get("issues", [])

    lines = [
        "SEO Technical Scan Report",
        f"Site: {scan.get('base_url', '-')}",
        f"Scan level: {scan.get('scan_level', 'light')}",
        f"Scan profile: max_pages={profile.get('max_pages', '-')}, delay={profile.get('request_delay', '-')}, timeout={profile.get('timeout', '-')}",
        f"Robots: {robots.get('status', 'unknown')} ({robots.get('url', '-')})",
        f"Sitemap: {sitemap.get('status', 'unknown')} ({sitemap.get('url', '-')})",
        f"Sitemap URL count: {sitemap.get('url_count', 0)}",
        "",
        "Summary",
        f"- Candidate URLs found: {stats.get('candidate_urls_found', 0)}",
        f"- Pages scanned: {stats.get('pages_scanned', 0)}",
        f"- Non-200 pages: {stats.get('non_200_pages', 0)}",
        f"- Missing title: {stats.get('missing_title', 0)}",
        f"- Duplicate title groups: {stats.get('duplicate_title_count', 0)}",
        f"- Missing meta description: {stats.get('missing_meta_description', 0)}",
        f"- Missing canonical: {stats.get('missing_canonical', 0)}",
        f"- Missing H1: {stats.get('missing_h1', 0)}",
        f"- Noindex pages: {stats.get('noindex_pages', 0)}",
        "",
        "Top Issues",
    ]

    if not issues:
        lines.append("- No major technical SEO issues detected in scanned pages")
    else:
        for issue in issues[:25]:
            lines.append(f"- {issue}")

    lines.extend(
        [
            "",
            "Recommended levels",
            "- light: daily quick check (default)",
            "- standard: weekly scan",
            "- deep: pre-release or monthly audit",
            "- full: off-peak full-site crawl",
        ]
    )

    return "\n".join(lines)
