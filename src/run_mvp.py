"""Main entry point for SEO automation agent MVP."""
import csv
import sys
from pathlib import Path
from typing import List, Dict

from config import get_settings
from wp_client import WPClient
from content_generator import generate_article_html
from telegram_notify import send_telegram


def read_topics(csv_path: Path) -> List[Dict[str, str]]:
    """
    Read topics from CSV file.

    Args:
        csv_path: Path to topics CSV file

    Returns:
        List of topic dictionaries
    """
    topics = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            topics.append(row)
    return topics


def validate_topic(topic: Dict[str, str]) -> bool:
    """
    Validate that topic has required fields.

    Args:
        topic: Topic dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    slug = topic.get('slug', '').strip()
    title = topic.get('title', '').strip()

    if not slug or not title:
        print(f"⚠️  Skipping invalid topic: missing slug or title - {topic}")
        return False

    return True


def main():
    """Main execution function."""
    print("🚀 SEO Automation Agent MVP - Starting...\n")

    # Load configuration
    try:
        settings = get_settings()
        print(f"✅ Configuration loaded")
        print(f"   WordPress: {settings.wp_base_url}")
        print(f"   Username: {settings.wp_username}\n")
    except RuntimeError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Initialize WordPress client
    wp_client = WPClient(
        base_url=settings.wp_base_url,
        username=settings.wp_username,
        app_password=settings.wp_app_password,
    )

    # Test WordPress connection
    print("🔍 Testing WordPress connection...")
    if not wp_client.test_connection():
        print("❌ Cannot connect to WordPress REST API!")
        print("   Please check your configuration and network connection.")
        print(f"   Try accessing: {settings.wp_base_url}/wp-json/wp/v2/posts")
        sys.exit(1)
    print("✅ WordPress connection successful\n")

    # Read topics from CSV
    topics_csv_path = Path(__file__).parent.parent / "topics.csv"

    if not topics_csv_path.exists():
        print(f"❌ Topics file not found: {topics_csv_path}")
        sys.exit(1)

    topics = read_topics(topics_csv_path)
    print(f"📋 Found {len(topics)} topics to process\n")

    if not topics:
        print("⚠️  No topics to process")
        sys.exit(0)

    # Process each topic
    created_drafts = []

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] Processing: {topic.get('title', 'Unknown')}")

        # Validate topic
        if not validate_topic(topic):
            continue

        try:
            # Generate HTML content
            html_content = generate_article_html(topic)
            print(f"  ✅ Generated HTML content ({len(html_content)} characters)")

            # Create draft post in WordPress
            result = wp_client.create_post_draft(
                title=topic['title'],
                slug=topic['slug'],
                html=html_content,
                excerpt=f"Comprehensive guide about {topic.get('primary_keyword', '')}",
            )

            # Get post link
            post_link = result.get('link') or f"{settings.wp_base_url}/?p={result['id']}"

            print(f"  ✅ Created draft: {post_link}")

            created_drafts.append({
                'title': topic['title'],
                'link': post_link,
            })

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

        print()

    # Send Telegram notification
    if created_drafts:
        print(f"\n📤 Sending Telegram notification...")

        message_lines = ["✅ *SEO Drafts Created:*\n"]
        for draft in created_drafts:
            message_lines.append(f"• {draft['title']}")
            message_lines.append(f"  {draft['link']}\n")

        message = "\n".join(message_lines)

        try:
            send_telegram(
                bot_token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
                text=message,
            )
        except Exception as e:
            print(f"⚠️  Telegram notification failed: {e}")

    # Summary
    print(f"\n{'='*50}")
    print(f"✅ Done. Created drafts: {len(created_drafts)}/{len(topics)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
