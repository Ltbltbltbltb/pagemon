"""Tests for pagemon.models: Target, Snapshot, CheckResult."""

from __future__ import annotations

from datetime import datetime

from pagemon.models import CheckResult, CheckStatus, Snapshot, Target

# ---------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------


class TestTarget:
    def test_should_set_created_at_automatically_when_not_provided(self) -> None:
        target = Target(url="https://example.com")
        assert target.created_at != ""

    def test_should_preserve_created_at_when_explicitly_provided(self) -> None:
        ts = "2024-01-01T00:00:00"
        target = Target(url="https://example.com", created_at=ts)
        assert target.created_at == ts

    def test_should_have_none_id_before_persistence(self) -> None:
        target = Target(url="https://example.com")
        assert target.id is None

    def test_should_use_default_interval_of_30_minutes(self) -> None:
        target = Target(url="https://example.com")
        assert target.interval_minutes == 30

    def test_should_store_custom_interval(self) -> None:
        target = Target(url="https://example.com", interval_minutes=120)
        assert target.interval_minutes == 120

    def test_should_store_none_name_when_not_provided(self) -> None:
        target = Target(url="https://example.com")
        assert target.name is None

    def test_should_store_none_selector_when_not_provided(self) -> None:
        target = Target(url="https://example.com")
        assert target.selector is None

    def test_should_store_custom_headers(self) -> None:
        headers = {"Authorization": "Bearer token123"}
        target = Target(url="https://example.com", headers=headers)
        assert target.headers == {"Authorization": "Bearer token123"}

    def test_should_store_none_headers_when_not_provided(self) -> None:
        target = Target(url="https://example.com")
        assert target.headers is None

    def test_should_store_url(self) -> None:
        target = Target(url="https://example.com/path?query=1")
        assert target.url == "https://example.com/path?query=1"

    def test_should_produce_iso_format_created_at(self) -> None:
        target = Target(url="https://example.com")
        # Should parse without raising
        datetime.fromisoformat(target.created_at)

    def test_should_store_all_fields(self) -> None:
        target = Target(
            url="https://example.com",
            name="My Page",
            selector=".content",
            interval_minutes=15,
            headers={"X-Token": "abc"},
            created_at="2024-06-01T10:00:00",
            id=42,
        )
        assert target.name == "My Page"
        assert target.selector == ".content"
        assert target.interval_minutes == 15
        assert target.headers == {"X-Token": "abc"}
        assert target.id == 42


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_should_set_timestamp_automatically_when_not_provided(self) -> None:
        snap = Snapshot(target_id=1, content="hello", content_hash="abc", status_code=200)
        assert snap.timestamp != ""

    def test_should_preserve_timestamp_when_explicitly_provided(self) -> None:
        ts = "2024-01-01T12:00:00"
        snap = Snapshot(
            target_id=1, content="hello", content_hash="abc", status_code=200, timestamp=ts
        )
        assert snap.timestamp == ts

    def test_should_have_none_id_before_persistence(self) -> None:
        snap = Snapshot(target_id=1, content="hello", content_hash="abc", status_code=200)
        assert snap.id is None

    def test_should_produce_iso_format_timestamp(self) -> None:
        snap = Snapshot(target_id=1, content="hello", content_hash="abc", status_code=200)
        datetime.fromisoformat(snap.timestamp)

    def test_hash_content_should_return_sha256_hex(self) -> None:
        result = Snapshot.hash_content("hello")
        # sha256("hello") is known
        import hashlib

        expected = hashlib.sha256("hello".encode()).hexdigest()
        assert result == expected

    def test_hash_content_should_return_64_char_hex_string(self) -> None:
        result = Snapshot.hash_content("any content")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_content_should_be_deterministic(self) -> None:
        assert Snapshot.hash_content("same") == Snapshot.hash_content("same")

    def test_hash_content_should_differ_for_different_inputs(self) -> None:
        assert Snapshot.hash_content("abc") != Snapshot.hash_content("def")

    def test_hash_content_should_handle_empty_string(self) -> None:
        result = Snapshot.hash_content("")
        assert len(result) == 64

    def test_hash_content_should_handle_unicode(self) -> None:
        result = Snapshot.hash_content("こんにちは")
        assert len(result) == 64


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_should_set_timestamp_automatically(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.UNCHANGED)
        assert result.timestamp != ""

    def test_should_produce_iso_format_timestamp(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.UNCHANGED)
        datetime.fromisoformat(result.timestamp)

    def test_should_default_diff_text_to_none(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.UNCHANGED)
        assert result.diff_text is None

    def test_should_default_error_to_none(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.UNCHANGED)
        assert result.error is None

    def test_should_default_new_snapshot_to_none(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.UNCHANGED)
        assert result.new_snapshot is None

    def test_should_store_error_message(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.ERROR, error="timeout")
        assert result.error == "timeout"

    def test_should_store_diff_text(self) -> None:
        target = Target(url="https://example.com")
        result = CheckResult(target=target, status=CheckStatus.CHANGED, diff_text="-old\n+new")
        assert result.diff_text == "-old\n+new"

    def test_should_store_check_status(self) -> None:
        target = Target(url="https://example.com")
        for status in CheckStatus:
            result = CheckResult(target=target, status=status)
            assert result.status == status


class TestCheckStatus:
    def test_should_have_four_variants(self) -> None:
        assert len(CheckStatus) == 4

    def test_should_have_changed_value(self) -> None:
        assert CheckStatus.CHANGED.value == "changed"

    def test_should_have_unchanged_value(self) -> None:
        assert CheckStatus.UNCHANGED.value == "unchanged"

    def test_should_have_error_value(self) -> None:
        assert CheckStatus.ERROR.value == "error"

    def test_should_have_new_value(self) -> None:
        assert CheckStatus.NEW.value == "new"
