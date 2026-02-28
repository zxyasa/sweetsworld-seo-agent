"""AutoGen integration for SEO automation agent."""
import re
import sys
from pathlib import Path
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from wp_client import WPClient
from content_generator import generate_article_html
from openai_generator import OpenAIGenerator
from gsc_client import GSCClient


def _normalize_tokens(text: str) -> List[str]:
    text = (text or "").lower()
    tokens = re.split(r"[^a-z0-9]+", text)
    return [t for t in tokens if len(t) >= 3]


def _choose_best_category(categories: List[Dict], title: str, keyword: str, category_hint: str) -> Dict:
    """Auto-select best WordPress category based on title/keyword/hint token overlap."""
    if not categories:
        return {"id": None, "name": "Uncategorized", "score": 0}

    query_tokens = set(_normalize_tokens(" ".join([title, keyword, category_hint])))
    best = {"id": None, "name": "Uncategorized", "score": -1}

    for cat in categories:
        name = str(cat.get("name", ""))
        slug = str(cat.get("slug", ""))
        cat_tokens = set(_normalize_tokens(name + " " + slug))

        score = len(query_tokens.intersection(cat_tokens))

        # Slight preference for non-default categories when tied
        if name.lower() not in {"uncategorized", "general"}:
            score += 0.1

        if score > best["score"]:
            best = {"id": cat.get("id"), "name": name, "score": score}

    return best


def create_seo_article(
    title: str,
    slug: str,
    primary_keyword: str,
    category_hint: str = "Products",
    use_ai: bool = True,
    use_gsc: bool = False,
    force_create: bool = False,
) -> Dict[str, str]:
    """
    Create a SEO-optimized article draft in WordPress.

    Returns:
        Dict containing status/details and optional similar post check results.
    """
    try:
        settings = get_settings()

        wp_client = WPClient(
            base_url=settings.wp_base_url,
            username=settings.wp_username,
            app_password=settings.wp_app_password,
        )

        if not wp_client.test_connection():
            return {
                "status": "error",
                "message": "Failed to connect to WordPress API",
                "post_link": None,
                "post_id": None,
            }

        # Auto category selection from existing WP categories
        wp_categories = wp_client.get_categories()
        best_category = _choose_best_category(wp_categories, title, primary_keyword, category_hint)

        # Similar post detection before creation
        similar_query = f"{title} {primary_keyword}".strip()
        similar_posts = wp_client.find_similar_posts(similar_query, max_results=5)
        if similar_posts and not force_create:
            return {
                "status": "similar_found",
                "message": "Found similar posts; confirmation required",
                "similar_posts": similar_posts,
                "selected_category": best_category,
            }

        openai_generator = None
        if use_ai and settings.use_ai_generation and settings.openai_api_key:
            openai_generator = OpenAIGenerator(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )

        gsc_data = None
        if use_gsc and settings.use_gsc_data:
            try:
                gsc_client = GSCClient(
                    property_url=settings.gsc_property_url,
                    credentials_file=settings.gsc_credentials_file,
                )
                gsc_data = gsc_client.get_related_keywords(
                    primary_keyword=primary_keyword,
                    days=90,
                    max_results=15,
                )

                try:
                    top_pages = gsc_client.get_top_pages(days=90, max_results=20)
                    gsc_data["top_pages"] = top_pages

                    tokens = [t for t in primary_keyword.lower().replace("-", " ").split() if len(t) >= 3]
                    related_urls = []
                    for row in top_pages:
                        url = row.get("url", "")
                        if not url:
                            continue
                        lower_url = url.lower()
                        if any(tok in lower_url for tok in tokens):
                            related_urls.append(url)

                    gsc_data["internal_link_urls"] = related_urls[:8]
                except Exception as e:
                    print(f"Warning: GSC top pages lookup failed: {e}")
            except Exception as e:
                print(f"Warning: GSC lookup failed: {e}")

        topic_dict = {
            "title": title,
            "slug": slug,
            "primary_keyword": primary_keyword,
            "category_hint": category_hint,
        }

        html_content = generate_article_html(
            topic_dict=topic_dict,
            use_ai=bool(openai_generator),
            openai_generator=openai_generator,
            gsc_data=gsc_data,
        )

        result = wp_client.create_post_draft(
            title=title,
            slug=slug,
            html=html_content,
            excerpt=f"Comprehensive guide about {primary_keyword}",
            category_id=best_category.get("id"),
        )

        post_link = result.get("link") or f"{settings.wp_base_url}/?p={result['id']}"

        return {
            "status": "success",
            "post_link": post_link,
            "post_id": result["id"],
            "message": f"Successfully created draft: {title}",
            "characters": len(html_content),
            "mode": "AI-powered" if openai_generator else "template",
            "selected_category": best_category,
            "similar_posts": similar_posts,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating article: {str(e)}",
            "post_link": None,
            "post_id": None,
        }


def batch_create_articles(topics: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Batch create multiple SEO articles."""
    results = []

    for topic in topics:
        result = create_seo_article(
            title=topic.get("title", ""),
            slug=topic.get("slug", ""),
            primary_keyword=topic.get("primary_keyword", ""),
            category_hint=topic.get("category_hint", "Products"),
            use_ai=topic.get("use_ai", True),
            use_gsc=topic.get("use_gsc", False),
        )
        results.append(result)

    return results


AUTOGEN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_seo_article",
            "description": "Create a SEO-optimized article draft in WordPress for sweetsworld.com.au.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Article title"},
                    "slug": {"type": "string", "description": "URL-friendly slug"},
                    "primary_keyword": {"type": "string", "description": "Main SEO keyword"},
                    "category_hint": {"type": "string", "description": "Category hint", "default": "Products"},
                    "use_ai": {"type": "boolean", "description": "Use OpenAI", "default": True},
                    "use_gsc": {"type": "boolean", "description": "Use GSC", "default": False},
                    "force_create": {"type": "boolean", "description": "Ignore similar-post check", "default": False},
                },
                "required": ["title", "slug", "primary_keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "batch_create_articles",
            "description": "Batch create multiple SEO articles at once",
            "parameters": {
                "type": "object",
                "properties": {
                    "topics": {
                        "type": "array",
                        "description": "List of article topics to create",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "slug": {"type": "string"},
                                "primary_keyword": {"type": "string"},
                                "category_hint": {"type": "string"},
                            },
                            "required": ["title", "slug", "primary_keyword"],
                        },
                    }
                },
                "required": ["topics"],
            },
        },
    },
]
