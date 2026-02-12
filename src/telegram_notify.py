"""Telegram notification module for sending updates."""
import requests


def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    """
    Send a message via Telegram Bot API.

    Args:
        bot_token: Telegram bot token (from BotFather)
        chat_id: Telegram chat ID to send message to
        text: Message text to send (supports Markdown)

    Raises:
        requests.HTTPError: If the API request fails
    """
    if not bot_token or not chat_id:
        print("⚠️  Telegram credentials not configured, skipping notification")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    response = requests.post(url, json=payload, timeout=10)

    # Raise exception for 4xx/5xx status codes
    response.raise_for_status()

    print("✅ Telegram notification sent successfully")
