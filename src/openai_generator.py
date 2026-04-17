"""OpenAI-powered content generation for SEO articles."""
from typing import Dict, Optional, List
from openai import OpenAI
from pathlib import Path
import re
import html


def _load_design_prompt() -> str:
    """Read Agent Prompt Guide from DESIGN.md section 11."""
    design_md = Path(__file__).parent.parent / "design-system" / "DESIGN.md"
    if not design_md.exists():
        return ""
    try:
        content = design_md.read_text()
        m = re.search(
            r'## 11\. Agent Prompt Guide.*?(\*\*SYSTEM:.*?purchase\.)',
            content,
            re.DOTALL,
        )
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


_DESIGN_PROMPT: str = _load_design_prompt()


class OpenAIGenerator:
    """Generate SEO-optimized content using OpenAI API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        site_description: str = "sweetsworld.com.au, an Australian candy and confectionery e-commerce store",
        base_url: str = "",
        collection_urls: Optional[Dict] = None,
        prompt_config: Optional[Dict] = None,
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.site_description = site_description
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.collection_urls = collection_urls or {}
        self.prompt_config = prompt_config or {}

    def generate_article_html(
        self,
        topic_dict: Dict[str, str],
        gsc_data: Optional[Dict] = None,
        content_brief: Optional[Dict] = None,
    ) -> str:
        title = topic_dict.get("title", "")
        keyword = topic_dict.get("primary_keyword", "")
        category = topic_dict.get("category_hint", "")

        internal_links = self._extract_internal_links(gsc_data)
        selected_products = (content_brief or {}).get("selected_products", []) or []
        prompt = self._build_prompt(title, keyword, category, gsc_data, internal_links, selected_products)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            ((_DESIGN_PROMPT + "\n\n") if _DESIGN_PROMPT else "")
                            + f"You are an expert SEO content writer for {self.site_description}. "
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
            _faq_items = (content_brief or {}).get("faq_items", []) or []
            html_content = self._sanitize_model_output(raw_content, faq_items=_faq_items)
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
        selected_products: Optional[List[Dict]] = None,
    ) -> str:
        pc = self.prompt_config  # shorthand

        target_audience = pc.get(
            "target_audience",
            "Australian consumers and businesses buying candy/confectionery",
        )
        language_instruction = pc.get(
            "language_instruction",
            "English (Australian English spelling and style)",
        )
        word_count = pc.get("word_count", "1200-1500")
        tone_style = pc.get(
            "tone_style",
            "- Professional but friendly and approachable\n"
            "- Australian English (colour, flavour, etc.)\n"
            "- Focus on practical advice and buying guidance\n"
            "- Emphasize quality, value, and local Australian context",
        )

        prompt = f"""Write a comprehensive SEO-optimized article for {self.site_description} with the following specifications:

**CRITICAL REQUIREMENT: Write ONLY in English language. NO Chinese or other languages allowed.**

**Article Details:**
- Title: {title}
- Primary Keyword: {keyword}
- Category: {category}
- Target Audience: {target_audience}
- Language: {language_instruction}

**Content Requirements:**
1. Do NOT use <h1> — WordPress renders H1 from the post title automatically. Start headings at <h2>.
2. Include 4-6 <h2> section headings
3. Add 2-3 <h3> subsections where appropriate
4. Write {word_count} words total
5. Naturally incorporate the primary keyword throughout (aim for 1-2% density)
6. Include bullet points (<ul>/<li>) for key features or tips
7. Add a CTA (Call-to-Action) section with internal links
8. Include an FAQ section with at least 5 relevant questions and answers
9. Add "Last updated: 2026" at the end

**Tone & Style:**
{tone_style}

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

        if selected_products:
            product_lines = []
            for p in selected_products[:8]:
                name = p.get("product_name", p.get("name", ""))
                url = p.get("url", "")
                if name and url:
                    product_lines.append(f'- <a href="{url}">{name}</a>')
                elif name:
                    product_lines.append(f"- {name} (mention by name only, do NOT add a link)")
            if product_lines:
                prompt += (
                    "\n\n**Available Products to Mention (MANDATORY rules):**\n"
                    + "\n".join(product_lines)
                    + "\n\nRules:\n"
                    "1. You MAY mention these products naturally in the article body.\n"
                    "2. Products with a URL: use EXACTLY that URL as the href — do not modify it.\n"
                    "3. Products marked 'mention by name only': include the name as plain text, NO hyperlink.\n"
                    "4. Do NOT invent or guess any other product URLs. If a product is not listed above, mention it as plain text only."
                )
        else:
            prompt += (
                "\n\n**Product Link Rule (MANDATORY):**\n"
                "Do NOT include hyperlinks to any specific products. "
                "You may mention product types or brand names as plain text, but never add a <a href> to a product page unless the URL is explicitly provided above."
            )

        if internal_links:
            links_block = "\n".join(f"- {u}" for u in internal_links[:6])
            prompt += (
                "\n\n**MANDATORY Internal Links (theme-related):**\n"
                f"{links_block}\n"
                "Use at least 3 of these links in the body/CTA with meaningful anchor text."
            )

        if pc.get("extra_instructions"):
            prompt += f"\n\n**Site-Specific Instructions (MANDATORY):**\n{pc['extra_instructions']}"

        prompt += "\n\n**Output Format:**\nReturn ONLY the HTML content (starting with <h2> or <article>, NOT <h1>), no markdown, no explanations."
        return prompt

    def _sanitize_model_output(self, text: str, faq_items: list | None = None) -> str:
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

        # Do NOT inject <h1> — WordPress renders H1 from the post title.
        # If the AI incorrectly added an <h1>, strip it to avoid double H1.
        out = re.sub(r"<h1[^>]*>.*?</h1>", "", out, flags=re.IGNORECASE | re.DOTALL).strip()

        if 'class="intro"' not in out and keyword:
            # Use a brief site name (first segment before comma or parenthesis)
            _short_site = re.split(r"[,(]", self.site_description)[0].strip()
            intro = (
                f'<p class="intro">This guide covers {html.escape(keyword)} '
                f'— practical insights from {html.escape(_short_site)}.</p>\n'
            )
            out = intro + out

        if "<h2" not in out.lower():
            _short_site = re.split(r"[,(]", self.site_description)[0].strip()
            out += f"\n<h2>Key Considerations</h2>\n<p>Explore more resources on {html.escape(keyword)} at {html.escape(_short_site)}.</p>\n"

        # Check for FAQ in visible HTML only (exclude JSON-LD <script> blocks)
        _visible_html = re.sub(r"<script[^>]*>.*?</script>", "", out, flags=re.IGNORECASE | re.DOTALL)
        _has_faq = "faq" in _visible_html.lower() or "frequently asked" in _visible_html.lower()
        if not _has_faq and faq_items:
            faq_html = "\n<h2>FAQ</h2>\n"
            for item in faq_items[:3]:
                q = item.get("question", "")
                a = item.get("answer", "")
                if q and a:
                    faq_html += f"<h3>{html.escape(q)}</h3>\n<p>{html.escape(a)}</p>\n"
            out += faq_html

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
            if self.collection_urls:
                # Use site-specific collection URLs (e.g. /services/ for newcastlehub)
                links = list(self.collection_urls.values())[:3]
            else:
                try:
                    from config import get_settings, get_site_collection_urls
                    _settings_url = get_settings().wp_base_url.rstrip("/")
                    # Only inject sweetsworld fallback links when the generator is for sweetsworld
                    _generator_url = self.base_url or _settings_url
                    if _generator_url == _settings_url:
                        _u = get_site_collection_urls(_settings_url)
                        links = [_u["candy"], _u["wholesale"], _u["sour_lollies"]]
                except Exception:
                    links = []

        deduped: List[str] = []
        seen = set()
        for u in links:
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        return deduped[:8]

    def _count_internal_links(self, html_text: str) -> int:
        try:
            from urllib.parse import urlparse
            from config import get_settings
            _host = urlparse(get_settings().wp_base_url).netloc
        except Exception:
            _host = ""
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE)
        count = 0
        for href in hrefs:
            if href.startswith("/") or (_host and _host in href):
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
