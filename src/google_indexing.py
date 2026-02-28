"""Google Indexing API helper (best-effort)."""

from __future__ import annotations

from typing import Dict

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


INDEXING_SCOPE = "https://www.googleapis.com/auth/indexing"
INDEXING_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def submit_url(url: str, credentials_file: str, notify_type: str = "URL_UPDATED") -> Dict[str, str]:
    """Submit a URL update/removal notification to Google Indexing API."""
    if not url:
        return {"status": "error", "message": "empty url"}

    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=[INDEXING_SCOPE],
        )
        session = AuthorizedSession(creds)
        payload = {"url": url, "type": notify_type}
        resp = session.post(INDEXING_ENDPOINT, json=payload, timeout=20)

        if resp.status_code >= 400:
            return {
                "status": "error",
                "message": f"HTTP {resp.status_code}: {resp.text[:400]}",
            }

        data = resp.json()
        return {
            "status": "success",
            "message": "submitted",
            "url": url,
            "notify_type": notify_type,
            "response": str(data)[:500],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
