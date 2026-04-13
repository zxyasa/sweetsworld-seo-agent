"""Unit tests for page_type_strategies.

Covers: LandingPageStrategy, FAQPageStrategy, CategoryPageStrategy, OccasionPageStrategy.
Each test exercises one behaviour of one method.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from page_type_strategies.base import BriefContext, QualityGate  # noqa: E402
from page_type_strategies.landing_page import LandingPageStrategy  # noqa: E402
from page_type_strategies.faq_page import FAQPageStrategy  # noqa: E402
from page_type_strategies.category_page import CategoryPageStrategy  # noqa: E402
from page_type_strategies.occasion_page import OccasionPageStrategy  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _ctx(**overrides) -> BriefContext:
    """Return a minimal BriefContext suitable for all strategy tests."""
    defaults = dict(
        slug="test-slug",
        title="Test Candy Page",
        primary_keyword="test candy Australia",
        category_hint="Gummy Bears",
        cluster="gummies",
        page_type="landing_page",
        selected_products=[
            {"product_name": "Haribo Gold Bears 1kg"},
            {"product_name": "Trolli Sour Worms 500g"},
        ],
    )
    defaults.update(overrides)
    return BriefContext(**defaults)


# ---------------------------------------------------------------------------
# LandingPageStrategy
# ---------------------------------------------------------------------------

class TestLandingPageStrategy:
    @pytest.fixture(autouse=True)
    def strategy(self):
        self.s = LandingPageStrategy()
        self.ctx = _ctx(page_type="landing_page")

    # build_intro
    def test_build_intro_returns_non_empty_string(self):
        result = self.s.build_intro(self.ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_intro_max_240_chars(self):
        result = self.s.build_intro(self.ctx)
        assert len(result) <= 240

    def test_build_intro_contains_australia(self):
        result = self.s.build_intro(self.ctx)
        assert "Australia" in result

    # build_sections
    def test_build_sections_returns_list(self):
        result = self.s.build_sections(self.ctx)
        assert isinstance(result, list)

    def test_build_sections_has_at_least_one_item(self):
        result = self.s.build_sections(self.ctx)
        assert len(result) >= 1

    def test_build_sections_each_item_has_heading(self):
        for section in self.s.build_sections(self.ctx):
            assert "heading" in section
            assert isinstance(section["heading"], str)
            assert section["heading"]

    def test_build_sections_each_item_has_paragraphs(self):
        for section in self.s.build_sections(self.ctx):
            assert "paragraphs" in section
            assert isinstance(section["paragraphs"], list)

    def test_build_sections_each_item_has_bullets(self):
        for section in self.s.build_sections(self.ctx):
            assert "bullets" in section

    def test_build_sections_uses_product_names_as_bullets(self):
        all_bullets = []
        for section in self.s.build_sections(self.ctx):
            all_bullets.extend(section.get("bullets", []))
        joined = " ".join(all_bullets)
        assert any(name in joined for name in ["Haribo Gold Bears 1kg", "Trolli Sour Worms 500g"])

    # build_faq_items
    def test_build_faq_items_returns_list(self):
        result = self.s.build_faq_items(self.ctx)
        assert isinstance(result, list)

    def test_build_faq_items_returns_at_least_one_item(self):
        result = self.s.build_faq_items(self.ctx)
        assert len(result) >= 1

    def test_build_faq_items_each_item_has_question_and_answer(self):
        for item in self.s.build_faq_items(self.ctx):
            assert "question" in item
            assert "answer" in item
            assert item["question"]
            assert item["answer"]

    def test_build_faq_items_landing_page_returns_3(self):
        result = self.s.build_faq_items(self.ctx)
        assert len(result) == 3

    # build_cta
    def test_build_cta_returns_dict(self):
        result = self.s.build_cta(self.ctx)
        assert isinstance(result, dict)

    def test_build_cta_has_text_key(self):
        result = self.s.build_cta(self.ctx)
        assert "button_text" in result

    def test_build_cta_has_heading(self):
        result = self.s.build_cta(self.ctx)
        assert "heading" in result
        assert result["heading"]

    def test_build_cta_has_body(self):
        result = self.s.build_cta(self.ctx)
        assert "body" in result
        assert result["body"]

    # quality_gate
    def test_quality_gate_returns_quality_gate_instance(self):
        result = self.s.quality_gate()
        assert isinstance(result, QualityGate)

    def test_quality_gate_min_word_count_positive(self):
        gate = self.s.quality_gate()
        assert gate.min_words > 0

    def test_quality_gate_requires_products(self):
        gate = self.s.quality_gate()
        assert gate.required_products is True

    # schema_types
    def test_schema_types_returns_non_empty_list(self):
        result = self.s.schema_types()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_schema_types_includes_breadcrumb(self):
        assert "BreadcrumbList" in self.s.schema_types()

    def test_schema_types_includes_item_list(self):
        assert "ItemList" in self.s.schema_types()

    # distribution_channels
    def test_distribution_channels_returns_list(self):
        result = self.s.distribution_channels()
        assert isinstance(result, list)

    def test_distribution_channels_includes_facebook(self):
        assert "facebook" in self.s.distribution_channels()

    def test_distribution_channels_includes_instagram(self):
        assert "instagram" in self.s.distribution_channels()


# ---------------------------------------------------------------------------
# FAQPageStrategy
# ---------------------------------------------------------------------------

class TestFAQPageStrategy:
    @pytest.fixture(autouse=True)
    def strategy(self):
        self.s = FAQPageStrategy()
        self.ctx = _ctx(page_type="faq_page")

    # build_intro
    def test_build_intro_returns_non_empty_string(self):
        assert self.s.build_intro(self.ctx)

    def test_build_intro_max_240_chars(self):
        assert len(self.s.build_intro(self.ctx)) <= 240

    # build_sections
    def test_build_sections_returns_non_empty_list(self):
        result = self.s.build_sections(self.ctx)
        assert len(result) >= 1

    def test_build_sections_sections_have_heading_and_paragraphs(self):
        for section in self.s.build_sections(self.ctx):
            assert section.get("heading")
            assert isinstance(section.get("paragraphs"), list)

    # build_faq_items — FAQ page must return >= 5 (matching its quality_gate)
    def test_build_faq_items_returns_at_least_5(self):
        result = self.s.build_faq_items(self.ctx)
        assert len(result) >= 5

    def test_build_faq_items_all_have_question_and_answer(self):
        for item in self.s.build_faq_items(self.ctx):
            assert item.get("question")
            assert item.get("answer")

    def test_build_faq_items_count_matches_quality_gate_min(self):
        gate = self.s.quality_gate()
        items = self.s.build_faq_items(self.ctx)
        assert len(items) >= gate.min_faq_items

    # build_cta
    def test_build_cta_has_text_key(self):
        assert "button_text" in self.s.build_cta(self.ctx)

    def test_build_cta_button_text_non_empty(self):
        assert self.s.build_cta(self.ctx)["button_text"]

    # quality_gate
    def test_quality_gate_min_words_positive(self):
        assert self.s.quality_gate().min_words > 0

    def test_quality_gate_requires_faq(self):
        assert self.s.quality_gate().required_faq is True

    def test_quality_gate_min_faq_items_at_least_5(self):
        assert self.s.quality_gate().min_faq_items >= 5

    # schema_types
    def test_schema_types_non_empty(self):
        assert len(self.s.schema_types()) > 0

    def test_schema_types_includes_faq_page(self):
        assert "FAQPage" in self.s.schema_types()

    # distribution_channels
    def test_distribution_channels_is_list(self):
        assert isinstance(self.s.distribution_channels(), list)

    def test_distribution_channels_includes_facebook(self):
        assert "facebook" in self.s.distribution_channels()


# ---------------------------------------------------------------------------
# CategoryPageStrategy
# ---------------------------------------------------------------------------

class TestCategoryPageStrategy:
    @pytest.fixture(autouse=True)
    def strategy(self):
        self.s = CategoryPageStrategy()
        self.ctx = _ctx(page_type="category_page")

    def test_build_intro_non_empty(self):
        assert self.s.build_intro(self.ctx)

    def test_build_intro_max_240_chars(self):
        assert len(self.s.build_intro(self.ctx)) <= 240

    def test_build_sections_at_least_one(self):
        assert len(self.s.build_sections(self.ctx)) >= 1

    def test_build_faq_items_returns_list(self):
        assert isinstance(self.s.build_faq_items(self.ctx), list)

    def test_build_faq_items_returns_at_least_one(self):
        assert len(self.s.build_faq_items(self.ctx)) >= 1

    def test_build_faq_items_each_has_question_and_answer(self):
        for item in self.s.build_faq_items(self.ctx):
            assert item.get("question")
            assert item.get("answer")

    def test_build_cta_has_text_key(self):
        assert "button_text" in self.s.build_cta(self.ctx)

    def test_build_cta_text_non_empty(self):
        assert self.s.build_cta(self.ctx)["button_text"]

    def test_quality_gate_min_words_positive(self):
        assert self.s.quality_gate().min_words > 0

    def test_quality_gate_instance(self):
        assert isinstance(self.s.quality_gate(), QualityGate)

    def test_schema_types_non_empty(self):
        assert len(self.s.schema_types()) > 0

    def test_distribution_channels_non_empty(self):
        assert len(self.s.distribution_channels()) > 0

    def test_distribution_channels_returns_list(self):
        assert isinstance(self.s.distribution_channels(), list)


# ---------------------------------------------------------------------------
# OccasionPageStrategy
# ---------------------------------------------------------------------------

class TestOccasionPageStrategy:
    @pytest.fixture(autouse=True)
    def strategy(self):
        self.s = OccasionPageStrategy()
        self.ctx = _ctx(page_type="occasion_page")

    def test_build_intro_non_empty(self):
        assert self.s.build_intro(self.ctx)

    def test_build_intro_max_240_chars(self):
        assert len(self.s.build_intro(self.ctx)) <= 240

    def test_build_sections_non_empty(self):
        assert len(self.s.build_sections(self.ctx)) >= 1

    def test_build_sections_each_has_heading(self):
        for section in self.s.build_sections(self.ctx):
            assert section.get("heading")

    def test_build_faq_items_returns_3(self):
        result = self.s.build_faq_items(self.ctx)
        assert len(result) == 3

    def test_build_faq_items_all_have_question_answer(self):
        for item in self.s.build_faq_items(self.ctx):
            assert item.get("question")
            assert item.get("answer")

    def test_build_cta_has_text_key(self):
        assert "button_text" in self.s.build_cta(self.ctx)

    def test_build_cta_heading_non_empty(self):
        assert self.s.build_cta(self.ctx)["heading"]

    def test_quality_gate_min_words_positive(self):
        assert self.s.quality_gate().min_words > 0

    def test_quality_gate_requires_faq(self):
        assert self.s.quality_gate().required_faq is True

    def test_quality_gate_requires_products(self):
        assert self.s.quality_gate().required_products is True

    def test_quality_gate_min_products_at_least_1(self):
        assert self.s.quality_gate().min_products >= 1

    def test_schema_types_non_empty(self):
        assert len(self.s.schema_types()) > 0

    def test_schema_types_includes_breadcrumb(self):
        assert "BreadcrumbList" in self.s.schema_types()

    def test_distribution_channels_non_empty(self):
        assert len(self.s.distribution_channels()) > 0

    def test_distribution_channels_includes_instagram(self):
        assert "instagram" in self.s.distribution_channels()


# ---------------------------------------------------------------------------
# Cross-strategy: shared base contract
# ---------------------------------------------------------------------------

ALL_STRATEGIES = [
    LandingPageStrategy(),
    FAQPageStrategy(),
    CategoryPageStrategy(),
    OccasionPageStrategy(),
]


@pytest.mark.parametrize("strategy", ALL_STRATEGIES, ids=lambda s: s.type_id)
class TestBaseContract:
    """Every strategy must satisfy the PageTypeStrategy contract."""

    def test_type_id_non_empty(self, strategy):
        assert strategy.type_id

    def test_display_name_non_empty(self, strategy):
        assert strategy.display_name

    def test_build_intro_returns_non_empty(self, strategy):
        ctx = _ctx(page_type=strategy.type_id)
        assert strategy.build_intro(ctx)

    def test_build_sections_returns_non_empty_list(self, strategy):
        ctx = _ctx(page_type=strategy.type_id)
        sections = strategy.build_sections(ctx)
        assert isinstance(sections, list)
        assert len(sections) >= 1

    def test_build_faq_items_returns_list(self, strategy):
        ctx = _ctx(page_type=strategy.type_id)
        items = strategy.build_faq_items(ctx)
        assert isinstance(items, list)

    def test_build_cta_has_text_key(self, strategy):
        ctx = _ctx(page_type=strategy.type_id)
        cta = strategy.build_cta(ctx)
        assert "button_text" in cta

    def test_quality_gate_min_words_positive(self, strategy):
        gate = strategy.quality_gate()
        assert isinstance(gate, QualityGate)
        assert gate.min_words > 0

    def test_schema_types_non_empty_list(self, strategy):
        types = strategy.schema_types()
        assert isinstance(types, list)
        assert len(types) > 0

    def test_distribution_channels_is_list(self, strategy):
        channels = strategy.distribution_channels()
        assert isinstance(channels, list)

    def test_build_meta_description_within_155_chars(self, strategy):
        ctx = _ctx(page_type=strategy.type_id)
        desc = strategy.build_meta_description(ctx)
        assert isinstance(desc, str)
        assert len(desc) <= 155

    def test_search_intent_non_empty(self, strategy):
        assert strategy.search_intent()


# ---------------------------------------------------------------------------
# Edge cases: empty / minimal BriefContext
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_landing_page_no_products_still_returns_sections(self):
        s = LandingPageStrategy()
        ctx = _ctx(selected_products=[])
        sections = s.build_sections(ctx)
        assert len(sections) >= 1

    def test_faq_page_empty_keyword_falls_back_to_title(self):
        s = FAQPageStrategy()
        ctx = _ctx(primary_keyword="", title="Haribo Gummies")
        intro = s.build_intro(ctx)
        assert "Haribo Gummies" in intro

    def test_category_page_no_category_hint_uses_default(self):
        s = CategoryPageStrategy()
        ctx = _ctx(category_hint="")
        # Should not raise; returns something sensible
        intro = s.build_intro(ctx)
        assert intro

    def test_occasion_page_empty_cluster_still_builds(self):
        s = OccasionPageStrategy()
        ctx = _ctx(cluster="")
        sections = s.build_sections(ctx)
        assert sections

    def test_trim_helper_truncates_long_intro(self):
        """Strategy._trim must not exceed the specified limit."""
        s = LandingPageStrategy()
        # Force a long primary_keyword
        ctx = _ctx(primary_keyword="a" * 500)
        intro = s.build_intro(ctx)
        assert len(intro) <= 240
