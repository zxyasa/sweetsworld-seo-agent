"""Unit tests for topics_db.TopicsDB."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from topics_db import TopicsDB, VALID_STATUSES  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_topic(slug: str = "test-slug", **overrides) -> dict:
    base = {
        "slug": slug,
        "title": "Test Title",
        "primary_keyword": "test keyword",
        "category_hint": "Candy",
        "page_type": "landing_page",
        "cluster": "test_cluster",
        "priority": 5,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    def test_creates_db_file(self, tmp_path):
        db_file = str(tmp_path / "topics.db")
        TopicsDB(db_file)
        assert Path(db_file).exists()

    def test_creates_topics_table(self, tmp_path):
        import sqlite3
        db_file = str(tmp_path / "topics.db")
        TopicsDB(db_file)
        con = sqlite3.connect(db_file)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        con.close()
        assert "topics" in tables

    def test_creates_indexes(self, tmp_path):
        import sqlite3
        db_file = str(tmp_path / "topics.db")
        TopicsDB(db_file)
        con = sqlite3.connect(db_file)
        indexes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
        con.close()
        assert "idx_topics_status" in indexes
        assert "idx_topics_priority" in indexes

    def test_init_is_idempotent(self, tmp_path):
        """Calling TopicsDB twice on the same file must not raise."""
        db_file = str(tmp_path / "topics.db")
        TopicsDB(db_file)
        TopicsDB(db_file)  # should not raise

    def test_creates_parent_directories(self, tmp_path):
        db_file = str(tmp_path / "nested" / "deep" / "topics.db")
        TopicsDB(db_file)
        assert Path(db_file).exists()


# ---------------------------------------------------------------------------
# add_topic
# ---------------------------------------------------------------------------

class TestAddTopic:
    def test_returns_true_on_insert(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        result = db.add_topic(_minimal_topic())
        assert result is True

    def test_inserted_row_has_correct_fields(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        topic = _minimal_topic(slug="my-slug", title="My Title", primary_keyword="my keyword",
                                category_hint="Gummy", page_type="category_page",
                                cluster="gummies", priority=3)
        db.add_topic(topic)
        row = db.get_by_slug("my-slug")
        assert row is not None
        assert row["slug"] == "my-slug"
        assert row["title"] == "My Title"
        assert row["primary_keyword"] == "my keyword"
        assert row["category_hint"] == "Gummy"
        assert row["page_type"] == "category_page"
        assert row["cluster"] == "gummies"
        assert row["priority"] == 3
        assert row["status"] == "pending"

    def test_default_status_is_pending(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic())
        row = db.get_by_slug("test-slug")
        assert row["status"] == "pending"

    def test_default_priority_is_99(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic({"slug": "low-prio", "title": "T", "primary_keyword": "k"})
        row = db.get_by_slug("low-prio")
        assert row["priority"] == 99

    def test_duplicate_slug_returns_false(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="dup"))
        result = db.add_topic(_minimal_topic(slug="dup"))
        assert result is False

    def test_duplicate_slug_does_not_raise(self, tmp_path):
        """Duplicate insert must be handled gracefully, not raise an exception."""
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="dup"))
        try:
            db.add_topic(_minimal_topic(slug="dup"))
        except Exception as exc:
            pytest.fail(f"add_topic raised an unexpected exception: {exc}")

    def test_duplicate_does_not_overwrite_existing_row(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="dup", title="Original"))
        db.add_topic(_minimal_topic(slug="dup", title="Overwrite Attempt"))
        row = db.get_by_slug("dup")
        assert row["title"] == "Original"

    def test_raises_on_empty_slug(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        with pytest.raises(ValueError, match="slug"):
            db.add_topic({"slug": "", "title": "T", "primary_keyword": "k"})

    def test_strips_whitespace_from_slug(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic({"slug": "  spaced  ", "title": "T", "primary_keyword": "k"})
        row = db.get_by_slug("spaced")
        assert row is not None

    def test_created_at_and_updated_at_are_set(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic())
        row = db.get_by_slug("test-slug")
        assert row["created_at"]
        assert row["updated_at"]


# ---------------------------------------------------------------------------
# mark_status
# ---------------------------------------------------------------------------

class TestMarkStatus:
    def test_updates_status(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="s1"))
        db.mark_status("s1", "published")
        row = db.get_by_slug("s1")
        assert row["status"] == "published"

    def test_returns_true_when_slug_found(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="s1"))
        result = db.mark_status("s1", "drafted")
        assert result is True

    def test_returns_false_when_slug_not_found(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        result = db.mark_status("does-not-exist", "drafted")
        assert result is False

    def test_sets_published_at_when_status_is_published(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="pub"))
        db.mark_status("pub", "published")
        row = db.get_by_slug("pub")
        assert row["published_at"] is not None

    def test_does_not_set_published_at_for_non_published_status(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="draft"))
        db.mark_status("draft", "drafted")
        row = db.get_by_slug("draft")
        assert row["published_at"] is None

    def test_sets_quality_blocked_flag_on_quality_blocked_status(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="qb"))
        db.mark_status("qb", "quality_blocked", quality_reasons=["too short"])
        row = db.get_by_slug("qb")
        assert row["quality_blocked"] == 1

    def test_stores_quality_reasons_as_list(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="qb2"))
        reasons = ["too short", "no products"]
        db.mark_status("qb2", "quality_blocked", quality_reasons=reasons)
        row = db.get_by_slug("qb2")
        assert row["quality_reasons"] == reasons

    def test_updates_wp_post_id_and_url(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="wp"))
        db.mark_status("wp", "published", wp_post_id=42, wp_post_url="https://example.com/post")
        row = db.get_by_slug("wp")
        assert row["wp_post_id"] == 42
        assert row["wp_post_url"] == "https://example.com/post"

    def test_raises_on_invalid_status(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="bad"))
        with pytest.raises(ValueError, match="Invalid status"):
            db.mark_status("bad", "not_a_real_status")

    def test_all_valid_statuses_accepted(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        for i, status in enumerate(VALID_STATUSES):
            slug = f"status-test-{i}"
            db.add_topic(_minimal_topic(slug=slug))
            db.mark_status(slug, status)  # must not raise


# ---------------------------------------------------------------------------
# get_pending_queue
# ---------------------------------------------------------------------------

class TestGetPendingQueue:
    def test_returns_only_pending_rows(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="p1", priority=1))
        db.add_topic(_minimal_topic(slug="p2", priority=2))
        db.add_topic(_minimal_topic(slug="pub", priority=3))
        db.mark_status("pub", "published")
        queue = db.get_pending_queue()
        slugs = [r["slug"] for r in queue]
        assert "p1" in slugs
        assert "p2" in slugs
        assert "pub" not in slugs

    def test_ordered_by_priority_ascending(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="high-prio", priority=1))
        db.add_topic(_minimal_topic(slug="mid-prio", priority=5))
        db.add_topic(_minimal_topic(slug="low-prio", priority=10))
        queue = db.get_pending_queue()
        priorities = [r["priority"] for r in queue]
        assert priorities == sorted(priorities)

    def test_limit_restricts_result_count(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        for i in range(5):
            db.add_topic(_minimal_topic(slug=f"topic-{i}", priority=i))
        queue = db.get_pending_queue(limit=3)
        assert len(queue) == 3

    def test_filters_by_page_type(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="landing", page_type="landing_page"))
        db.add_topic(_minimal_topic(slug="category", page_type="category_page"))
        queue = db.get_pending_queue(page_type="landing_page")
        slugs = [r["slug"] for r in queue]
        assert "landing" in slugs
        assert "category" not in slugs

    def test_filters_by_cluster(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="c-a", cluster="cluster_a"))
        db.add_topic(_minimal_topic(slug="c-b", cluster="cluster_b"))
        queue = db.get_pending_queue(cluster="cluster_a")
        slugs = [r["slug"] for r in queue]
        assert "c-a" in slugs
        assert "c-b" not in slugs

    def test_filters_by_slug_list(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="alpha"))
        db.add_topic(_minimal_topic(slug="beta"))
        db.add_topic(_minimal_topic(slug="gamma"))
        queue = db.get_pending_queue(slugs=["alpha", "gamma"])
        slugs = [r["slug"] for r in queue]
        assert "alpha" in slugs
        assert "gamma" in slugs
        assert "beta" not in slugs

    def test_returns_empty_list_when_no_pending(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="done"))
        db.mark_status("done", "published")
        queue = db.get_pending_queue()
        assert queue == []

    def test_rows_are_dicts_with_expected_keys(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic())
        row = db.get_pending_queue()[0]
        for key in ("slug", "title", "primary_keyword", "page_type", "status", "priority"):
            assert key in row


# ---------------------------------------------------------------------------
# migrate_from_csv
# ---------------------------------------------------------------------------

class TestMigrateFromCsv:
    def _write_csv(self, path: Path, rows: list) -> None:
        fieldnames = ["slug", "title", "primary_keyword", "category_hint",
                      "page_type", "cluster", "priority"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_inserts_rows_from_csv(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        csv_path = tmp_path / "topics.csv"
        self._write_csv(csv_path, [
            {"slug": "a", "title": "A", "primary_keyword": "a kw", "category_hint": "",
             "page_type": "landing_page", "cluster": "", "priority": "1"},
            {"slug": "b", "title": "B", "primary_keyword": "b kw", "category_hint": "",
             "page_type": "category_page", "cluster": "", "priority": "2"},
        ])
        result = db.migrate_from_csv(str(csv_path))
        assert result["inserted"] == 2
        assert result["skipped"] == 0

    def test_skips_duplicate_slugs(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="a"))
        csv_path = tmp_path / "topics.csv"
        self._write_csv(csv_path, [
            {"slug": "a", "title": "A", "primary_keyword": "a kw", "category_hint": "",
             "page_type": "landing_page", "cluster": "", "priority": "1"},
        ])
        result = db.migrate_from_csv(str(csv_path))
        assert result["inserted"] == 0
        assert result["skipped"] == 1

    def test_returns_error_when_file_not_found(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        result = db.migrate_from_csv(str(tmp_path / "nonexistent.csv"))
        assert "error" in result

    def test_sets_status_to_pending(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        csv_path = tmp_path / "topics.csv"
        self._write_csv(csv_path, [
            {"slug": "csv-slug", "title": "CSV Title", "primary_keyword": "kw", "category_hint": "",
             "page_type": "landing_page", "cluster": "", "priority": "1"},
        ])
        db.migrate_from_csv(str(csv_path))
        row = db.get_by_slug("csv-slug")
        assert row["status"] == "pending"

    def test_handles_missing_priority_column_as_99(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        csv_path = tmp_path / "topics.csv"
        # Write CSV without a priority value (empty string)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["slug", "title", "primary_keyword",
                                                    "category_hint", "page_type", "cluster", "priority"])
            writer.writeheader()
            writer.writerow({"slug": "no-prio", "title": "T", "primary_keyword": "k",
                             "category_hint": "", "page_type": "landing_page", "cluster": "", "priority": ""})
        db.migrate_from_csv(str(csv_path))
        row = db.get_by_slug("no-prio")
        assert row["priority"] == 99

    def test_returns_inserted_count(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        csv_path = tmp_path / "topics.csv"
        rows = [{"slug": f"slug-{i}", "title": f"T{i}", "primary_keyword": "kw",
                 "category_hint": "", "page_type": "landing_page", "cluster": "", "priority": str(i)}
                for i in range(4)]
        self._write_csv(csv_path, rows)
        result = db.migrate_from_csv(str(csv_path))
        assert result["inserted"] == 4


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------

class TestExportCsv:
    def test_creates_output_file(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic())
        out = str(tmp_path / "out.csv")
        db.export_csv(out)
        assert Path(out).exists()

    def test_returns_row_count(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="a"))
        db.add_topic(_minimal_topic(slug="b"))
        out = str(tmp_path / "out.csv")
        count = db.export_csv(out)
        assert count == 2

    def test_csv_contains_expected_columns(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic())
        out = str(tmp_path / "out.csv")
        db.export_csv(out)
        with open(out, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        for col in ("slug", "title", "primary_keyword", "category_hint", "page_type", "cluster", "priority"):
            assert col in fieldnames

    def test_round_trip_preserves_data(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        original = _minimal_topic(slug="rt-slug", title="Round Trip", primary_keyword="rt kw",
                                   category_hint="Chocolate", page_type="guide_page",
                                   cluster="guide_cluster", priority=7)
        db.add_topic(original)
        csv_out = str(tmp_path / "out.csv")
        db.export_csv(csv_out)

        # Import into a fresh DB and verify data matches
        db2 = TopicsDB(str(tmp_path / "t2.db"))
        db2.migrate_from_csv(csv_out)
        row = db2.get_by_slug("rt-slug")
        assert row is not None
        assert row["title"] == "Round Trip"
        assert row["primary_keyword"] == "rt kw"
        assert row["category_hint"] == "Chocolate"
        assert row["page_type"] == "guide_page"
        assert row["cluster"] == "guide_cluster"
        assert row["priority"] == 7

    def test_export_ordered_by_priority(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="high", priority=1))
        db.add_topic(_minimal_topic(slug="low", priority=10))
        db.add_topic(_minimal_topic(slug="mid", priority=5))
        out = str(tmp_path / "out.csv")
        db.export_csv(out)
        with open(out, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            priorities = [int(r["priority"]) for r in reader]
        assert priorities == sorted(priorities)

    def test_export_overwrites_existing_file(self, tmp_path):
        db = TopicsDB(str(tmp_path / "t.db"))
        db.add_topic(_minimal_topic(slug="first"))
        out = str(tmp_path / "out.csv")
        db.export_csv(out)

        db.add_topic(_minimal_topic(slug="second"))
        db.export_csv(out)
        with open(out, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            slugs = [r["slug"] for r in reader]
        assert "first" in slugs
        assert "second" in slugs
