"""OpenAI-powered content generation for SEO articles."""
from typing import Dict, Optional, List
from openai import OpenAI
import re
import html


class OpenAIGenerator:
    """Generate SEO-optimized content using OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_article_html(
        self,
        topic_dict: Dict[str, str],
        gsc_data: Optional[Dict] = None
    ) -> str:
        title = topic_dict.get("title", "")
        keyword = topic_dict.get("primary_keyword", "")
        category = topic_dict.get("category_hint", "")

        internal_links = self._extract_internal_links(gsc_data)
        prompt = self._build_prompt(title, keyword, category, gsc_data, internal_links)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert SEO content writer for sweetsworld.com.au, "
                            "an Australian candy and confectionery e-commerce store. "
                            "Write engaging, informative, and SEO-optimized articles in HTML format. "
                            "IMPORTANT: ALL content MUST be written in English language using Australian English spelling and style. "
                            "NEVER write in Chinese or any other language - only English."
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

            raw_content = response.choices[0].message.content or ""
            html_content = self._sanitize_model_output(raw_content)
            html_content = self._ensure_basic_seo_blocks(html_content, title, keyword)

            if not html_content.lstrip().lower().startswith("<article"):
                html_content = f'<article class="seo-content">\n{html_content}\n</article>'

            html_content = self._ensure_internal_links(html_content, internal_links)
            return html_content

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    def _build_prompt(
        self,
        title: str,
        keyword: str,
        category: str,
        gsc_data: Optional[Dict] = None,
        internal_links: Optional[List[str]] = None,
    ) -> str:
        prompt = f"""Write a comprehensive SEO-optimized article for sweetsworld.com.au with the following specifications:

**CRITICAL REQUIREMENT: Write ONLY in English language. NO Chinese or other languages allowed.**

**Article Details:**
- Title: {title}
- Primary Keyword: {keyword}
- Category: {category}
- Target Audience: Australian consumers and businesses buying candy/confectionery
- Language: English (Australian English spelling and style)

**Content Requirements:**
1. Use <h1> for the main title
2. Include 4-6 <h2> section headings
3. Add 2-3 <h3> subsections where appropriate
4. Write 1200-1500 words total
5. Naturally incorporate the primary keyword throughout (aim for 1-2% density)
6. Include bullet points (<ul>/<li>) for key features or tips
7. Add a CTA (Call-to-Action) section with internal links
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

        keyword_lc = (keyword or "").lower()
        seasonal_terms = ["valentine", "christmas", "easter", "halloween", "new year", "black friday", "boxing day"]
        seasonal_intent = any(term in keyword_lc for term in seasonal_terms)

        if not seasonal_intent:
            prompt += (
                "\n\n**Topic Guardrail (MANDATORY):**\n"
                "- Stay tightly focused on the provided title/primary keyword.\n"
                "- Do NOT introduce seasonal campaigns (e.g., Valentine's Day, Christmas, Easter) unless explicitly present in the title/keyword.\n"
                "- If examples are needed, use generic evergreen buying scenarios."
            )

        if gsc_data and gsc_data.get("related_keywords"):
            keywords_list = ", ".join(gsc_data["related_keywords"][:10])
            prompt += f"\n\n**Related Keywords to Include (from Search Console):**\n{keywords_list}"

        if internal_links:
            links_block = "\n".join(f"- {u}" for u in internal_links[:6])
            prompt += (
                "\n\n**MANDATORY Internal Links (theme-related):**\n"
                f"{links_block}\n"
                "Use at least 3 of these links in the body/CTA with meaningful anchor text."
            )

        prompt += "\n\n**Output Format:**\nReturn ONLY the HTML content (starting with <h1> or <article>), no markdown, no explanations."
        return prompt

    def _sanitize_model_output(self, text: str) -> str:
        """Strip markdown code fences and normalize model output to raw HTML."""
        out = str(text or "").strip()
        out = re.sub(r"^```(?:html)?\s*", "", out, flags=re.IGNORECASE)
        out = re.sub(r"\s*```$", "", out, flags=re.IGNORECASE)

        if out.lower().startswith("html\n"):
            out = out[5:]
        elif out.lower() == "html":
            out = ""

        return out.strip()

    def _ensure_basic_seo_blocks(self, html_content: str, title: str, keyword: str) -> str:
        """Add minimal SEO blocks when model output misses key sections."""
        out = html_content

        if "<h1" not in out.lower() and title:
            out = f"<h1>{html.escape(title)}</h1>\n" + out

        if 'class="intro"' not in out and keyword:
            intro = (
                f'<p class="intro">This guide helps you understand {html.escape(keyword)} '
                'with practical buying tips for Australian shoppers.</p>\n'
            )
            out = intro + out

        if "<h2" not in out.lower():
            out += "\n<h2>Key Buying Considerations</h2>\n<p>Compare quality, pricing, delivery, and supplier trust signals before purchasing.</p>\n"

        if "faq" not in out.lower():
            out += (
                "\n<h2>FAQ</h2>\n"
                "<h3>How do I choose the best option?</h3>\n"
                "<p>Match product type, budget, and delivery timeline to your use case.</p>\n"
            )

        if "last updated" not in out.lower():
            out += "\n<p class=\"last-updated\"><em>Last updated: 2026</em></p>\n"

        return out

    def _extract_internal_links(self, gsc_data: Optional[Dict]) -> List[str]:
        links: List[str] = []

        if gsc_data:
            for url in gsc_data.get("internal_link_urls", []) or []:
                if isinstance(url, str) and url.strip():
                    links.append(url.strip())

            for row in gsc_data.get("top_pages", []) or []:
                url = row.get("url") if isinstance(row, dict) else None
                if isinstance(url, str) and url.strip():
                    links.append(url.strip())

        if not links:
            links = [
                "https://sweetsworld.com.au/candy/",
                "https://sweetsworld.com.au/wholesale-candy-australia/",
                "https://sweetsworld.com.au/candy/sour-lollies/",
            ]

        deduped: List[str] = []
        seen = set()
        for u in links:
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        return deduped[:8]

    def _count_internal_links(self, html_text: str) -> int:
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE)
        count = 0
        for href in hrefs:
            if href.startswith("/") or "sweetsworld.com.au" in href:
                count += 1
        return count

    def _ensure_internal_links(self, html_text: str, internal_links: List[str]) -> str:
        if self._count_internal_links(html_text) >= 3:
            return html_text

        links_html = "\n".join(
            f'  <li><a href="{u}">{u}</a></li>' for u in internal_links[:3]
        )
        block = (
            "\n<section class=\"related-internal-links\">\n"
            "  <h2>Related Internal Resources</h2>\n"
            "  <ul>\n"
            f"{links_html}\n"
            "  </ul>\n"
            "</section>\n"
        )

        if "</article>" in html_text:
            return html_text.replace("</article>", block + "</article>")
        return html_text + block
