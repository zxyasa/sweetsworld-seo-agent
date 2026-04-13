"""Unit tests for citation_planner.CitationPlanner."""
import sys

sys.path.insert(0, "/Users/michaelzhao/agents/agents/sweetsworld-seo-agent/src")

import pytest
from citation_planner import (
    CitationPlanner,
    CitationBrief,
    ALL_CHANNELS,
    MIN_CITATIONS_TARGET,
    PAGE_TYPE_CHANNELS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def planner(tmp_path):
    """Return a CitationPlanner backed by a fresh temp SQLite file."""
    db = str(tmp_path / "citations.db")
    return CitationPlanner(db_path=db, site_id="test_site")


PAGE_URL = "https://sweetsworld.com.au/bulk-candy"
PAGE_TYPE = "guide_page"
TITLE = "The Ultimate Bulk Candy Guide"
EXCERPT = "Find the best bulk candy deals across Australia."
KEYWORD = "bulk candy australia"


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def test_init_creates_schema(tmp_path):
    """CitationPlanner.__init__ creates the SQLite file with a citations table."""
    import sqlite3

    db = str(tmp_path / "init_test.db")
    CitationPlanner(db_path=db, site_id="test_site")

    con = sqlite3.connect(db)
    tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    con.close()
    assert "citations" in tables


def test_init_idempotent(tmp_path):
    """Constructing CitationPlanner twice on same DB does not raise."""
    db = str(tmp_path / "idem.db")
    CitationPlanner(db_path=db)
    CitationPlanner(db_path=db)  # should not raise


# ---------------------------------------------------------------------------
# log_citation
# ---------------------------------------------------------------------------


def test_log_citation_inserts_row_with_status_published(planner):
    """log_citation creates a row with status='published' by default."""
    planner.log_citation(PAGE_URL, "pinterest", "https://pin.it/abc123")

    coverage = planner.get_citation_coverage(PAGE_URL)
    assert coverage["published_citations"] == 1
    assert "pinterest" in coverage["channels"]


def test_log_citation_stores_citation_url(planner):
    """log_citation persists the citation_url in the DB."""
    import sqlite3

    planner.log_citation(PAGE_URL, "facebook", "https://fb.com/post/999")

    con = sqlite3.connect(planner.db_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT * FROM citations WHERE page_url=? AND channel_id=?",
        (PAGE_URL, "facebook"),
    ).fetchone()
    con.close()

    assert row is not None
    assert row["citation_url"] == "https://fb.com/post/999"
    assert row["status"] == "published"


def test_log_citation_upsert_on_duplicate_updates(planner):
    """log_citation on the same (page_url, channel_id) pair updates, not inserts."""
    planner.log_citation(PAGE_URL, "pinterest", "https://pin.it/first")
    planner.log_citation(PAGE_URL, "pinterest", "https://pin.it/second")

    import sqlite3

    con = sqlite3.connect(planner.db_path)
    count = con.execute(
        "SELECT COUNT(*) FROM citations WHERE page_url=? AND channel_id=?",
        (PAGE_URL, "pinterest"),
    ).fetchone()[0]
    con.close()

    assert count == 1  # only one row, not two


def test_log_citation_upsert_updates_citation_url(planner):
    """On duplicate (page_url, channel_id), the citation_url is updated."""
    planner.log_citation(PAGE_URL, "pinterest", "https://pin.it/old")
    planner.log_citation(PAGE_URL, "pinterest", "https://pin.it/new")

    import sqlite3

    con = sqlite3.connect(planner.db_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT citation_url FROM citations WHERE page_url=? AND channel_id=?",
        (PAGE_URL, "pinterest"),
    ).fetchone()
    con.close()

    assert row["citation_url"] == "https://pin.it/new"


def test_log_citation_pending_status_not_counted_as_published(planner):
    """A citation with status='pending' is not counted in published_citations."""
    planner.log_citation(PAGE_URL, "medium", status="pending")

    coverage = planner.get_citation_coverage(PAGE_URL)
    assert coverage["total_citations"] == 1
    assert coverage["published_citations"] == 0
    assert "medium" not in coverage["channels"]


# ---------------------------------------------------------------------------
# get_citation_coverage
# ---------------------------------------------------------------------------


def test_get_citation_coverage_returns_correct_published_count(planner):
    """get_citation_coverage counts only published citations."""
    planner.log_citation(PAGE_URL, "facebook", status="published")
    planner.log_citation(PAGE_URL, "instagram", status="published")
    planner.log_citation(PAGE_URL, "medium", status="pending")

    coverage = planner.get_citation_coverage(PAGE_URL)
    assert coverage["published_citations"] == 2
    assert coverage["total_citations"] == 3


def test_get_citation_coverage_meets_minimum_false_below_threshold(planner):
    """meets_minimum is False when published_citations < MIN_CITATIONS_TARGET."""
    assert MIN_CITATIONS_TARGET >= 2, "Sanity check on constant"

    planner.log_citation(PAGE_URL, "facebook", status="published")
    planner.log_citation(PAGE_URL, "instagram", status="published")
    # 2 < 3 (MIN_CITATIONS_TARGET)

    coverage = planner.get_citation_coverage(PAGE_URL)
    assert coverage["meets_minimum"] is False


def test_get_citation_coverage_meets_minimum_true_at_threshold(planner):
    """meets_minimum is True when published_citations >= MIN_CITATIONS_TARGET."""
    planner.log_citation(PAGE_URL, "facebook", status="published")
    planner.log_citation(PAGE_URL, "instagram", status="published")
    planner.log_citation(PAGE_URL, "pinterest", status="published")

    coverage = planner.get_citation_coverage(PAGE_URL)
    assert coverage["meets_minimum"] is True


def test_get_citation_coverage_channels_list(planner):
    """get_citation_coverage['channels'] contains only published channel IDs."""
    planner.log_citation(PAGE_URL, "gbp_post", status="published")
    planner.log_citation(PAGE_URL, "x", status="pending")

    coverage = planner.get_citation_coverage(PAGE_URL)
    assert "gbp_post" in coverage["channels"]
    assert "x" not in coverage["channels"]


def test_get_citation_coverage_empty_for_uncited_page(planner):
    """get_citation_coverage returns zero counts for a page with no citations."""
    coverage = planner.get_citation_coverage("https://uncited.example.com/page")
    assert coverage["published_citations"] == 0
    assert coverage["total_citations"] == 0
    assert coverage["meets_minimum"] is False


# ---------------------------------------------------------------------------
# get_pages_below_minimum
# ---------------------------------------------------------------------------


def test_get_pages_below_minimum_returns_undercovered_pages(planner):
    """Pages with fewer than MIN_CITATIONS_TARGET published citations are returned."""
    url_a = "https://sweetsworld.com.au/page-a"
    url_b = "https://sweetsworld.com.au/page-b"

    # page-a: 3 citations (at minimum, should NOT appear)
    for ch in ["facebook", "instagram", "pinterest"]:
        planner.log_citation(url_a, ch, status="published")

    # page-b: 1 citation (below minimum, SHOULD appear)
    planner.log_citation(url_b, "facebook", status="published")

    below = planner.get_pages_below_minimum()
    below_urls = {r["page_url"] for r in below}

    assert url_b in below_urls
    assert url_a not in below_urls


def test_get_pages_below_minimum_empty_when_all_meet_target(planner):
    """Returns empty list when all pages meet the citation target."""
    for ch in ["facebook", "instagram", "pinterest"]:
        planner.log_citation(PAGE_URL, ch, status="published")

    assert planner.get_pages_below_minimum() == []


def test_get_pages_below_minimum_ignores_pending_citations(planner):
    """Pending citations do not count toward the minimum."""
    # 2 published + 2 pending = still below minimum
    planner.log_citation(PAGE_URL, "facebook", status="published")
    planner.log_citation(PAGE_URL, "instagram", status="published")
    planner.log_citation(PAGE_URL, "pinterest", status="pending")
    planner.log_citation(PAGE_URL, "x", status="pending")

    below = planner.get_pages_below_minimum()
    below_urls = {r["page_url"] for r in below}
    assert PAGE_URL in below_urls


# ---------------------------------------------------------------------------
# get_uncited_channels
# ---------------------------------------------------------------------------


def test_get_uncited_channels_returns_missing_channels(planner):
    """get_uncited_channels returns channels in page_type target not yet published."""
    page_type = "guide_page"
    target_ids = set(PAGE_TYPE_CHANNELS[page_type])  # e.g. pinterest, facebook, medium

    # Publish only one of the targets
    planner.log_citation(PAGE_URL, "pinterest", status="published")

    uncited = planner.get_uncited_channels(PAGE_URL, page_type)
    uncited_ids = {c.channel_id for c in uncited}

    assert "pinterest" not in uncited_ids
    assert uncited_ids.issubset(target_ids)
    assert len(uncited_ids) == len(target_ids) - 1


def test_get_uncited_channels_empty_when_all_covered(planner):
    """get_uncited_channels returns empty list when all target channels are published."""
    page_type = "guide_page"
    for ch in PAGE_TYPE_CHANNELS[page_type]:
        planner.log_citation(PAGE_URL, ch, status="published")

    uncited = planner.get_uncited_channels(PAGE_URL, page_type)
    assert uncited == []


def test_get_uncited_channels_ignores_pending(planner):
    """A pending citation does not remove a channel from the uncited list."""
    page_type = "guide_page"
    planner.log_citation(PAGE_URL, "pinterest", status="pending")

    uncited = planner.get_uncited_channels(PAGE_URL, page_type)
    uncited_ids = {c.channel_id for c in uncited}
    # pinterest is pending, so it should still appear as uncited
    assert "pinterest" in uncited_ids


# ---------------------------------------------------------------------------
# build_citation_brief
# ---------------------------------------------------------------------------


def test_build_citation_brief_returns_brief_for_valid_channel(planner):
    """build_citation_brief returns a CitationBrief for a known channel_id."""
    brief = planner.build_citation_brief(
        PAGE_URL, PAGE_TYPE, TITLE, EXCERPT, KEYWORD, channel_id="pinterest"
    )
    assert brief is not None
    assert isinstance(brief, CitationBrief)
    assert brief.page_url == PAGE_URL
    assert brief.page_type == PAGE_TYPE
    assert brief.title == TITLE
    assert brief.keyword == KEYWORD
    assert brief.channel.channel_id == "pinterest"


def test_build_citation_brief_returns_none_for_unknown_channel(planner):
    """build_citation_brief returns None when channel_id is not recognised."""
    brief = planner.build_citation_brief(
        PAGE_URL, PAGE_TYPE, TITLE, EXCERPT, KEYWORD, channel_id="nonexistent_platform"
    )
    assert brief is None


def test_build_citation_brief_caption_not_empty(planner):
    """build_citation_brief always populates suggested_caption."""
    for channel_id in ["gbp_post", "pinterest", "medium", "facebook", "reddit"]:
        brief = planner.build_citation_brief(
            PAGE_URL, PAGE_TYPE, TITLE, EXCERPT, KEYWORD, channel_id=channel_id
        )
        assert brief is not None
        assert len(brief.suggested_caption) > 0


def test_build_citation_brief_syndication_sets_canonical_note(planner):
    """Syndication channels (medium) include a canonical_note with the page URL."""
    brief = planner.build_citation_brief(
        PAGE_URL, PAGE_TYPE, TITLE, EXCERPT, KEYWORD, channel_id="medium"
    )
    assert brief is not None
    assert PAGE_URL in brief.canonical_note


def test_build_citation_brief_non_syndication_has_empty_canonical(planner):
    """Non-syndication channels have an empty canonical_note."""
    brief = planner.build_citation_brief(
        PAGE_URL, PAGE_TYPE, TITLE, EXCERPT, KEYWORD, channel_id="pinterest"
    )
    assert brief is not None
    assert brief.canonical_note == ""


def test_build_citation_brief_hashtags_include_base_tags(planner):
    """suggested_hashtags always contains the three base SweetsWorld tags."""
    brief = planner.build_citation_brief(
        PAGE_URL, "occasion_page", TITLE, EXCERPT, KEYWORD, channel_id="gbp_post"
    )
    assert brief is not None
    assert "#AustralianCandy" in brief.suggested_hashtags
    assert "#SweetsWorld" in brief.suggested_hashtags
    assert "#CandyAustralia" in brief.suggested_hashtags


# ---------------------------------------------------------------------------
# citation_summary
# ---------------------------------------------------------------------------


def test_citation_summary_returns_by_channel_counts(planner):
    """citation_summary returns correct counts broken down by channel_id."""
    url_a = "https://sweetsworld.com.au/page-a"
    url_b = "https://sweetsworld.com.au/page-b"

    planner.log_citation(url_a, "facebook", status="published")
    planner.log_citation(url_b, "facebook", status="published")
    planner.log_citation(url_a, "pinterest", status="published")
    planner.log_citation(url_b, "instagram", status="pending")  # not counted

    summary = planner.citation_summary()

    assert summary["by_channel"]["facebook"] == 2
    assert summary["by_channel"]["pinterest"] == 1
    # instagram was pending — must not appear in by_channel
    assert "instagram" not in summary["by_channel"]


def test_citation_summary_total_includes_all_statuses(planner):
    """citation_summary total_citations counts all rows regardless of status."""
    planner.log_citation(PAGE_URL, "facebook", status="published")
    planner.log_citation(PAGE_URL, "medium", status="pending")

    summary = planner.citation_summary()
    assert summary["total_citations"] == 2


def test_citation_summary_empty_when_no_citations(planner):
    """citation_summary on empty DB returns zero total and empty by_channel."""
    summary = planner.citation_summary()
    assert summary["total_citations"] == 0
    assert summary["by_channel"] == {}


def test_citation_summary_site_id_isolation(tmp_path):
    """citation_summary only counts rows for its own site_id."""
    db = str(tmp_path / "shared.db")
    planner_a = CitationPlanner(db_path=db, site_id="site_a")
    planner_b = CitationPlanner(db_path=db, site_id="site_b")

    planner_a.log_citation(PAGE_URL, "facebook", status="published")
    planner_a.log_citation(PAGE_URL, "instagram", status="published")
    planner_b.log_citation(PAGE_URL, "pinterest", status="published")

    summary_a = planner_a.citation_summary()
    summary_b = planner_b.citation_summary()

    assert summary_a["total_citations"] == 2
    assert summary_b["total_citations"] == 1
    assert "facebook" in summary_a["by_channel"]
    assert "pinterest" in summary_b["by_channel"]
    assert "facebook" not in summary_b["by_channel"]
