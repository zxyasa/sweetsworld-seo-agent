"""Content generation module for creating SEO-optimized article HTML."""
from typing import Dict, Optional


def generate_article_html(
    topic_dict: Dict[str, str],
    use_ai: bool = False,
    openai_generator: Optional[any] = None,
    gsc_data: Optional[Dict] = None
) -> str:
    """
    Generate SEO-optimized HTML article content.

    Supports both template-based and AI-powered generation.

    Args:
        topic_dict: Dictionary containing topic information with keys:
                   - title: Article title
                   - primary_keyword: Main SEO keyword
                   - category_hint: Category/topic hint
        use_ai: Whether to use OpenAI for generation (default: False)
        openai_generator: OpenAIGenerator instance (required if use_ai=True)
        gsc_data: Optional Google Search Console keyword data

    Returns:
        str: Complete HTML content for the article
    """
    # Use AI generation if enabled
    if use_ai and openai_generator:
        try:
            return openai_generator.generate_article_html(topic_dict, gsc_data)
        except Exception as e:
            print(f"⚠️  AI generation failed, falling back to template: {str(e)}")
            # Fall back to template generation

    # Use template generation
    return generate_template_html(topic_dict)


def generate_template_html(topic_dict: Dict[str, str]) -> str:
    """
    Generate SEO-optimized HTML using template.

    Args:
        topic_dict: Dictionary containing topic information

    Returns:
        str: Complete HTML content for the article
    """
    title = topic_dict.get("title", "Untitled")
    keyword = topic_dict.get("primary_keyword", "")
    category = topic_dict.get("category_hint", "Products")

    html = f"""
<article class="seo-content">
    <h1>{title}</h1>

    <p class="intro">
        Looking for the best {keyword}? This comprehensive guide covers everything you need to know
        about finding quality products, comparing suppliers, and making informed purchasing decisions in 2026.
    </p>

    <h2>Why Choose Australian Suppliers for {category}?</h2>
    <p>
        Australian suppliers offer exceptional quality, reliable shipping, and local customer support.
        When you buy from local suppliers, you benefit from faster delivery times, better communication,
        and products that meet Australian standards.
    </p>
    <p>
        Our {keyword} selection features premium brands and competitive wholesale pricing for both
        businesses and individual customers.
    </p>

    <h2>Top Features to Look For</h2>
    <ul>
        <li><strong>Quality Certification:</strong> Ensure products meet Australian food safety standards</li>
        <li><strong>Variety:</strong> Wide range of flavours and options to suit all preferences</li>
        <li><strong>Bulk Options:</strong> Competitive pricing for wholesale and bulk orders</li>
        <li><strong>Fresh Stock:</strong> Regular inventory turnover guarantees freshness</li>
        <li><strong>Fast Shipping:</strong> Quick delivery across Australia</li>
    </ul>

    <h2>How to Order and Save Money</h2>
    <p>
        Shopping smart means understanding your options. For bulk orders, wholesale pricing can
        significantly reduce your per-unit costs. Many Australian suppliers offer tiered pricing
        that rewards larger purchases.
    </p>
    <p>
        Consider joining loyalty programs or subscribing to newsletters for exclusive discounts
        and early access to new products.
    </p>

    <div class="cta-box" style="background: #f8f9fa; padding: 24px; margin: 32px 0; border-left: 4px solid #ff6b6b; border-radius: 4px;">
        <h3 style="margin-top: 0;">🍬 Ready to Order?</h3>
        <p>
            Explore our full range of premium confectionery products. Whether you're looking for
            wholesale quantities or personal treats, we've got you covered.
        </p>
        <p style="margin-bottom: 0;">
            <a href="/candy/" style="color: #ff6b6b; font-weight: bold;">Browse All Candy</a> |
            <a href="/wholesale-candy-australia/" style="color: #ff6b6b; font-weight: bold;">Wholesale Options</a> |
            <a href="/candy/sour-lollies/" style="color: #ff6b6b; font-weight: bold;">Sour Lollies Collection</a>
        </p>
    </div>

    <h2>Frequently Asked Questions</h2>

    <div class="faq-section">
        <h3>What is the minimum order quantity?</h3>
        <p>
            Most products have no minimum order requirement for retail customers. Wholesale customers
            can enjoy bulk discounts starting from orders of $200 or more.
        </p>

        <h3>How long does shipping take?</h3>
        <p>
            Standard shipping across Australia typically takes 3-7 business days. Express shipping
            options are available for faster delivery to major cities.
        </p>

        <h3>Are the products suitable for special dietary requirements?</h3>
        <p>
            We clearly label all allergen information and dietary specifications. Many products are
            available in vegan, gluten-free, and sugar-free options.
        </p>

        <h3>Can I return products if I'm not satisfied?</h3>
        <p>
            Yes, we offer a satisfaction guarantee. Unopened products can be returned within 30 days
            of purchase for a full refund or exchange.
        </p>

        <h3>Do you offer custom packaging or branding?</h3>
        <p>
            For wholesale orders above certain thresholds, we can discuss custom packaging solutions
            and branded options. Contact our sales team for more information.
        </p>
    </div>

    <p class="last-updated" style="font-size: 0.9em; color: #666; margin-top: 48px;">
        <em>Last updated: 2026</em>
    </p>
</article>
"""

    return html.strip()
