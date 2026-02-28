#!/usr/bin/env python3
"""Quick test of seo_discover functionality"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from seo_discovery import discover_from_topic
from config import get_settings

print("=" * 60)
print("Testing SEO Discovery (Topic Mode)")
print("=" * 60)

settings = get_settings()

print(f"\n✅ OpenAI API Key: {'✓ configured' if settings.openai_api_key else '✗ missing'}")
print(f"✅ Model: {settings.openai_model}")

print("\n🔍 Discovering content opportunities for 'chocolate'...")

try:
    suggestions = discover_from_topic(
        topic_area="chocolate",
        openai_api_key=settings.openai_api_key,
        model=settings.openai_model
    )

    print(f"\n✅ Generated {len(suggestions)} suggestions:\n")

    for i, sugg in enumerate(suggestions, 1):
        print(f"{i}. {sugg['title']}")
        print(f"   🔑 Keyword: {sugg['primary_keyword']}")
        print(f"   📈 Traffic Potential: {sugg['traffic_potential']}/10")
        print(f"   💡 Reason: {sugg['reason']}\n")

    print("=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
