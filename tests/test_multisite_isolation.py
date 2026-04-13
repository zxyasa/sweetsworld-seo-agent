"""Tests for multi-site data isolation.

Covers:
- ContentContaminationError raised when foreign domain appears in HTML
- Clean HTML passes without error
- SiteContext loads correct per-site paths
- catalog_loader returns only the site's own items
- validate_topic uses ctx.default_category_hint
"""
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sites_registry import assert_no_cross_site_contamination, ContentContaminationError, SitesRegistry  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_registry(base_urls: list[str]) -> SitesRegistry:
    """Return a SitesRegistry mock whose get_all_base_urls() returns given list."""
    reg = MagicMock(spec=SitesRegistry)
    reg.get_all_base_urls.return_value = base_urls
    return reg


# ---------------------------------------------------------------------------
# assert_no_cross_site_contamination
# ---------------------------------------------------------------------------

class TestContaminationGuard:
    SWEETSWORLD = "https://sweetsworld.com.au"
    NEWCASTLEHUB = "https://newcastlehub.info"
    ALL_URLS = [SWEETSWORLD, NEWCASTLEHUB]

    def test_clean_html_passes(self):
        html = "<p>Buy lollies online today!</p>"
        reg = _make_registry(self.ALL_URLS)
        # Should not raise
        assert_no_cross_site_contamination(html, "sweetsworld", self.SWEETSWORLD, reg)

    def test_own_domain_in_html_passes(self):
        html = f'<a href="{self.SWEETSWORLD}/candy/">View Candy</a>'
        reg = _make_registry(self.ALL_URLS)
        assert_no_cross_site_contamination(html, "sweetsworld", self.SWEETSWORLD, reg)

    def test_foreign_domain_raises(self):
        html = f'<a href="{self.NEWCASTLEHUB}/services/">See Services</a>'
        reg = _make_registry(self.ALL_URLS)
        with pytest.raises(ContentContaminationError) as exc_info:
            assert_no_cross_site_contamination(html, "sweetsworld", self.SWEETSWORLD, reg)
        assert "newcastlehub.info" in str(exc_info.value)
        assert "sweetsworld" in str(exc_info.value)

    def test_foreign_domain_in_newcastlehub_content_raises(self):
        html = f'<p>Visit {self.SWEETSWORLD}/wholesale/ for bulk orders.</p>'
        reg = _make_registry(self.ALL_URLS)
        with pytest.raises(ContentContaminationError) as exc_info:
            assert_no_cross_site_contamination(html, "newcastlehub", self.NEWCASTLEHUB, reg)
        assert "sweetsworld.com.au" in str(exc_info.value)

    def test_plain_domain_without_scheme_does_not_trigger(self):
        """Guard only blocks full https:// URLs, not bare domain mentions."""
        html = "<p>Unlike newcastlehub.info, we focus on candy.</p>"
        reg = _make_registry(self.ALL_URLS)
        # Should not raise — no https:// prefix
        assert_no_cross_site_contamination(html, "sweetsworld", self.SWEETSWORLD, reg)

    def test_multiple_foreign_domains_all_reported(self):
        third = "https://example.com"
        html = f'<a href="{self.NEWCASTLEHUB}/">A</a> <a href="{third}/">B</a>'
        reg = _make_registry(self.ALL_URLS + [third])
        with pytest.raises(ContentContaminationError) as exc_info:
            assert_no_cross_site_contamination(html, "sweetsworld", self.SWEETSWORLD, reg)
        msg = str(exc_info.value)
        assert "newcastlehub.info" in msg
        assert "example.com" in msg

    def test_empty_html_passes(self):
        reg = _make_registry(self.ALL_URLS)
        assert_no_cross_site_contamination("", "sweetsworld", self.SWEETSWORLD, reg)

    def test_single_site_registry_always_passes(self):
        """When only one site is registered, no foreign URLs exist."""
        html = f'<a href="{self.SWEETSWORLD}/candy/">candy</a>'
        reg = _make_registry([self.SWEETSWORLD])
        assert_no_cross_site_contamination(html, "sweetsworld", self.SWEETSWORLD, reg)


# ---------------------------------------------------------------------------
# validate_topic default_category_hint
# ---------------------------------------------------------------------------

class TestValidateTopicCategoryHint:

    def _run(self, topic: dict, ctx=None) -> dict:
        from run_mvp import validate_topic
        validate_topic(topic, ctx=ctx)
        return topic

    def test_no_ctx_defaults_to_confectionery(self):
        t = {"slug": "test", "title": "Test", "primary_keyword": "test", "category_hint": ""}
        result = self._run(t, ctx=None)
        assert result["category_hint"] == "Confectionery"

    def test_ctx_default_category_hint_used(self):
        ctx = MagicMock()
        ctx.default_category_hint = "Digital Marketing"
        t = {"slug": "test", "title": "Test", "primary_keyword": "test", "category_hint": ""}
        result = self._run(t, ctx=ctx)
        assert result["category_hint"] == "Digital Marketing"

    def test_explicit_category_hint_not_overwritten(self):
        ctx = MagicMock()
        ctx.default_category_hint = "Digital Marketing"
        t = {"slug": "test", "title": "Test", "primary_keyword": "test", "category_hint": "SEO"}
        result = self._run(t, ctx=ctx)
        assert result["category_hint"] == "SEO"

    def test_ctx_missing_attribute_falls_back_to_confectionery(self):
        ctx = MagicMock(spec=[])  # no attributes at all
        t = {"slug": "test", "title": "Test", "primary_keyword": "test", "category_hint": ""}
        result = self._run(t, ctx=ctx)
        assert result["category_hint"] == "Confectionery"


# ---------------------------------------------------------------------------
# catalog_loader isolation
# ---------------------------------------------------------------------------

class TestCatalogLoaderIsolation:

    def _make_ctx(self, tmpdir: Path, catalog_type: str, items: list) -> MagicMock:
        if catalog_type == "products":
            fname = "products.json"
            data = {"products": items}
        else:
            fname = "services.json"
            data = {"services": items}
        catalog_path = tmpdir / fname
        catalog_path.write_text(json.dumps(data))
        ctx = MagicMock()
        ctx.catalog_type = catalog_type
        ctx.catalog_path = catalog_path
        return ctx

    def test_products_catalog_loads_correctly(self, tmp_path):
        items = [
            {"product_name": "Sour Worms", "category": "Candy", "categories": ["Candy"],
             "tags": ["sour"], "url": "https://sw.com/sour-worms/", "slug": "sour-worms",
             "image_url": None, "is_in_stock": True, "description": "Sour worms"},
        ]
        ctx = self._make_ctx(tmp_path, "products", items)
        from catalog_loader import load_catalog
        result = load_catalog(ctx)
        assert len(result) == 1
        assert result[0].name == "Sour Worms"
        assert result[0].is_available is True

    def test_services_catalog_loads_correctly(self, tmp_path):
        items = [
            {"service_name": "Local SEO Newcastle", "category": "SEO", "categories": ["SEO"],
             "tags": ["seo"], "url": "https://newcastlehub.info/services/", "slug": "local-seo",
             "image_url": None, "is_active": True, "description": "Local SEO"},
        ]
        ctx = self._make_ctx(tmp_path, "services", items)
        from catalog_loader import load_catalog
        result = load_catalog(ctx)
        assert len(result) == 1
        assert result[0].name == "Local SEO Newcastle"
        assert result[0].is_available is True

    def test_inactive_services_excluded_by_default(self, tmp_path):
        items = [
            {"service_name": "Active", "category": "SEO", "categories": [], "tags": [],
             "url": "https://x.com/a/", "slug": "a", "image_url": None,
             "is_active": True, "description": ""},
            {"service_name": "Inactive", "category": "SEO", "categories": [], "tags": [],
             "url": "https://x.com/b/", "slug": "b", "image_url": None,
             "is_active": False, "description": ""},
        ]
        ctx = self._make_ctx(tmp_path, "services", items)
        from catalog_loader import load_catalog, select_for_topic
        all_items = load_catalog(ctx)
        selected = select_for_topic(all_items, keywords=["seo"], available_only=True)
        assert all(i.is_available for i in selected)
        assert not any(i.name == "Inactive" for i in selected)
