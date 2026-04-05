"""
SEO 关键词发现和主题建议
从 Google Search Console 数据中发现高潜力关键词并生成文章建议
"""
import logging
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def discover_opportunities(
    gsc_client,
    openai_api_key: str,
    model: str = "gpt-4o",
    days: int = 90,
    min_impressions: int = 50,
    site_description: str = "sweetsworld.com.au, an Australian candy and confectionery e-commerce website",
) -> Dict:
    """
    从 GSC 数据中发现内容机会

    Args:
        gsc_client: GSC客户端实例
        openai_api_key: OpenAI API密钥
        model: OpenAI模型
        days: 分析天数
        min_impressions: 最小展示次数

    Returns:
        包含机会关键词和文章建议的字典
    """
    try:
        from openai import OpenAI

        # 1. 从 GSC 获取高展示、低点击的关键词（高潜力）
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['query'],
            'rowLimit': 100,  # 获取前100个查询
        }

        response = gsc_client.service.searchanalytics().query(
            siteUrl=gsc_client.property_url,
            body=request
        ).execute()

        # 2. 分析数据，找到机会关键词
        opportunities = []

        if 'rows' in response:
            for row in response['rows']:
                query = row['keys'][0]
                impressions = row.get('impressions', 0)
                clicks = row.get('clicks', 0)
                ctr = row.get('ctr', 0)
                position = row.get('position', 100)

                # 筛选条件：高展示、低点击、排名在10-30之间（有优化空间）
                if (impressions >= min_impressions and
                    ctr < 0.05 and  # CTR < 5%
                    10 <= position <= 30):  # 排名在第2-3页

                    opportunities.append({
                        'keyword': query,
                        'impressions': impressions,
                        'clicks': clicks,
                        'ctr': round(ctr * 100, 2),
                        'position': round(position, 1),
                        'potential_score': impressions * (1 - ctr)  # 潜力分数
                    })

        # 按潜力分数排序
        opportunities.sort(key=lambda x: x['potential_score'], reverse=True)
        top_opportunities = opportunities[:10]  # 取前10个

        if not top_opportunities:
            return {
                'status': 'no_data',
                'message': '未找到足够的 GSC 数据，建议手动输入关键词',
                'opportunities': [],
                'suggestions': []
            }

        # 3. 用 OpenAI 生成文章主题建议
        client = OpenAI(api_key=openai_api_key)

        # 构建关键词列表
        keyword_list = "\n".join([
            f"- {opp['keyword']} (展示: {opp['impressions']}, 点击率: {opp['ctr']}%, 排名: {opp['position']})"
            for opp in top_opportunities
        ])

        prompt = f"""You are an SEO content strategist for {site_description}.

I've discovered the following **high-potential keywords** from Google Search Console:
These keywords have high impressions but low CTR, ranking on pages 2-3, indicating significant optimization opportunity.

{keyword_list}

Based on this data, generate **5 article topic suggestions** to help us improve rankings and traffic for these keywords.

IMPORTANT: All content MUST be in ENGLISH (for Australian market).

Each suggestion must include:
1. title - Engaging title (include 2026)
2. slug - URL-friendly slug
3. primary_keyword - Choose the most relevant keyword from the list above
4. category_hint - Article category
5. traffic_potential - Traffic potential score (1-10)
6. reason - Why this topic is valuable (brief explanation)

Return in JSON format:
{{
  "suggestions": [
    {{
      "title": "...",
      "slug": "...",
      "primary_keyword": "...",
      "category_hint": "...",
      "traffic_potential": 8,
      "reason": "..."
    }}
  ]
}}

Requirements:
- Prioritize keywords with high impressions and high potential scores
- Target user search intent (buying guides, comparisons, reviews, etc.)
- Content must fit Australian market needs
- Each suggestion should target a different keyword, no repetition
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional SEO content strategist specializing in discovering content opportunities from data. Always respond in English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        suggestions = result.get("suggestions", [])

        return {
            'status': 'success',
            'opportunities': top_opportunities,
            'suggestions': suggestions[:5],  # 返回前5个建议
            'analysis_period': f'{days} 天',
            'total_keywords_analyzed': len(opportunities)
        }

    except Exception as e:
        logger.exception("Failed to discover SEO opportunities from GSC data")
        return {
            'status': 'error',
            'message': f'发现失败: {str(e)}',
            'opportunities': [],
            'suggestions': []
        }


def discover_from_topic(
    topic_area: str,
    openai_api_key: str,
    model: str = "gpt-4o",
    site_description: str = "sweetsworld.com.au, an Australian candy and confectionery e-commerce website",
) -> List[Dict]:
    """
    基于主题领域生成关键词和文章建议（无需 GSC 数据）

    Args:
        topic_area: 主题领域，例如 "chocolate", "candy", "lollies"
        openai_api_key: OpenAI API密钥
        model: OpenAI模型

    Returns:
        文章建议列表
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)

        prompt = f"""You are an SEO content strategist for {site_description}.

The user wants to create content in this area:
"{topic_area}"

Based on Australian market search trends and user needs, generate **5 high-traffic potential article topic suggestions**.

IMPORTANT: All content MUST be in ENGLISH (for Australian market).

Each suggestion must include:
1. title - Engaging title (include 2026)
2. slug - URL-friendly slug
3. primary_keyword - Primary keyword (for Australian market)
4. category_hint - Article category
5. traffic_potential - Traffic potential score (1-10)
6. reason - Why this topic has high traffic potential

Consider:
- Seasonal trends (Christmas, Easter, etc.)
- Australian preferences (local brands, preferences)
- User search intent (buying, comparison, health choices, etc.)
- Competition level (choose medium-competition long-tail keywords)

Return in JSON format:
{{
  "suggestions": [
    {{
      "title": "...",
      "slug": "...",
      "primary_keyword": "...",
      "category_hint": "...",
      "traffic_potential": 8,
      "reason": "..."
    }}
  ]
}}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional SEO content strategist specializing in discovering high-traffic potential content topics. Always respond in English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result.get("suggestions", [])

    except Exception as e:
        # 返回基础建议
        return [
            {
                "title": f"Best {topic_area.title()} in Australia 2026",
                "slug": f"best-{topic_area.lower()}-australia-2026",
                "primary_keyword": f"{topic_area.lower()} australia",
                "category_hint": "Reviews",
                "traffic_potential": 7,
                "reason": "购买指南类内容通常有较高搜索量"
            }
        ]


def format_discovery_results(data: Dict) -> str:
    """
    格式化发现结果为易读文本

    Args:
        data: discover_opportunities 返回的数据

    Returns:
        格式化的文本
    """
    if data['status'] == 'no_data':
        return f"⚠️ {data['message']}"

    if data['status'] == 'error':
        return f"❌ {data['message']}"

    output = "🔍 **SEO 内容机会发现报告**\n\n"
    output += f"📊 分析周期: {data['analysis_period']}\n"
    output += f"🔎 关键词总数: {data['total_keywords_analyzed']}\n\n"

    # 高潜力关键词
    if data['opportunities']:
        output += "📈 **高潜力关键词（前5个）：**\n\n"
        for i, opp in enumerate(data['opportunities'][:5], 1):
            output += f"{i}. **{opp['keyword']}**\n"
            output += f"   展示: {opp['impressions']} | 点击率: {opp['ctr']}% | 排名: {opp['position']}\n"
            output += f"   💡 潜力分数: {int(opp['potential_score'])}\n\n"

    # 文章建议
    if data['suggestions']:
        output += "✍️ **推荐文章主题（基于数据）：**\n\n"
        for i, sugg in enumerate(data['suggestions'], 1):
            output += f"**{i}. {sugg['title']}**\n"
            output += f"   🔑 关键词: {sugg['primary_keyword']}\n"
            output += f"   🔗 Slug: {sugg['slug']}\n"
            output += f"   📁 分类: {sugg['category_hint']}\n"
            output += f"   📈 流量潜力: {'⭐' * sugg['traffic_potential']}/10\n"
            output += f"   💡 原因: {sugg['reason']}\n\n"

    output += "🚀 **下一步：**\n"
    output += "- 选择一个主题，用 'seo_plan' 生成详细参数\n"
    output += "- 或直接说 '创建第 X 个主题的文章'"

    return output


def format_topic_suggestions(suggestions: List[Dict], topic_area: str) -> str:
    """
    格式化主题建议为易读文本

    Args:
        suggestions: 建议列表
        topic_area: 主题领域

    Returns:
        格式化的文本
    """
    output = f"💡 **{topic_area.title()} 领域高流量文章建议**\n\n"

    for i, sugg in enumerate(suggestions, 1):
        output += f"**{i}. {sugg['title']}**\n"
        output += f"   🔑 关键词: {sugg['primary_keyword']}\n"
        output += f"   🔗 Slug: {sugg['slug']}\n"
        output += f"   📁 分类: {sugg['category_hint']}\n"
        output += f"   📈 流量潜力: {'⭐' * sugg['traffic_potential']}/10\n"
        output += f"   💡 原因: {sugg['reason']}\n\n"

    output += "🚀 **下一步：**\n"
    output += "- 选择一个主题直接创建文章\n"
    output += "- 或用 'seo_plan' 查看更多角度"

    return output
