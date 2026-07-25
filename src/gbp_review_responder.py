"""Auto-respond to new Google Business Profile reviews + notify via Telegram.

Reads GBP OAuth credentials from site .env, checks all locations for unreplied
reviews, generates appropriate replies by star rating, and sends Telegram alerts.

Usage:
    python3 src/gbp_review_responder.py --site sweetsworld [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SITES_DIR = Path(__file__).resolve().parent.parent / "sites"

# OAuth credentials (shared with social-network-create-post-agent)
SOCIAL_AGENT_ENV = Path(__file__).resolve().parent.parent.parent / "social-network-create-post-agent" / ".env"

GBP_API_BASE = "https://mybusiness.googleapis.com/v4"


def _load_env(path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        k, v = key.strip(), value.strip()
        os.environ[k] = v
        loaded[k] = v
    return loaded


def _get_access_token() -> str:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("Missing GOOGLE_OAUTH_* env vars")

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=json.dumps({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())["access_token"]


def _gbp_request(url: str, token: str, method: str = "GET",
                 data: dict | None = None) -> Any:
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=20)
    return json.loads(resp.read())


def generate_reply(star_rating: str, reviewer_name: str, store_name: str,
                   comment: str) -> str:
    """Generate a contextual reply based on star rating."""
    first_name = reviewer_name.split()[0] if reviewer_name else "there"

    if star_rating == "FIVE":
        return (
            f"Thank you so much for the wonderful review, {first_name}! "
            f"We're thrilled you enjoyed your visit to our {store_name} store. "
            f"We look forward to seeing you again soon!"
        )
    elif star_rating == "FOUR":
        return (
            f"Thanks for the great feedback, {first_name}! "
            f"We're glad you had a good experience at {store_name}. "
            f"If there's anything we can do to make it even better next time, "
            f"don't hesitate to let us know. See you soon!"
        )
    elif star_rating == "THREE":
        return (
            f"Hi {first_name}, thank you for taking the time to share your feedback. "
            f"We appreciate your honest review and would love to improve your experience. "
            f"If you have any specific suggestions, please feel free to reach out to us "
            f"at 1300 526 397. We hope to welcome you back to {store_name} soon."
        )
    else:  # TWO or ONE
        return (
            f"Hi {first_name}, we're sorry to hear about your experience at our "
            f"{store_name} store. This isn't the standard we aim for, and we take "
            f"your feedback seriously. We'd really appreciate the chance to make "
            f"things right — please call us at 1300 526 397 or visit us in-store "
            f"so we can address your concerns directly. Thank you for letting us know."
        )


def send_telegram(message: str) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        logger.warning("Telegram not configured, skipping notification")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.error("Telegram send failed: %s", e)


def run(site_id: str, dry_run: bool = False) -> dict[str, Any]:
    # Load credentials
    site_env = SITES_DIR / site_id / ".env"
    _load_env(site_env)
    _load_env(SOCIAL_AGENT_ENV)

    site_json = SITES_DIR / site_id / "site.json"
    config = json.loads(site_json.read_text())
    gbp_config = config.get("gbp", {})
    account_id = gbp_config.get("account_id", "")
    location_ids = gbp_config.get("location_ids", [])
    location_labels = gbp_config.get("location_labels", {})

    if not account_id or not location_ids:
        raise ValueError(f"No GBP config in {site_id}/site.json")

    token = _get_access_token()

    total_replied = 0
    total_new = 0
    alerts: list[str] = []

    for loc_id in location_ids:
        store_name = location_labels.get(loc_id, loc_id.split("/")[-1])

        # Paginate through all reviews
        page_token = None
        while True:
            url = f"{GBP_API_BASE}/{account_id}/{loc_id}/reviews?pageSize=50"
            if page_token:
                url += f"&pageToken={page_token}"
            data = _gbp_request(url, token)

            for review in data.get("reviews", []):
                if review.get("reviewReply"):
                    continue  # already replied

                total_new += 1
                star_rating = review.get("starRating", "STAR_RATING_UNSPECIFIED")
                reviewer = review.get("reviewer", {}).get("displayName", "Customer")
                comment = review.get("comment", "")
                review_name = review["name"]

                reply_text = generate_reply(star_rating, reviewer, store_name, comment)

                stars_map = {"FIVE": "5", "FOUR": "4", "THREE": "3", "TWO": "2", "ONE": "1"}
                stars_str = stars_map.get(star_rating, "?")

                if dry_run:
                    logger.info("[DRY RUN] %s | %s⭐ %s | Reply: %s",
                                store_name, stars_str, reviewer, reply_text[:60])
                else:
                    reply_url = f"{GBP_API_BASE}/{review_name}/reply"
                    try:
                        _gbp_request(reply_url, token, "PUT", {"comment": reply_text})
                        total_replied += 1
                        logger.info("Replied: %s | %s⭐ | %s", store_name, stars_str, reviewer)
                    except urllib.error.HTTPError as e:
                        logger.error("Reply failed for %s: %s", reviewer, e)

                # Alert for low ratings
                if star_rating in ("ONE", "TWO", "THREE"):
                    alerts.append(
                        f"⚠️ <b>{store_name}</b>: {stars_str}⭐ from {reviewer}\n"
                        f"<i>{comment[:150]}</i>"
                    )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    # Send Telegram summary
    if total_new > 0 and not dry_run:
        parts = [f"📋 <b>GBP Review Auto-Reply</b>: {total_replied} new replies"]
        if alerts:
            parts.append("\n".join(alerts))
        send_telegram("\n\n".join(parts))
    elif total_new == 0:
        logger.info("No unreplied reviews found.")

    return {
        "new_reviews": total_new,
        "replied": total_replied,
        "low_rating_alerts": len(alerts),
        "dry_run": dry_run,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Auto-reply to GBP reviews")
    parser.add_argument("--site", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(args.site, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
