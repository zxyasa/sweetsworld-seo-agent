"""Main entry point for SEO automation agent MVP."""
import csv
import sys
from pathlib import Path
from typing import List, Dict, Optional

from config import get_settings
from wp_client import WPClient
from content_generator import generate_article_html
from telegram_notify import send_telegram

# Optional imports for AI and GSC features
try:
    from openai_generator import OpenAIGenerator
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from gsc_client import GSCClient
    GSC_AVAILABLE = True
except ImportError:
    GSC_AVAILABLE = False


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

    # Initialize OpenAI generator if enabled
    openai_generator = None
    if settings.use_ai_generation:
        if not OPENAI_AVAILABLE:
            print("⚠️  OpenAI requested but openai package not installed")
            print("   Run: pip install openai")
            print("   Falling back to template generation\n")
        elif not settings.openai_api_key:
            print("⚠️  USE_AI_GENERATION=true but OPENAI_API_KEY not set")
            print("   Falling back to template generation\n")
        else:
            try:
                openai_generator = OpenAIGenerator(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model
                )
                print(f"✅ OpenAI enabled (model: {settings.openai_model})\n")
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI: {e}")
                print("   Falling back to template generation\n")

    # Initialize GSC client if enabled
    gsc_client = None
    if settings.use_gsc_data:
        if not GSC_AVAILABLE:
            print("⚠️  GSC requested but google-api-python-client not installed")
            print("   Run: pip install google-api-python-client google-auth-oauthlib")
            print("   Continuing without GSC data\n")
        elif not settings.gsc_property_url:
            print("⚠️  USE_GSC_DATA=true but GSC_PROPERTY_URL not set")
            print("   Continuing without GSC data\n")
        else:
            try:
                gsc_client = GSCClient(
                    property_url=settings.gsc_property_url,
                    credentials_file=settings.gsc_credentials_file
                )
                print(f"✅ Google Search Console enabled\n")
            except Exception as e:
                print(f"⚠️  Failed to initialize GSC: {e}")
                print("   Continuing without GSC data\n")

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
            # Get GSC data if available
            gsc_data = None
            if gsc_client and topic.get('primary_keyword'):
                try:
                    gsc_data = gsc_client.get_related_keywords(
                        primary_keyword=topic['primary_keyword'],
                        days=90,
                        max_results=15
                    )
                    if gsc_data['related_keywords']:
                        print(f"  📊 Found {len(gsc_data['related_keywords'])} related keywords from GSC")
                except Exception as e:
                    print(f"  ⚠️  GSC lookup failed: {e}")

            # Generate HTML content
            html_content = generate_article_html(
                topic_dict=topic,
                use_ai=bool(openai_generator),
                openai_generator=openai_generator,
                gsc_data=gsc_data
            )
            generation_mode = "AI-powered" if openai_generator else "template"
            print(f"  ✅ Generated HTML content ({len(html_content)} characters, {generation_mode})")

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
