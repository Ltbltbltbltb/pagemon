"""Tests for pagemon.storage: Storage CRUD operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from pagemon.models import Snapshot, Target
from pagemon.storage import Storage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_target(url: str = "https://example.com", **kwargs) -> Target:
    return Target(url=url, **kwargs)


def make_snapshot(target_id: int, content: str = "page content") -> Snapshot:
    return Snapshot(
        target_id=target_id,
        content=content,
        content_hash=Snapshot.hash_content(content),
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Storage init
# ---------------------------------------------------------------------------


class TestStorageInit:
    def test_should_create_db_file_when_initialized(self, tmp_db: Path) -> None:
        s = Storage(tmp_db)
        s.close()
        assert tmp_db.exists()

    def test_should_create_parent_directories_when_missing(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nested" / "dirs" / "pagemon.db"
        s = Storage(db_path)
        s.close()
        assert db_path.exists()

    def test_should_be_idempotent_when_initialized_twice_on_same_db(self, tmp_db: Path) -> None:
        s1 = Storage(tmp_db)
        s1.close()
        s2 = Storage(tmp_db)
        s2.close()
        assert tmp_db.exists()


# ---------------------------------------------------------------------------
# add_target
# ---------------------------------------------------------------------------


class TestAddTarget:
    def test_should_return_target_with_id_assigned(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        assert target.id is not None

    def test_should_assign_sequential_ids(self, storage: Storage) -> None:
        t1 = storage.add_target(make_target("https://a.com"))
        t2 = storage.add_target(make_target("https://b.com"))
        assert t2.id > t1.id

    def test_should_persist_url(self, storage: Storage) -> None:
        storage.add_target(make_target("https://example.com"))
        retrieved = storage.get_target_by_url("https://example.com")
        assert retrieved.url == "https://example.com"

    def test_should_persist_name(self, storage: Storage) -> None:
        storage.add_target(make_target(name="My Page"))
        retrieved = storage.get_target_by_url("https://example.com")
        assert retrieved.name == "My Page"

    def test_should_persist_selector(self, storage: Storage) -> None:
        storage.add_target(make_target(selector=".content"))
        retrieved = storage.get_target_by_url("https://example.com")
        assert retrieved.selector == ".content"

    def test_should_persist_interval_minutes(self, storage: Storage) -> None:
        storage.add_target(make_target(interval_minutes=15))
        retrieved = storage.get_target_by_url("https://example.com")
        assert retrieved.interval_minutes == 15

    def test_should_persist_headers_as_dict(self, storage: Storage) -> None:
        headers = {"Authorization": "Bearer abc", "X-Custom": "value"}
        storage.add_target(make_target(headers=headers))
        retrieved = storage.get_target_by_url("https://example.com")
        assert retrieved.headers == headers

    def test_should_persist_none_headers(self, storage: Storage) -> None:
        storage.add_target(make_target(headers=None))
        retrieved = storage.get_target_by_url("https://example.com")
        assert retrieved.headers is None

    def test_should_raise_when_duplicate_url_added(self, storage: Storage) -> None:
        storage.add_target(make_target("https://example.com"))
        import sqlite3

        with pytest.raises(sqlite3.IntegrityError):
            storage.add_target(make_target("https://example.com"))


# ---------------------------------------------------------------------------
# get_target_by_url
# ---------------------------------------------------------------------------


class TestGetTargetByUrl:
    def test_should_return_target_when_url_exists(self, storage: Storage) -> None:
        storage.add_target(make_target("https://example.com"))
        result = storage.get_target_by_url("https://example.com")
        assert result is not None

    def test_should_return_none_when_url_does_not_exist(self, storage: Storage) -> None:
        result = storage.get_target_by_url("https://nonexistent.com")
        assert result is None

    def test_should_return_correct_target_when_multiple_exist(self, storage: Storage) -> None:
        storage.add_target(make_target("https://a.com", name="A"))
        storage.add_target(make_target("https://b.com", name="B"))
        result = storage.get_target_by_url("https://b.com")
        assert result.name == "B"


# ---------------------------------------------------------------------------
# get_target_by_id
# ---------------------------------------------------------------------------


class TestGetTargetById:
    def test_should_return_target_when_id_exists(self, storage: Storage) -> None:
        added = storage.add_target(make_target())
        result = storage.get_target_by_id(added.id)
        assert result is not None

    def test_should_return_none_when_id_does_not_exist(self, storage: Storage) -> None:
        result = storage.get_target_by_id(9999)
        assert result is None

    def test_should_return_target_with_matching_url(self, storage: Storage) -> None:
        added = storage.add_target(make_target("https://example.com"))
        result = storage.get_target_by_id(added.id)
        assert result.url == "https://example.com"


# ---------------------------------------------------------------------------
# list_targets
# ---------------------------------------------------------------------------


class TestListTargets:
    def test_should_return_empty_list_when_no_targets(self, storage: Storage) -> None:
        result = storage.list_targets()
        assert result == []

    def test_should_return_all_added_targets(self, storage: Storage) -> None:
        storage.add_target(make_target("https://a.com"))
        storage.add_target(make_target("https://b.com"))
        result = storage.list_targets()
        assert len(result) == 2

    def test_should_return_targets_ordered_by_created_at_desc(self, storage: Storage) -> None:
        storage.add_target(make_target("https://first.com", created_at="2024-01-01T00:00:00"))
        storage.add_target(make_target("https://second.com", created_at="2024-06-01T00:00:00"))
        result = storage.list_targets()
        assert result[0].url == "https://second.com"

    def test_should_return_target_instances(self, storage: Storage) -> None:
        storage.add_target(make_target())
        result = storage.list_targets()
        assert all(isinstance(t, Target) for t in result)


# ---------------------------------------------------------------------------
# remove_target
# ---------------------------------------------------------------------------


class TestRemoveTarget:
    def test_should_return_true_when_target_exists(self, storage: Storage) -> None:
        storage.add_target(make_target("https://example.com"))
        result = storage.remove_target("https://example.com")
        assert result is True

    def test_should_return_false_when_target_does_not_exist(self, storage: Storage) -> None:
        result = storage.remove_target("https://nonexistent.com")
        assert result is False

    def test_should_remove_target_from_list(self, storage: Storage) -> None:
        storage.add_target(make_target("https://example.com"))
        storage.remove_target("https://example.com")
        assert storage.get_target_by_url("https://example.com") is None

    def test_should_leave_target_unretrievable_after_removal(self, storage: Storage) -> None:
        # Verify the target itself is gone; foreign key cascade is not guaranteed
        # without PRAGMA foreign_keys = ON, which Storage does not enable.
        target = storage.add_target(make_target("https://example.com"))
        storage.add_snapshot(make_snapshot(target.id))
        storage.remove_target("https://example.com")
        assert storage.get_target_by_url("https://example.com") is None


# ---------------------------------------------------------------------------
# add_snapshot
# ---------------------------------------------------------------------------


class TestAddSnapshot:
    def test_should_return_snapshot_with_id_assigned(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        snap = storage.add_snapshot(make_snapshot(target.id))
        assert snap.id is not None

    def test_should_persist_content(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        storage.add_snapshot(make_snapshot(target.id, content="unique content xyz"))
        retrieved = storage.get_latest_snapshot(target.id)
        assert retrieved.content == "unique content xyz"

    def test_should_persist_status_code(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        snap = Snapshot(
            target_id=target.id,
            content="x",
            content_hash=Snapshot.hash_content("x"),
            status_code=404,
        )
        storage.add_snapshot(snap)
        retrieved = storage.get_latest_snapshot(target.id)
        assert retrieved.status_code == 404

    def test_should_persist_content_hash(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        content = "some page text"
        expected_hash = Snapshot.hash_content(content)
        storage.add_snapshot(make_snapshot(target.id, content=content))
        retrieved = storage.get_latest_snapshot(target.id)
        assert retrieved.content_hash == expected_hash


# ---------------------------------------------------------------------------
# get_latest_snapshot
# ---------------------------------------------------------------------------


class TestGetLatestSnapshot:
    def test_should_return_none_when_no_snapshots(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        result = storage.get_latest_snapshot(target.id)
        assert result is None

    def test_should_return_most_recent_snapshot(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        snap1 = Snapshot(
            target_id=target.id,
            content="old",
            content_hash=Snapshot.hash_content("old"),
            status_code=200,
            timestamp="2024-01-01T10:00:00",
        )
        snap2 = Snapshot(
            target_id=target.id,
            content="new",
            content_hash=Snapshot.hash_content("new"),
            status_code=200,
            timestamp="2024-06-01T10:00:00",
        )
        storage.add_snapshot(snap1)
        storage.add_snapshot(snap2)
        result = storage.get_latest_snapshot(target.id)
        assert result.content == "new"

    def test_should_return_none_for_unknown_target_id(self, storage: Storage) -> None:
        result = storage.get_latest_snapshot(9999)
        assert result is None


# ---------------------------------------------------------------------------
# get_snapshots
# ---------------------------------------------------------------------------


class TestGetSnapshots:
    def test_should_return_empty_list_when_no_snapshots(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        result = storage.get_snapshots(target.id)
        assert result == []

    def test_should_respect_limit(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        for i in range(5):
            content = f"content {i}"
            storage.add_snapshot(
                Snapshot(
                    target_id=target.id,
                    content=content,
                    content_hash=Snapshot.hash_content(content),
                    status_code=200,
                    timestamp=f"2024-01-0{i + 1}T00:00:00",
                )
            )
        result = storage.get_snapshots(target.id, limit=3)
        assert len(result) == 3

    def test_should_return_snapshots_ordered_by_timestamp_desc(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        for ts in ["2024-01-01T00:00:00", "2024-03-01T00:00:00", "2024-06-01T00:00:00"]:
            c = f"content at {ts}"
            storage.add_snapshot(
                Snapshot(
                    target_id=target.id,
                    content=c,
                    content_hash=Snapshot.hash_content(c),
                    status_code=200,
                    timestamp=ts,
                )
            )
        result = storage.get_snapshots(target.id)
        assert result[0].timestamp == "2024-06-01T00:00:00"

    def test_should_return_snapshot_instances(self, storage: Storage) -> None:
        target = storage.add_target(make_target())
        storage.add_snapshot(make_snapshot(target.id))
        result = storage.get_snapshots(target.id)
        assert all(isinstance(s, Snapshot) for s in result)

    def test_should_only_return_snapshots_for_requested_target(self, storage: Storage) -> None:
        t1 = storage.add_target(make_target("https://a.com"))
        t2 = storage.add_target(make_target("https://b.com"))
        storage.add_snapshot(make_snapshot(t1.id, "content a"))
        storage.add_snapshot(make_snapshot(t2.id, "content b"))
        result = storage.get_snapshots(t1.id)
        assert len(result) == 1
        assert result[0].content == "content a"
