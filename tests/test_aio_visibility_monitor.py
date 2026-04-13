"""Unit tests for aio_visibility_monitor.AIOVisibilityMonitor."""
import sys
sys.path.insert(0, '/Users/michaelzhao/agents/agents/sweetsworld-seo-agent/src')

import pytest
from aio_visibility_monitor import AIOVisibilityMonitor, AIOCoverageReport, AIOObservation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "aio_test.db")


@pytest.fixture()
def monitor(db_path):
    return AIOVisibilityMonitor(db_path, site_id="testsite")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGE_A = "https://sweetsworld.com.au/guides/bulk-lollies/"
PAGE_B = "https://sweetsworld.com.au/guides/chocolate-gifts/"
PAGE_C = "https://sweetsworld.com.au/guides/halal-candy/"


# ===========================================================================
# Initialization
# ===========================================================================

class TestInit:

    def test_schema_created_on_init(self, db_path):
        """Constructor creates the aio_observations table in the DB."""
        import sqlite3
        monitor = AIOVisibilityMonitor(db_path, site_id="testsite")
        con = sqlite3.connect(db_path)
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        con.close()
        assert "aio_observations" in tables

    def test_parent_dir_created_if_missing(self, tmp_path):
        nested_path = str(tmp_path / "subdir" / "nested" / "aio.db")
        m = AIOVisibilityMonitor(nested_path, site_id="testsite")
        import sqlite3
        con = sqlite3.connect(nested_path)
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        con.close()
        assert "aio_observations" in tables

    def test_site_id_stored(self, monitor):
        assert monitor.site_id == "testsite"


# ===========================================================================
# log_observation — basic inserts
# ===========================================================================

class TestLogObservation:

    def test_log_cited_true_inserts_row(self, monitor):
        obs = monitor.log_observation(
            page_url=PAGE_A,
            engine="perplexity",
            query="bulk lollies australia",
            was_cited=True,
            citation_url="https://perplexity.ai/search/abc",
            notes="Appeared as #1",
        )
        assert isinstance(obs, AIOObservation)
        assert obs.was_cited is True
        assert obs.page_url == PAGE_A
        assert obs.engine == "perplexity"
        assert obs.query == "bulk lollies australia"
        assert obs.citation_url == "https://perplexity.ai/search/abc"
        assert obs.notes == "Appeared as #1"

    def test_log_cited_false_inserts_row(self, monitor):
        obs = monitor.log_observation(
            page_url=PAGE_B,
            engine="chatgpt",
            query="chocolate gifts",
            was_cited=False,
        )
        assert isinstance(obs, AIOObservation)
        assert obs.was_cited is False
        assert obs.page_url == PAGE_B

    def test_observed_at_is_populated(self, monitor):
        obs = monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="test")
        assert obs.observed_at != ""

    def test_returns_aio_observation_instance(self, monitor):
        result = monitor.log_observation(page_url=PAGE_A, engine="google_aio", query="q")
        assert isinstance(result, AIOObservation)

    def test_engine_name_property(self, monitor):
        obs = monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q")
        assert obs.engine_name == "Perplexity AI"

    def test_unknown_engine_raises_value_error(self, monitor):
        with pytest.raises(ValueError, match="Unknown engine"):
            monitor.log_observation(page_url=PAGE_A, engine="unknown_engine", query="q")

    def test_unknown_engine_error_lists_valid_engines(self, monitor):
        with pytest.raises(ValueError) as exc_info:
            monitor.log_observation(page_url=PAGE_A, engine="bad", query="q")
        assert "chatgpt" in str(exc_info.value) or "perplexity" in str(exc_info.value)


# ===========================================================================
# log_observation — upsert on duplicate
# ===========================================================================

class TestLogObservationUpsert:

    def test_duplicate_key_updates_was_cited(self, monitor):
        # First: not cited
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="same-query", was_cited=False)
        # Second: cited — should update in place
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="same-query", was_cited=True)

        observations = monitor.get_observations_for_page(PAGE_A)
        assert len(observations) == 1, "Upsert should produce exactly one row"
        assert observations[0].was_cited is True

    def test_duplicate_key_updates_notes(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", notes="first")
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", notes="updated")
        observations = monitor.get_observations_for_page(PAGE_A)
        assert len(observations) == 1
        assert observations[0].notes == "updated"

    def test_different_query_inserts_new_row(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="query-1")
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="query-2")
        observations = monitor.get_observations_for_page(PAGE_A)
        assert len(observations) == 2

    def test_different_engine_same_query_inserts_new_row(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1")
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q1")
        observations = monitor.get_observations_for_page(PAGE_A)
        assert len(observations) == 2


# ===========================================================================
# get_observations_for_page
# ===========================================================================

class TestGetObservationsForPage:

    def test_returns_observations_for_correct_page(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=True)
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q2", was_cited=False)
        monitor.log_observation(page_url=PAGE_B, engine="chatgpt", query="q1", was_cited=True)

        results = monitor.get_observations_for_page(PAGE_A)
        assert len(results) == 2
        for r in results:
            assert r.page_url == PAGE_A

    def test_returns_empty_for_unobserved_page(self, monitor):
        results = monitor.get_observations_for_page("https://unknown.example.com/")
        assert results == []

    def test_isolates_by_site_id(self, db_path):
        m1 = AIOVisibilityMonitor(db_path, site_id="site-a")
        m2 = AIOVisibilityMonitor(db_path, site_id="site-b")

        m1.log_observation(page_url=PAGE_A, engine="chatgpt", query="q")
        # site-b should not see site-a's observations
        assert m2.get_observations_for_page(PAGE_A) == []

    def test_returns_most_recent_first(self, monitor):
        # Two different queries so they don't upsert
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="first-query")
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="second-query")
        results = monitor.get_observations_for_page(PAGE_A)
        # Should be ordered by observed_at DESC
        assert results[0].observed_at >= results[1].observed_at


# ===========================================================================
# get_uncited_pages
# ===========================================================================

class TestGetUncitedPages:

    def test_returns_pages_with_zero_citations(self, monitor):
        # PAGE_A: not cited; PAGE_B: not cited
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=False)
        monitor.log_observation(page_url=PAGE_B, engine="perplexity", query="q", was_cited=False)

        uncited = monitor.get_uncited_pages([PAGE_A, PAGE_B])
        assert PAGE_A in uncited
        assert PAGE_B in uncited

    def test_excludes_pages_with_at_least_one_citation(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=True)
        monitor.log_observation(page_url=PAGE_B, engine="perplexity", query="q1", was_cited=False)

        uncited = monitor.get_uncited_pages([PAGE_A, PAGE_B])
        assert PAGE_A not in uncited
        assert PAGE_B in uncited

    def test_empty_page_list_returns_empty(self, monitor):
        uncited = monitor.get_uncited_pages([])
        assert uncited == []

    def test_page_not_in_db_is_returned_as_uncited(self, monitor):
        # PAGE_C has never been logged — it's implicitly uncited
        uncited = monitor.get_uncited_pages([PAGE_C])
        assert PAGE_C in uncited

    def test_all_cited_returns_empty_list(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=True)
        monitor.log_observation(page_url=PAGE_B, engine="perplexity", query="q", was_cited=True)
        uncited = monitor.get_uncited_pages([PAGE_A, PAGE_B])
        assert uncited == []

    def test_mixed_not_cited_and_no_entry_both_returned(self, monitor):
        # PAGE_A: explicitly not-cited; PAGE_C: never logged
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=False)
        uncited = monitor.get_uncited_pages([PAGE_A, PAGE_C])
        assert PAGE_A in uncited
        assert PAGE_C in uncited


# ===========================================================================
# get_aio_score
# ===========================================================================

class TestGetAioScore:

    def test_returns_zero_for_uncited_page(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=False)
        score = monitor.get_aio_score(PAGE_A)
        assert score == 0.0

    def test_returns_zero_for_page_with_no_observations(self, monitor):
        score = monitor.get_aio_score("https://unknown.example.com/")
        assert score == 0.0

    def test_returns_positive_for_cited_page(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=True)
        score = monitor.get_aio_score(PAGE_A)
        assert score > 0.0

    def test_score_bounded_between_0_and_1(self, monitor):
        # Cite the page by multiple engines
        for engine in ("chatgpt", "perplexity", "google_aio", "copilot", "gemini"):
            monitor.log_observation(page_url=PAGE_A, engine=engine, query=f"q-{engine}", was_cited=True)
        score = monitor.get_aio_score(PAGE_A)
        assert 0.0 <= score <= 1.0

    def test_more_citations_means_higher_score(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=True)
        monitor.log_observation(page_url=PAGE_B, engine="chatgpt", query="q", was_cited=True)
        monitor.log_observation(page_url=PAGE_B, engine="perplexity", query="q2", was_cited=True)
        score_a = monitor.get_aio_score(PAGE_A)
        score_b = monitor.get_aio_score(PAGE_B)
        assert score_b > score_a

    def test_score_uses_engine_weights(self, monitor):
        # chatgpt weight=1.0, copilot weight=0.8
        # Total weight = 1.0+0.9+1.0+0.8+0.9 = 4.6
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=True)
        score_chatgpt = monitor.get_aio_score(PAGE_A)

        monitor2 = AIOVisibilityMonitor(
            str(pytest.MonkeyPatch().mktemp if False else __import__("tempfile").mktemp(suffix=".db")),
            site_id="testsite",
        )
        monitor2.log_observation(page_url=PAGE_A, engine="copilot", query="q", was_cited=True)
        score_copilot = monitor2.get_aio_score(PAGE_A)

        # chatgpt (1.0) should score higher than copilot (0.8)
        assert score_chatgpt > score_copilot


# ===========================================================================
# coverage_report
# ===========================================================================

class TestCoverageReport:

    def test_returns_aio_coverage_report_instance(self, monitor):
        report = monitor.coverage_report()
        assert isinstance(report, AIOCoverageReport)

    def test_empty_db_returns_zero_counts(self, monitor):
        report = monitor.coverage_report()
        assert report.total_observations == 0
        assert report.total_citations == 0
        assert report.citation_rate == 0.0
        assert report.by_engine == {}
        assert report.top_cited_pages == []
        assert report.zero_citation_pages == []

    def test_total_observations_count(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1")
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q2")
        monitor.log_observation(page_url=PAGE_B, engine="chatgpt", query="q1")
        report = monitor.coverage_report()
        assert report.total_observations == 3

    def test_total_citations_count(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=True)
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q2", was_cited=False)
        monitor.log_observation(page_url=PAGE_B, engine="chatgpt", query="q1", was_cited=True)
        report = monitor.coverage_report()
        assert report.total_citations == 2

    def test_citation_rate_calculation(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=True)
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q2", was_cited=False)
        report = monitor.coverage_report()
        assert abs(report.citation_rate - 0.5) < 1e-9

    def test_by_engine_contains_correct_engines(self, monitor):
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=True)
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q2", was_cited=False)
        report = monitor.coverage_report()
        assert "chatgpt" in report.by_engine
        assert "perplexity" in report.by_engine
        assert report.by_engine["chatgpt"]["observations"] == 1
        assert report.by_engine["chatgpt"]["citations"] == 1
        assert report.by_engine["perplexity"]["observations"] == 1
        assert report.by_engine["perplexity"]["citations"] == 0

    def test_top_cited_pages_sorted_descending(self, monitor):
        # PAGE_A cited twice, PAGE_B cited once
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=True)
        monitor.log_observation(page_url=PAGE_A, engine="perplexity", query="q2", was_cited=True)
        monitor.log_observation(page_url=PAGE_B, engine="chatgpt", query="q1", was_cited=True)
        report = monitor.coverage_report()
        assert len(report.top_cited_pages) == 2
        assert report.top_cited_pages[0]["page_url"] == PAGE_A
        assert report.top_cited_pages[0]["citation_count"] == 2
        assert report.top_cited_pages[1]["page_url"] == PAGE_B
        assert report.top_cited_pages[1]["citation_count"] == 1

    def test_zero_citation_pages_contains_observed_but_uncited(self, monitor):
        # PAGE_A: observed but not cited
        # PAGE_B: observed and cited
        monitor.log_observation(page_url=PAGE_A, engine="chatgpt", query="q1", was_cited=False)
        monitor.log_observation(page_url=PAGE_B, engine="chatgpt", query="q1", was_cited=True)
        report = monitor.coverage_report()
        assert PAGE_A in report.zero_citation_pages
        assert PAGE_B not in report.zero_citation_pages

    def test_site_id_on_report(self, monitor):
        report = monitor.coverage_report()
        assert report.site_id == "testsite"

    def test_site_isolation_in_report(self, db_path):
        m1 = AIOVisibilityMonitor(db_path, site_id="site-x")
        m2 = AIOVisibilityMonitor(db_path, site_id="site-y")

        m1.log_observation(page_url=PAGE_A, engine="chatgpt", query="q", was_cited=True)
        m1.log_observation(page_url=PAGE_A, engine="perplexity", query="q2", was_cited=True)

        # m2 has no observations
        report = m2.coverage_report()
        assert report.total_observations == 0

        # m1 has 2 observations
        report1 = m1.coverage_report()
        assert report1.total_observations == 2
