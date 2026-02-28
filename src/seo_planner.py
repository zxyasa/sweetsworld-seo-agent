"""
SEO article planner.
Generate English SEO article suggestions from a short topic description.
"""
from typing import Dict, List
import json
import re


def _contains_cjk(text: str) -> bool:
    """Detect CJK characters so we can enforce English-only output."""
    if not text:
        return False
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:80] or "untitled-guide"


def _clean_topic(text: str) -> str:
    cleaned = re.sub(r"[<>]", " ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "candy"


def _fallback_suggestions(topic: str) -> List[Dict[str, str]]:
    base_topic = _clean_topic(topic)
    base_slug = _slugify(base_topic)
    return [
        {
            "title": f"Ultimate Guide to {base_topic} in Australia (2026)",
            "slug": f"{base_slug}-australia-guide-2026",
            "primary_keyword": f"{base_topic.lower()} australia",
            "category_hint": "Buying Guide",
        },
        {
            "title": f"Best {base_topic} Brands in Australia (2026 Comparison)",
            "slug": f"best-{base_slug}-brands-australia-2026",
            "primary_keyword": f"best {base_topic.lower()} brands australia",
            "category_hint": "Brand Comparison",
        },
        {
            "title": f"Healthy Alternatives to {base_topic}: Australia 2026",
            "slug": f"healthy-{base_slug}-alternatives-australia-2026",
            "primary_keyword": f"healthy {base_topic.lower()} alternatives",
            "category_hint": "Health & Alternatives",
        },
    ]


def _is_english_suggestion(suggestion: Dict[str, str]) -> bool:
    fields = [
        suggestion.get("title", ""),
        suggestion.get("slug", ""),
        suggestion.get("primary_keyword", ""),
        suggestion.get("category_hint", ""),
    ]
    return not any(_contains_cjk(str(v)) for v in fields)


def plan_seo_article(topic: str, openai_api_key: str, model: str = "gpt-4o") -> List[Dict[str, str]]:
    """
    Generate 3 SEO article suggestions from a topic description.

    Args:
        topic: Topic description, e.g. "Australian Chocolate"
        openai_api_key: OpenAI API key
        model: OpenAI model

    Returns:
        List of 3 suggestions, each with: title, slug, primary_keyword, category_hint
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)

        prompt = f"""You are the SEO content strategist for sweetsworld.com.au, an Australian candy and confectionery ecommerce site.

The user wants SEO article ideas for this topic:
"{topic}"

Generate exactly 3 suggestions from different angles. Each suggestion must include:
1. title - catchy SEO title including year 2026
2. slug - URL-friendly lowercase slug (English only)
3. primary_keyword - primary SEO keyword for Australian search intent
4. category_hint - short English category label

IMPORTANT:
- ALL FIELDS MUST BE IN ENGLISH.
- Do not use Chinese or any non-English language in title/category/keyword.
- Keep slugs lowercase with hyphens only.

Return strict JSON in this shape:
{{
  "suggestions": [
    {{
      "title": "...",
      "slug": "...",
      "primary_keyword": "...",
      "category_hint": "..."
    }}
  ]
}}

Requirements:
- Include "2026" in each title.
- Keep each suggestion distinct in intent (e.g. buying guide, brand comparison, healthy alternatives).
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert SEO strategist. Output English only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        raw_suggestions = result.get("suggestions", [])
        suggestions: List[Dict[str, str]] = []
        for s in raw_suggestions:
            if not isinstance(s, dict):
                continue
            title = str(s.get("title", "")).strip()
            primary_keyword = str(s.get("primary_keyword", "")).strip()
            category_hint = str(s.get("category_hint", "")).strip()
            slug = _slugify(str(s.get("slug", "")).strip() or title)
            if title and primary_keyword:
                suggestions.append(
                    {
                        "title": title,
                        "slug": slug,
                        "primary_keyword": primary_keyword,
                        "category_hint": category_hint or "Products",
                    }
                )

        # Enforce English-only outputs. If model returns non-English text, fallback.
        if len(suggestions) < 3 or not all(_is_english_suggestion(s) for s in suggestions[:3]):
            return _fallback_suggestions(topic)

        return suggestions[:3]

    except Exception:
        return _fallback_suggestions(topic)


def format_suggestions_for_display(suggestions: List[Dict[str, str]]) -> str:
    """
    将建议格式化为易读的文本

    Args:
        suggestions: 建议列表

    Returns:
        格式化的文本
    """
    output = "📋 **SEO 文章建议（3个选项）**\n\n"

    for i, suggestion in enumerate(suggestions, 1):
        output += f"**选项 {i}：**\n"
        output += f"📝 标题: {suggestion['title']}\n"
        output += f"🔗 Slug: {suggestion['slug']}\n"
        output += f"🔑 关键词: {suggestion['primary_keyword']}\n"
        output += f"📁 分类: {suggestion['category_hint']}\n\n"

    output += "💡 **使用方法：**\n"
    output += "回复数字 1、2 或 3 来选择一个建议，或者说\"全部创建\"来创建所有3篇文章。"

    return output
