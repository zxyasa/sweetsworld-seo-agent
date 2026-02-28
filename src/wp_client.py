"""WordPress REST API client for creating draft posts."""
import base64
from typing import Dict, Any, List
import requests


class WPClient:
    """Client for interacting with WordPress REST API."""

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

    def test_connection(self) -> bool:
        try:
            test_url = f"{self.api_url}/users/me"
            response = requests.get(test_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def get_categories(self) -> List[Dict[str, Any]]:
        """Fetch available WordPress categories."""
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
            if isinstance(data, list):
                return data
            return []
        except requests.exceptions.RequestException:
            return []

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
        except requests.exceptions.RequestException:
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
        except requests.exceptions.RequestException:
            return []

    def find_similar_posts(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search potentially similar posts by query in title/content."""
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
            except requests.exceptions.RequestException:
                continue

        return results[:max_results]

    def create_post_draft(
        self,
        title: str,
        slug: str,
        html: str,
        excerpt: str = "",
        category_id: int | None = None,
    ) -> Dict[str, Any]:
        endpoint = f"{self.api_url}/posts"

        payload = {
            "title": title,
            "slug": slug,
            "content": html,
            "status": "draft",
        }

        if excerpt:
            payload["excerpt"] = excerpt
        if category_id:
            payload["categories"] = [int(category_id)]

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 401:
                raise requests.HTTPError(
                    f"❌ 401 Unauthorized - Authentication failed!\n"
                    f"   → Check your WordPress username: '{self.username}'\n"
                    f"   → Verify Application Password is correct (format: xxxx xxxx xxxx xxxx)\n"
                    f"   → Regenerate Application Password in WP Admin: Users → Profile → Application Passwords"
                )

            elif response.status_code == 403:
                raise requests.HTTPError(
                    f"❌ 403 Forbidden - Permission denied!\n"
                    f"   → User '{self.username}' lacks permission to create posts\n"
                    f"   → Required role: Editor or Administrator\n"
                    f"   → Check if security plugins (Wordfence, etc.) are blocking REST API\n"
                    f"   → Try temporarily disabling security plugins"
                )

            elif response.status_code == 404:
                raise requests.HTTPError(
                    f"❌ 404 Not Found - WordPress REST API endpoint not available!\n"
                    f"   → Check WP_BASE_URL: {self.base_url}\n"
                    f"   → Test API manually: {self.base_url}/wp-json/wp/v2/posts\n"
                    f"   → Verify WordPress permalinks: Settings → Permalinks → Save Changes"
                )

            elif response.status_code >= 500:
                raise requests.HTTPError(
                    f"❌ {response.status_code} Server Error - WordPress server issue!\n"
                    f"   → Check WordPress error logs\n"
                    f"   → Contact hosting provider if issue persists"
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError as e:
            raise requests.HTTPError(
                f"❌ Connection Error - Cannot reach WordPress site!\n"
                f"   → Check network connection\n"
                f"   → Verify URL: {self.base_url}\n"
                f"   → Check firewall/proxy settings\n"
                f"   Original error: {str(e)}"
            )

        except requests.exceptions.Timeout as e:
            raise requests.HTTPError(
                f"❌ Timeout Error - Request took too long!\n"
                f"   → WordPress server may be slow\n"
                f"   → Try again in a few moments\n"
                f"   Original error: {str(e)}"
            )

        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.HTTPError) and "❌" in str(e):
                raise
            raise requests.HTTPError(f"❌ Request Error: {str(e)}")

    def publish_post(self, post_id: int) -> Dict[str, Any]:
        """Publish an existing draft post via WordPress REST API."""
        endpoint = f"{self.api_url}/posts/{post_id}"
        payload = {"status": "publish"}

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise requests.HTTPError(f"❌ Publish failed: {str(e)}")


    def _extract_slug_from_url(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            parts = [p for p in parsed.path.split('/') if p]
            if not parts:
                return ''
            return parts[-1].strip()
        except Exception:
            return ''

    def _find_item_by_slug(self, item_type: str, slug: str) -> Dict[str, Any] | None:
        endpoint = f"{self.api_url}/{item_type}"
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params={"slug": slug, "per_page": 1, "status": "publish", "context": "edit"},
                timeout=20,
            )
            if response.status_code >= 400:
                return None
            data = response.json()
            if isinstance(data, list) and data:
                return data[0]
            return None
        except requests.exceptions.RequestException:
            return None

    def _update_item(self, item_type: str, item_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = f"{self.api_url}/{item_type}/{item_id}"
        response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def update_item_content(self, item_type: str, item_id: int, html_content: str) -> bool:
        try:
            self._update_item(item_type=item_type, item_id=item_id, payload={"content": html_content})
            return True
        except requests.exceptions.RequestException:
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
        except requests.exceptions.RequestException:
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
        changed: list[str] = []

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
            return {"status": "skipped", "url": page_url, "item_id": item_id, "item_type": item_type, "reason": "nothing to fix"}

        try:
            self._update_item(item_type, item_id, payload)
            return {
                "status": "fixed",
                "url": page_url,
                "item_id": item_id,
                "item_type": item_type,
                "changed": changed,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "url": page_url,
                "item_id": item_id,
                "item_type": item_type,
                "reason": str(e),
            }
