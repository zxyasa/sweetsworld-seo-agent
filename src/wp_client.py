"""WordPress REST API client for creating and updating posts."""
import base64
import logging
import os
import time
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

import requests

logger = logging.getLogger(__name__)

# Status codes worth retrying (transient server-side issues)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# ---------------------------------------------------------------------------
# Optional BasePublisher integration
# website-os may not be on PYTHONPATH — degrade gracefully if not available.
# ---------------------------------------------------------------------------
try:
    from apps.website_os.shared.publisher import (  # type: ignore[import]
        BasePublisher,
        PublishPayload,
        PublishResult,
    )
    _HAS_BASE_PUBLISHER = True
except ImportError:
    _HAS_BASE_PUBLISHER = False
    BasePublisher = object  # type: ignore[assignment,misc]
    PublishPayload = None   # type: ignore[assignment]
    PublishResult = None    # type: ignore[assignment]


def _normalize_media_source_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(str(url))
    return unquote(parsed.path or "").rstrip("/").lower()


class WPClient(BasePublisher):
    """Client for interacting with the WordPress REST API.

    Inherits BasePublisher when website-os is on the Python path (see import
    guard above).  When BasePublisher is unavailable the fallback ``object``
    base is used and the class operates identically — only the formal interface
    contract is absent.
    """

    # ------------------------------------------------------------------
    # BasePublisher interface
    # ------------------------------------------------------------------

    @property
    def channel_name(self) -> str:
        """Machine-readable channel identifier."""
        return "wordpress"

    def publish(self, payload: Any, *, dry_run: bool = False) -> Any:
        """Implement BasePublisher.publish using create_post_draft + publish_post.

        Accepts a ``PublishPayload`` instance when website-os is available, or
        any object with the same attributes.  Returns a ``PublishResult`` when
        website-os is available; otherwise returns a plain dict so that callers
        that don't import BasePublisher can still use the return value.

        This method never raises — all errors are caught and returned via the
        result's ``error`` field (or ``success=False`` in the plain-dict path).
        """
        if payload is None:
            if _HAS_BASE_PUBLISHER:
                return PublishResult(
                    success=False,
                    channel=self.channel_name,
                    error="payload is None",
                    dry_run=dry_run,
                )
            return {"success": False, "channel": self.channel_name, "error": "payload is None"}

        if dry_run:
            if _HAS_BASE_PUBLISHER:
                return PublishResult(
                    success=True,
                    channel=self.channel_name,
                    dry_run=True,
                    metadata={"slug": getattr(payload, "slug", ""), "dry_run": True},
                )
            return {"success": True, "channel": self.channel_name, "dry_run": True}

        try:
            post_data = self.create_post_draft(
                title=getattr(payload, "title", ""),
                slug=getattr(payload, "slug", ""),
                html=getattr(payload, "content_html", ""),
                excerpt=getattr(payload, "excerpt", ""),
            )
            post_id = post_data.get("id")
            if not post_id:
                raise ValueError(f"WordPress did not return a post ID: {post_data}")

            published = self.publish_post(int(post_id))
            url = published.get("link") or published.get("guid", {}).get("rendered")

            if _HAS_BASE_PUBLISHER:
                return PublishResult(
                    success=True,
                    channel=self.channel_name,
                    published_url=url,
                    platform_id=str(post_id),
                    dry_run=False,
                    metadata={"post_id": post_id},
                )
            return {
                "success": True,
                "channel": self.channel_name,
                "published_url": url,
                "platform_id": str(post_id),
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("WPClient.publish failed for slug '%s': %s", getattr(payload, "slug", "?"), exc)
            if _HAS_BASE_PUBLISHER:
                return PublishResult(
                    success=False,
                    channel=self.channel_name,
                    error=str(exc),
                    dry_run=dry_run,
                )
            return {"success": False, "channel": self.channel_name, "error": str(exc)}

    # ------------------------------------------------------------------
    # Original constructor (unchanged)
    # ------------------------------------------------------------------

    def __init__(self, base_url: str, username: str, app_password: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.username = username

        credentials = f"{username}:{app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        retries: int = 3,
        backoff: float = 2.0,
        **kwargs: Any,
    ) -> requests.Response:
        """Send an HTTP request, retrying on transient server errors.

        Retries on status codes in _RETRYABLE_STATUS (429, 500, 502, 503, 504).
        Wait time doubles each attempt: backoff * 2^attempt seconds.
        Non-retryable errors (401, 403, 404, network) raise immediately.
        """
        last_exc: Optional[Exception] = None
        fn = getattr(requests, method.lower())

        for attempt in range(retries + 1):
            try:
                response = fn(url, headers=self.headers, **kwargs)
                if response.status_code in _RETRYABLE_STATUS and attempt < retries:
                    wait = backoff * (2 ** attempt)
                    logger.warning(
                        f"WP API returned {response.status_code} on attempt {attempt + 1}/{retries + 1}; "
                        f"retrying in {wait:.0f}s"
                    )
                    time.sleep(wait)
                    continue
                return response
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                if attempt < retries:
                    wait = backoff * (2 ** attempt)
                    logger.warning(
                        f"WP API connection error on attempt {attempt + 1}/{retries + 1}: {exc}; "
                        f"retrying in {wait:.0f}s"
                    )
                    time.sleep(wait)
                else:
                    raise

        # Should not be reached, but satisfy type checker
        if last_exc:
            raise last_exc
        raise requests.HTTPError(f"Request failed after {retries + 1} attempts")

    def test_connection(self) -> bool:
        try:
            test_url = f"{self.api_url}/users/me"
            response = requests.get(test_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as exc:
            logger.warning("WP connection test failed: %s", exc)
            return False

    def get_categories(self) -> List[Dict[str, Any]]:
        endpoint = f"{self.api_url}/categories"
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"per_page": 100, "hide_empty": False},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to fetch WP categories: %s", exc)
            return []


    def find_category_by_slug(self, slug: str) -> Dict[str, Any] | None:
        cleaned_slug = str(slug or '').strip()
        if not cleaned_slug:
            return None

        endpoint = f"{self.api_url}/categories"
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"slug": cleaned_slug, "per_page": 1, "hide_empty": False},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                item = data[0]
                return item if isinstance(item, dict) else None
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to find WP category by slug '%s': %s", cleaned_slug, exc)
            return None
        return None

    def ensure_category(self, slug: str, name: str, parent: int = 0) -> Dict[str, Any]:
        existing = self.find_category_by_slug(slug)
        if existing:
            return existing

        endpoint = f"{self.api_url}/categories"
        payload: Dict[str, Any] = {"slug": str(slug or '').strip(), "name": str(name or '').strip()}
        if parent:
            payload["parent"] = int(parent)

        response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}

    def update_post_categories(self, post_id: int, category_ids: List[int]) -> Dict[str, Any]:
        clean_ids = [int(category_id) for category_id in category_ids if category_id is not None]
        return self._update_item("posts", post_id, {"categories": clean_ids})

    def list_posts(self, status: str = "publish", per_page: int = 50) -> List[Dict[str, Any]]:
        endpoint = f"{self.api_url}/posts"
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"status": status, "per_page": min(max(per_page, 1), 100), "context": "edit"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to list WP posts with status '%s': %s", status, exc)
            return []

    def list_pages(self, status: str = "publish", per_page: int = 50) -> List[Dict[str, Any]]:
        endpoint = f"{self.api_url}/pages"
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"status": status, "per_page": min(max(per_page, 1), 100), "context": "edit"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to list WP pages with status '%s': %s", status, exc)
            return []

    def find_media_by_source_url(self, image_url: str) -> Dict[str, Any] | None:
        normalized_target = _normalize_media_source_url(image_url)
        if not normalized_target:
            return None

        filename = PurePosixPath(urlparse(image_url).path).name
        stem = PurePosixPath(filename).stem
        search_terms = [term for term in [stem, filename] if term]
        endpoint = f"{self.api_url}/media"

        for term in search_terms:
            try:
                response = requests.get(
                    endpoint,
                    headers=self.headers,
                    params={"search": term, "per_page": 25},
                    timeout=20,
                )
                if response.status_code >= 400:
                    continue
                data = response.json()
                if not isinstance(data, list):
                    continue

                for row in data:
                    source_url = str(row.get("source_url") or "")
                    normalized_source = _normalize_media_source_url(source_url)
                    if normalized_source == normalized_target:
                        return row if isinstance(row, dict) else None

                for row in data:
                    source_url = str(row.get("source_url") or "")
                    if filename and PurePosixPath(urlparse(source_url).path).name == filename:
                        return row if isinstance(row, dict) else None
            except requests.exceptions.RequestException as exc:
                logger.warning("Failed to search WP media for '%s': %s", image_url, exc)
                continue

        # Fallback: image URL is reachable but not in media library (orphan upload).
        # Re-import via wp/v2/media so subsequent posts hit the cache.
        return self._reimport_orphan_media(image_url, filename)

    def _reimport_orphan_media(self, image_url: str, filename: str) -> Dict[str, Any] | None:
        """When find_media_by_source_url returns None but the URL is reachable, download
        the file and re-upload via wp/v2/media to register it as an attachment."""
        try:
            r = requests.get(image_url, timeout=30)
            if r.status_code != 200 or not r.content:
                logger.warning("Re-import skipped: %s returned HTTP %s", image_url, r.status_code)
                return None
            # Guess mime
            import mimetypes
            mime, _ = mimetypes.guess_type(image_url)
            if not mime:
                mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            upload_resp = requests.post(
                f"{self.api_url}/media",
                headers={
                    **{k: v for k, v in self.headers.items() if k != "Content-Type"},
                    "Content-Type": mime,
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
                data=r.content,
                timeout=120,
            )
            if upload_resp.status_code in (200, 201):
                logger.info("  Re-imported orphan media: %s → id=%s", filename, upload_resp.json().get("id"))
                return upload_resp.json()
            logger.warning("Re-import failed: HTTP %s for %s", upload_resp.status_code, filename)
        except Exception as exc:
            logger.warning("Re-import exception for %s: %s", filename, exc)
        return None

    def find_similar_posts(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        endpoint = f"{self.api_url}/posts"
        results: List[Dict[str, Any]] = []
        seen = set()

        for status in ["draft", "publish", "pending", "future"]:
            try:
                response = requests.get(
                    endpoint,
                    headers=self.headers,
                    params={
                        "search": query,
                        "status": status,
                        "per_page": max_results,
                        "orderby": "relevance",
                    },
                    timeout=20,
                )
                if response.status_code >= 400:
                    continue
                data = response.json()
                if not isinstance(data, list):
                    continue

                for row in data:
                    post_id = row.get("id")
                    if post_id in seen:
                        continue
                    seen.add(post_id)
                    results.append(
                        {
                            "id": post_id,
                            "title": (row.get("title") or {}).get("rendered", ""),
                            "link": row.get("link") or f"{self.base_url}/?p={post_id}",
                            "status": row.get("status", status),
                        }
                    )
                    if len(results) >= max_results:
                        return results
            except requests.exceptions.RequestException as exc:
                logger.warning("Failed to search WP posts for query '%s' with status '%s': %s", query, status, exc)
                continue

        return results[:max_results]

    def find_post_by_slug(self, slug: str, statuses: List[str] | None = None) -> Dict[str, Any] | None:
        return self._find_item_by_slug(
            item_type="posts",
            slug=slug,
            statuses=statuses or ["draft", "publish", "pending", "future", "private"],
        )

    def create_post_draft(
        self,
        title: str,
        slug: str,
        html: str,
        excerpt: str = "",
        category_id: int | None = None,
        seo_meta: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        endpoint = f"{self.api_url}/posts"

        payload: Dict[str, Any] = {
            "title": title,
            "slug": slug,
            "content": html,
            "status": "draft",
        }

        if excerpt:
            payload["excerpt"] = excerpt
        if category_id:
            payload["categories"] = [int(category_id)]
        if seo_meta:
            payload["meta"] = seo_meta

        try:
            response = self._request_with_retry("post", endpoint, json=payload, timeout=30)

            if response.status_code == 401:
                raise requests.HTTPError(
                    f"ERROR: 401 Unauthorized - Authentication failed!\n"
                    f"   - Check your WordPress username: '{self.username}'\n"
                    f"   - Verify Application Password is correct (format: xxxx xxxx xxxx xxxx)\n"
                    f"   - Regenerate Application Password in WP Admin: Users -> Profile -> Application Passwords"
                )
            if response.status_code == 403:
                raise requests.HTTPError(
                    f"ERROR: 403 Forbidden - Permission denied!\n"
                    f"   - User '{self.username}' lacks permission to create posts\n"
                    f"   - Required role: Editor or Administrator\n"
                    f"   - Check if security plugins (Wordfence, etc.) are blocking REST API\n"
                    f"   - Try temporarily disabling security plugins"
                )
            if response.status_code == 404:
                raise requests.HTTPError(
                    f"ERROR: 404 Not Found - WordPress REST API endpoint not available!\n"
                    f"   - Check WP_BASE_URL: {self.base_url}\n"
                    f"   - Test API manually: {self.base_url}/wp-json/wp/v2/posts\n"
                    f"   - Verify WordPress permalinks: Settings -> Permalinks -> Save Changes"
                )
            if response.status_code >= 500:
                raise requests.HTTPError(
                    f"ERROR: {response.status_code} Server Error - WordPress server issue!\n"
                    f"   - Check WordPress error logs\n"
                    f"   - Contact hosting provider if issue persists"
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError as exc:
            raise requests.HTTPError(
                f"ERROR: Connection Error - Cannot reach WordPress site!\n"
                f"   - Check network connection\n"
                f"   - Verify URL: {self.base_url}\n"
                f"   - Check firewall/proxy settings\n"
                f"   Original error: {str(exc)}"
            )
        except requests.exceptions.Timeout as exc:
            raise requests.HTTPError(
                f"ERROR: Timeout Error - Request took too long!\n"
                f"   - WordPress server may be slow\n"
                f"   - Try again in a few moments\n"
                f"   Original error: {str(exc)}"
            )
        except requests.exceptions.RequestException as exc:
            if isinstance(exc, requests.HTTPError) and "ERROR:" in str(exc):
                raise
            raise requests.HTTPError(f"ERROR: Request Error: {str(exc)}")

    def revert_to_draft(self, post_id: int) -> Dict[str, Any]:
        """Set a published post back to draft status in WordPress."""
        endpoint = f"{self.api_url}/posts/{post_id}"
        try:
            response = self._request_with_retry("post", endpoint, json={"status": "draft"}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise requests.HTTPError(f"ERROR: Revert to draft failed: {str(exc)}")

    def publish_post(self, post_id: int) -> Dict[str, Any]:
        endpoint = f"{self.api_url}/posts/{post_id}"
        payload = {"status": "publish"}

        try:
            response = self._request_with_retry("post", endpoint, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise requests.HTTPError(f"ERROR: Publish failed: {str(exc)}")

    def set_featured_media(self, post_id: int, media_id: int) -> Dict[str, Any]:
        endpoint = f"{self.api_url}/posts/{post_id}"
        payload = {"featured_media": int(media_id)}
        try:
            response = self._request_with_retry("post", endpoint, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise requests.HTTPError(f"ERROR: Failed to set featured media: {str(exc)}")

    def write_seo_meta_via_db(
        self,
        post_id: int,
        keyword: str = "",
        seo_title: str = "",
        seo_description: str = "",
        endpoint_token: Optional[str] = None,
    ) -> bool:
        """Write rank_math meta fields directly via server-side PHP script.
        Returns True on success, False on any error (non-fatal)."""
        if endpoint_token is None:
            endpoint_token = os.environ.get('WP_SEO_BRIDGE_TOKEN')
        if not endpoint_token:
            logger.warning("WP_SEO_BRIDGE_TOKEN not set, skipping SEO meta write for post %d", post_id)
            return False
        url = f"{self.base_url}/wp-seo-meta.php"
        payload = {
            "token": endpoint_token,
            "post_id": post_id,
            "keyword": keyword,
            "title": seo_title,
            "description": seo_description,
        }
        try:
            resp = requests.post(url, data=payload, timeout=15)
            data = resp.json()
            if data.get("ok"):
                logger.info(f"  SEO meta written for post {post_id}: {data.get('written')}")
                return True
            logger.warning(f"WARN: SEO meta write failed for post {post_id}: {data}")
        except Exception as exc:
            logger.warning(f"WARN: SEO meta write error for post {post_id}: {exc}")
        return False

    def _extract_slug_from_url(self, url: str) -> str:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            parts = [part for part in parsed.path.split('/') if part]
            if not parts:
                return ''
            return parts[-1].strip()
        except Exception:
            return ''

    def _find_item_by_slug(
        self,
        item_type: str,
        slug: str,
        statuses: List[str] | None = None,
    ) -> Dict[str, Any] | None:
        if not slug:
            return None

        endpoint = f"{self.api_url}/{item_type}"
        for status in statuses or ["publish"]:
            try:
                response = requests.get(
                    endpoint,
                    headers=self.headers,
                    params={"slug": slug, "per_page": 1, "status": status, "context": "edit"},
                    timeout=20,
                )
                if response.status_code >= 400:
                    continue
                data = response.json()
                if isinstance(data, list) and data:
                    item = data[0]
                    if isinstance(item, dict) and "status" not in item:
                        item["status"] = status
                    return item
            except requests.exceptions.RequestException as exc:
                logger.warning("Failed to find WP %s by slug '%s' with status '%s': %s", item_type, slug, status, exc)
                continue
        return None

    def _update_item(self, item_type: str, item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = f"{self.api_url}/{item_type}/{item_id}"
        response = self._request_with_retry("post", endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def update_item_content(self, item_type: str, item_id: int, html_content: str) -> bool:
        try:
            self._update_item(item_type=item_type, item_id=item_id, payload={"content": html_content})
            return True
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to update WP item content (%s/%s): %s", item_type, item_id, exc)
            return False

    def update_category_description(self, cat_id: int, description_html: str) -> bool:
        endpoint = f"{self.api_url}/categories/{cat_id}"
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json={"description": description_html},
                timeout=30,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to update WP category description (cat_id=%s): %s", cat_id, exc)
            return False

    def auto_fix_basic_seo_by_url(
        self,
        page_url: str,
        needs_title: bool,
        needs_meta_description: bool,
        needs_h1: bool,
    ) -> Dict[str, Any]:
        """Best-effort basic SEO fixes on WP posts/pages by URL slug."""
        import re

        slug = self._extract_slug_from_url(page_url)
        if not slug:
            return {"status": "skipped", "url": page_url, "reason": "could not extract slug"}

        item = self._find_item_by_slug('posts', slug)
        item_type = 'posts'
        if not item:
            item = self._find_item_by_slug('pages', slug)
            item_type = 'pages'
        if not item:
            return {"status": "skipped", "url": page_url, "reason": f"no post/page found for slug={slug}"}

        item_id = int(item.get('id'))
        title_raw = ((item.get('title') or {}).get('raw') or (item.get('title') or {}).get('rendered') or '').strip()
        content_raw = ((item.get('content') or {}).get('raw') or (item.get('content') or {}).get('rendered') or '').strip()
        excerpt_raw = ((item.get('excerpt') or {}).get('raw') or (item.get('excerpt') or {}).get('rendered') or '').strip()

        payload: Dict[str, Any] = {}
        changed: List[str] = []

        if needs_title and not title_raw:
            guessed_title = slug.replace('-', ' ').strip().title()
            if guessed_title:
                payload['title'] = guessed_title
                title_raw = guessed_title
                changed.append('title')

        if needs_h1 and '<h1' not in content_raw.lower():
            h1_text = title_raw or slug.replace('-', ' ').strip().title() or 'Article'
            payload['content'] = f"<h1>{h1_text}</h1>\n" + content_raw
            content_raw = payload['content']
            changed.append('h1')

        if needs_meta_description and not excerpt_raw:
            plain = re.sub(r'<[^>]+>', ' ', content_raw)
            plain = re.sub(r'\s+', ' ', plain).strip()
            if plain:
                payload['excerpt'] = plain[:155]
                changed.append('meta_description_excerpt')

        if not payload:
            return {
                "status": "skipped",
                "url": page_url,
                "item_id": item_id,
                "item_type": item_type,
                "reason": "nothing to fix",
            }

        try:
            self._update_item(item_type, item_id, payload)
            return {
                "status": "fixed",
                "url": page_url,
                "item_id": item_id,
                "item_type": item_type,
                "changed": changed,
            }
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "url": page_url,
                "item_id": item_id,
                "item_type": item_type,
                "reason": str(exc),
            }
