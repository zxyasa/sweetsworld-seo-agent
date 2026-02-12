"""OpenAI-powered content generation for SEO articles."""
from typing import Dict, Optional
from openai import OpenAI


class OpenAIGenerator:
    """Generate SEO-optimized content using OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI generator.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_article_html(
        self,
        topic_dict: Dict[str, str],
        gsc_data: Optional[Dict] = None
    ) -> str:
        """
        Generate SEO-optimized HTML article using OpenAI.

        Args:
            topic_dict: Topic information with keys:
                       - title: Article title
                       - primary_keyword: Main SEO keyword
                       - category_hint: Category/topic hint
                       - slug: URL slug
            gsc_data: Optional Google Search Console data with keywords

        Returns:
            str: Complete HTML content for the article
        """
        title = topic_dict.get("title", "")
        keyword = topic_dict.get("primary_keyword", "")
        category = topic_dict.get("category_hint", "")
        slug = topic_dict.get("slug", "")

        # Build prompt
        prompt = self._build_prompt(title, keyword, category, gsc_data)

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert SEO content writer for sweetsworld.com.au, "
                            "an Australian candy and confectionery e-commerce store. "
                            "Write engaging, informative, and SEO-optimized articles in HTML format."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=3000,
            )

            # Extract HTML content
            html_content = response.choices[0].message.content.strip()

            # Ensure content is wrapped in article tag if not already
            if not html_content.startswith("<article"):
                html_content = f'<article class="seo-content">\n{html_content}\n</article>'

            return html_content

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    def _build_prompt(
        self,
        title: str,
        keyword: str,
        category: str,
        gsc_data: Optional[Dict] = None
    ) -> str:
        """
        Build comprehensive prompt for OpenAI.

        Args:
            title: Article title
            keyword: Primary keyword
            category: Category hint
            gsc_data: Optional GSC data

        Returns:
            str: Formatted prompt
        """
        prompt = f"""Write a comprehensive SEO-optimized article for sweetsworld.com.au with the following specifications:

**Article Details:**
- Title: {title}
- Primary Keyword: {keyword}
- Category: {category}
- Target Audience: Australian consumers and businesses buying candy/confectionery

**Content Requirements:**
1. Use <h1> for the main title
2. Include 4-6 <h2> section headings
3. Add 2-3 <h3> subsections where appropriate
4. Write 1200-1500 words total
5. Naturally incorporate the primary keyword throughout (aim for 1-2% density)
6. Include bullet points (<ul>/<li>) for key features or tips
7. Add a CTA (Call-to-Action) section with internal links to:
   - /candy/ (main candy collection)
   - /wholesale-candy-australia/ (wholesale section)
   - /candy/sour-lollies/ (sour lollies collection)
8. Include an FAQ section with at least 5 relevant questions and answers
9. Add "Last updated: 2026" at the end

**Tone & Style:**
- Professional but friendly and approachable
- Australian English (colour, flavour, etc.)
- Focus on practical advice and buying guidance
- Emphasize quality, value, and local Australian context

**SEO Best Practices:**
- Use semantic HTML5 tags
- Include relevant long-tail keywords naturally
- Write compelling meta-worthy content in the intro
- Use descriptive subheadings that include keywords"""

        # Add GSC data if available
        if gsc_data and gsc_data.get("related_keywords"):
            keywords_list = ", ".join(gsc_data["related_keywords"][:10])
            prompt += f"\n\n**Related Keywords to Include (from Search Console):**\n{keywords_list}"

        prompt += "\n\n**Output Format:**\nReturn ONLY the HTML content (starting with <h1> or <article>), no markdown, no explanations."

        return prompt
