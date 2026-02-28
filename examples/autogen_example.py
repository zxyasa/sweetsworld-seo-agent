"""
Example: Using SEO Agent with Microsoft AutoGen

This example shows how to integrate the SEO automation agent
with AutoGen for multi-agent content generation workflows.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from autogen_integration import create_seo_article, batch_create_articles, AUTOGEN_TOOLS


# ============================================================================
# Example 1: Direct Function Call (Simple)
# ============================================================================

def example_direct_call():
    """Direct function call - simplest way to use from AutoGen."""
    print("📝 Example 1: Direct Function Call\n")

    result = create_seo_article(
        title="Ultimate Guide to Australian Chocolate 2026",
        slug="australian-chocolate-guide-2026",
        primary_keyword="australian chocolate",
        category_hint="Chocolate",
        use_ai=True,
        use_gsc=False
    )

    if result["status"] == "success":
        print(f"✅ Success!")
        print(f"   Post ID: {result['post_id']}")
        print(f"   Link: {result['post_link']}")
        print(f"   Mode: {result['mode']}")
        print(f"   Size: {result['characters']} characters")
    else:
        print(f"❌ Error: {result['message']}")


# ============================================================================
# Example 2: Batch Processing
# ============================================================================

def example_batch_processing():
    """Batch create multiple articles at once."""
    print("\n📚 Example 2: Batch Processing\n")

    topics = [
        {
            "title": "Top 10 Chocolate Brands in Australia 2026",
            "slug": "top-chocolate-brands-australia",
            "primary_keyword": "chocolate brands australia",
            "category_hint": "Chocolate"
        },
        {
            "title": "Vegan Candy Options: Complete Guide",
            "slug": "vegan-candy-guide",
            "primary_keyword": "vegan candy australia",
            "category_hint": "Vegan Products"
        },
        {
            "title": "Sugar-Free Lollies for Diabetics",
            "slug": "sugar-free-lollies-diabetics",
            "primary_keyword": "sugar free lollies",
            "category_hint": "Healthy Candy"
        }
    ]

    results = batch_create_articles(topics)

    print(f"Created {len(results)} articles:")
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{i}. {status_icon} {result.get('message', 'Unknown')}")
        if result["status"] == "success":
            print(f"   {result['post_link']}")


# ============================================================================
# Example 3: AutoGen Agent with Function Calling
# ============================================================================

def example_autogen_agent():
    """
    Example using AutoGen ConversableAgent with function calling.

    NOTE: Requires autogen-agentchat package:
    pip install autogen-agentchat
    """
    print("\n🤖 Example 3: AutoGen Agent with Function Calling\n")

    try:
        from autogen import ConversableAgent

        # Create an assistant agent with SEO tools
        assistant = ConversableAgent(
            name="SEO_Content_Agent",
            system_message=(
                "You are an expert SEO content strategist for sweetsworld.com.au, "
                "an Australian candy and confectionery e-commerce store. "
                "Use the create_seo_article function to generate SEO-optimized articles."
            ),
            llm_config={
                "config_list": [{"model": "gpt-4o", "api_key": "your-openai-key"}],
                "tools": AUTOGEN_TOOLS,
            },
        )

        # User proxy agent
        user_proxy = ConversableAgent(
            name="User",
            llm_config=False,
            is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", ""),
            human_input_mode="NEVER",
        )

        # Register the functions
        assistant.register_for_llm(
            name="create_seo_article",
            description="Create a SEO-optimized article"
        )(create_seo_article)

        assistant.register_for_llm(
            name="batch_create_articles",
            description="Batch create multiple articles"
        )(batch_create_articles)

        user_proxy.register_for_execution(name="create_seo_article")(create_seo_article)
        user_proxy.register_for_execution(name="batch_create_articles")(batch_create_articles)

        # Start conversation
        user_proxy.initiate_chat(
            assistant,
            message=(
                "Create a SEO article about 'Candy Gift Boxes for Corporate Events' "
                "targeting the keyword 'corporate candy gifts australia'"
            )
        )

        print("\n✅ AutoGen agent example completed!")

    except ImportError:
        print("⚠️  AutoGen not installed. Install with: pip install autogen-agentchat")
        print("    This example shows the integration pattern.")


# ============================================================================
# Example 4: Multi-Agent Workflow
# ============================================================================

def example_multi_agent_workflow():
    """
    Example: Multi-agent workflow with AutoGen
    - Research Agent: Finds trending keywords
    - Content Agent: Creates articles
    - QA Agent: Reviews quality
    """
    print("\n🔄 Example 4: Multi-Agent Workflow Pattern\n")
    print("""
    Pattern for AutoGen multi-agent workflow:

    1. Research Agent → Identifies trending candy keywords
       ↓
    2. Strategy Agent → Creates content plan with titles/keywords
       ↓
    3. Content Agent → Calls create_seo_article() for each topic
       ↓
    4. QA Agent → Reviews generated drafts
       ↓
    5. Publish Agent → Approves and publishes

    Each agent can call create_seo_article() independently!
    """)


# ============================================================================
# Example 5: Scheduled AutoGen Agent
# ============================================================================

def example_scheduled_agent():
    """Example: Scheduled content generation with AutoGen."""
    print("\n⏰ Example 5: Scheduled Content Generation\n")
    print("""
    Setup cron job to run AutoGen agent daily:

    # crontab -e
    0 9 * * * cd /path/to/sweetsworld-seo-agent && python examples/autogen_daily.py

    AutoGen agent can:
    1. Analyze Search Console trends
    2. Identify content gaps
    3. Generate new articles automatically
    4. Send Telegram notifications
    """)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SEO Agent × AutoGen Integration Examples")
    print("=" * 70)

    # Run examples
    # example_direct_call()
    # example_batch_processing()
    # example_autogen_agent()
    example_multi_agent_workflow()
    example_scheduled_agent()

    print("\n" + "=" * 70)
    print("💡 Tips:")
    print("   - Use direct calls for simple tasks")
    print("   - Use batch processing for multiple articles")
    print("   - Use AutoGen agents for intelligent workflows")
    print("=" * 70)
