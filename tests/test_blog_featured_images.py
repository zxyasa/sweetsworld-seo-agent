from __future__ import annotations

import json
from pathlib import Path

import requests

from product_selector import (
    load_product_catalog,
    pick_featured_image_url,
    select_products_for_topic,
)
from content_generator import build_product_image_gallery
from run_mvp import _upsert_product_image_gallery
from wp_client import WPClient


def test_load_product_catalog_preserves_image_url(tmp_path: Path) -> None:
    payload = [
        {
            "product_name": "Jolly Rancher Hard Candy",
            "url": "https://sweetsworld.com.au/product/jolly-rancher-hard-candy/",
            "category": "American Candy",
            "description": "Hard candy",
            "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
        }
    ]
    catalog_path = tmp_path / "products.json"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")

    products = load_product_catalog(catalog_path)

    assert len(products) == 1
    assert products[0]["image_url"] == "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg"


def test_select_products_for_topic_keeps_image_url() -> None:
    product_catalog = [
        {
            "product_name": "Jolly Rancher Hard Candy",
            "category": "American Candy",
            "description": "Hard candy",
            "price": "$4.99",
            "url": "https://sweetsworld.com.au/product/jolly-rancher-hard-candy/",
            "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
            "_category_text": "american candy",
            "_name_text": "jolly rancher hard candy",
            "_normalized_name_text": "jolly rancher hard candy",
            "_description_text": "hard candy",
            "_normalized_category_text": "american candy",
            "_normalized_description_text": "hard candy",
        }
    ]
    topic = {
        "title": "Jolly Rancher Australia",
        "primary_keyword": "jolly rancher australia",
        "category_hint": "American Candy",
        "page_type": "blog_post",
    }

    selected = select_products_for_topic(topic, product_catalog, max_items=1)

    assert len(selected) == 1
    assert selected[0]["image_url"] == "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg"


def test_pick_featured_image_url_returns_first_non_empty() -> None:
    selected_products = [
        {"product_name": "A", "image_url": ""},
        {"product_name": "B", "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/b.jpg"},
        {"product_name": "C", "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/c.jpg"},
    ]

    assert pick_featured_image_url(selected_products) == "https://sweetsworld.com.au/wp-content/uploads/2024/05/b.jpg"


def test_find_media_by_source_url_matches_existing_site_media(monkeypatch) -> None:
    client = WPClient("https://sweetsworld.com.au", "user", "pass")

    class DummyResponse:
        status_code = 200

        def json(self):
            return [
                {
                    "id": 123,
                    "source_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
                }
            ]

    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append(params)
        return DummyResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    media = client.find_media_by_source_url(
        "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg"
    )

    assert media is not None
    assert media["id"] == 123
    assert calls


def test_build_product_image_gallery_renders_site_images() -> None:
    html = build_product_image_gallery(
        [
            {
                "product_name": "Jolly Rancher Hard Candy",
                "url": "https://sweetsworld.com.au/product/jolly-rancher-hard-candy/",
                "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
                "price": "$4.99",
            }
        ]
    )

    assert "seo-product-gallery" in html
    assert "<aside" in html
    assert "seo-product-card" in html
    assert "<img" in html
    assert "jolly-rancher.jpg" in html
    assert "Jolly Rancher Hard Candy" in html
    assert "You may also want to buy" in html
    assert "Quick product links" not in html
    assert "<h2" not in html
    assert "<h3" not in html
    assert '<span style="display: block; font-size: 0.98rem;' in html


def test_upsert_product_image_gallery_adds_gallery_after_intro() -> None:
    html_content = (
        '<article><p class="intro">Intro copy.</p>'
        '<h2>Heading 1</h2><p>Body one.</p>'
        '<h2>Heading 2</h2><p>Body two.</p>'
        '<h2>Heading 3</h2><p>Body three.</p></article>'
    )
    selected_products = [
        {
            "product_name": "Jolly Rancher Hard Candy",
            "url": "https://sweetsworld.com.au/product/jolly-rancher-hard-candy/",
            "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
        }
    ]

    updated = _upsert_product_image_gallery(html_content, selected_products)

    assert 'seo-product-gallery' in updated
    assert updated.index('<h2>Heading 1</h2>') < updated.index('seo-product-gallery')
    assert updated.index('seo-product-gallery') < updated.index('<h2>Heading 3</h2>')


def test_upsert_product_image_gallery_skips_when_html_already_has_images() -> None:
    html_content = '<article><p class="intro">Intro copy.</p><img src="/existing.jpg" alt="Existing" /></article>'
    selected_products = [
        {
            "product_name": "Jolly Rancher Hard Candy",
            "url": "https://sweetsworld.com.au/product/jolly-rancher-hard-candy/",
            "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
        }
    ]

    updated = _upsert_product_image_gallery(html_content, selected_products)

    assert updated == html_content


def test_upsert_product_image_gallery_replaces_existing_gallery() -> None:
    html_content = (
        '<article><p class="intro">Intro copy.</p><h2>Heading 1</h2><p>Body one.</p>'
        '<aside class="seo-product-gallery"><p>Old gallery</p></aside>'
        '<h2>Heading 2</h2><p>Body two.</p><h2>Heading 3</h2></article>'
    )
    selected_products = [
        {
            "product_name": "Jolly Rancher Hard Candy",
            "url": "https://sweetsworld.com.au/product/jolly-rancher-hard-candy/",
            "image_url": "https://sweetsworld.com.au/wp-content/uploads/2024/05/jolly-rancher.jpg",
        }
    ]

    updated = _upsert_product_image_gallery(html_content, selected_products)

    assert "Old gallery" not in updated
    assert updated.count('seo-product-gallery') == 1
    assert 'seo-product-card' in updated
    assert updated.index('<h2>Heading 1</h2>') < updated.index('seo-product-gallery')
    assert updated.index('seo-product-gallery') < updated.index('<h2>Heading 3</h2>')
