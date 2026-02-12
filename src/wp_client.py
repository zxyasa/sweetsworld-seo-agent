"""WordPress REST API client for creating draft posts."""
import base64
from typing import Dict, Any
import requests


class WPClient:
    """Client for interacting with WordPress REST API."""

    def __init__(self, base_url: str, username: str, app_password: str):
        """
        Initialize WordPress client with Basic Auth credentials.

        Args:
            base_url: WordPress site base URL (e.g., https://sweetsworld.com.au)
            username: WordPress username
            app_password: WordPress Application Password
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.username = username

        # Create Basic Auth header
        credentials = f"{username}:{app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> bool:
        """
        Test WordPress REST API connection and authentication.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            test_url = f"{self.api_url}/users/me"
            response = requests.get(test_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def create_post_draft(
        self,
        title: str,
        slug: str,
        html: str,
        excerpt: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new draft post via WordPress REST API.

        Args:
            title: Post title
            slug: Post slug (URL-friendly identifier)
            html: Post content in HTML format
            excerpt: Optional post excerpt/summary

        Returns:
            Dict containing the created post data from WordPress API

        Raises:
            requests.HTTPError: If the API request fails with detailed error message
        """
        endpoint = f"{self.api_url}/posts"

        payload = {
            "title": title,
            "slug": slug,
            "content": html,
            "status": "draft",  # Create as draft, not published
        }

        if excerpt:
            payload["excerpt"] = excerpt

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            # Check for specific error codes and provide helpful messages
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

            # Raise for any other 4xx/5xx status codes
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
            # Re-raise if it's already an HTTPError with our custom message
            if isinstance(e, requests.HTTPError) and "❌" in str(e):
                raise
            # Otherwise, wrap in a generic error
            raise requests.HTTPError(
                f"❌ Request Error: {str(e)}"
            )
