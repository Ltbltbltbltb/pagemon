"""Tests for pagemon.core: PageMon engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from pagemon.core import PageMon
from pagemon.models import CheckStatus, Snapshot, Target

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_engine(tmp_db: Path, webhook: str | None = None) -> PageMon:
    return PageMon(db_path=tmp_db, webhook_url=webhook)


def mock_http_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


HTML_V1 = "<html><body><p>Original content</p></body></html>"
HTML_V2 = "<html><body><p>Updated content substantially different</p></body></html>"


# ---------------------------------------------------------------------------
# PageMon.add
# ---------------------------------------------------------------------------


class TestPageMonAdd:
    def test_should_return_target_with_assigned_id(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        engine.close()
        assert target.id is not None

    def test_should_persist_url(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com")
        retrieved = engine.storage.get_target_by_url("https://example.com")
        engine.close()
        assert retrieved is not None

    def test_should_persist_name_when_provided(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com", name="My Page")
        retrieved = engine.storage.get_target_by_url("https://example.com")
        engine.close()
        assert retrieved.name == "My Page"

    def test_should_persist_selector_when_provided(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com", selector=".price")
        retrieved = engine.storage.get_target_by_url("https://example.com")
        engine.close()
        assert retrieved.selector == ".price"

    def test_should_use_default_interval_of_30(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        engine.close()
        assert target.interval_minutes == 30

    def test_should_persist_custom_interval(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com", interval=60)
        engine.close()
        assert target.interval_minutes == 60

    def test_should_persist_custom_headers(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com", headers={"X-Token": "abc"})
        retrieved = engine.storage.get_target_by_url("https://example.com")
        engine.close()
        assert retrieved.headers == {"X-Token": "abc"}


# ---------------------------------------------------------------------------
# PageMon.remove
# ---------------------------------------------------------------------------


class TestPageMonRemove:
    def test_should_return_true_when_target_exists(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com")
        result = engine.remove("https://example.com")
        engine.close()
        assert result is True

    def test_should_return_false_when_target_does_not_exist(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        result = engine.remove("https://nonexistent.com")
        engine.close()
        assert result is False

    def test_should_remove_target_from_storage(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com")
        engine.remove("https://example.com")
        retrieved = engine.storage.get_target_by_url("https://example.com")
        engine.close()
        assert retrieved is None


# ---------------------------------------------------------------------------
# PageMon.list_targets
# ---------------------------------------------------------------------------


class TestPageMonListTargets:
    def test_should_return_empty_list_when_no_targets(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        result = engine.list_targets()
        engine.close()
        assert result == []

    def test_should_return_all_added_targets(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://a.com")
        engine.add("https://b.com")
        result = engine.list_targets()
        engine.close()
        assert len(result) == 2

    def test_should_return_target_instances(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://example.com")
        result = engine.list_targets()
        engine.close()
        assert all(isinstance(t, Target) for t in result)


# ---------------------------------------------------------------------------
# PageMon.check — first visit (NEW)
# ---------------------------------------------------------------------------


class TestPageMonCheckNew:
    def test_should_return_new_status_on_first_visit(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            result = engine.check(target)
        engine.close()
        assert result.status == CheckStatus.NEW

    def test_should_save_snapshot_on_first_visit(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        snapshot = engine.storage.get_latest_snapshot(target.id)
        engine.close()
        assert snapshot is not None

    def test_should_return_new_snapshot_on_first_visit(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            result = engine.check(target)
        engine.close()
        assert result.new_snapshot is not None

    def test_should_not_trigger_notifier_on_first_visit(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.notifier = MagicMock()
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        engine.close()
        engine.notifier.send.assert_not_called()


# ---------------------------------------------------------------------------
# PageMon.check — no change (UNCHANGED)
# ---------------------------------------------------------------------------


class TestPageMonCheckUnchanged:
    def test_should_return_unchanged_status_when_content_same(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)  # first visit
            result = engine.check(target)  # second visit, same content
        engine.close()
        assert result.status == CheckStatus.UNCHANGED

    def test_should_not_save_snapshot_when_unchanged(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
            engine.check(target)
        snapshots = engine.storage.get_snapshots(target.id)
        engine.close()
        assert len(snapshots) == 1

    def test_should_not_trigger_notifier_when_unchanged(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.notifier = MagicMock()
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
            engine.check(target)
        engine.close()
        engine.notifier.send.assert_not_called()


# ---------------------------------------------------------------------------
# PageMon.check — content changed (CHANGED)
# ---------------------------------------------------------------------------


class TestPageMonCheckChanged:
    def test_should_return_changed_status_when_content_differs(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        with patch.object(engine, "_fetch", return_value=HTML_V2):
            result = engine.check(target)
        engine.close()
        assert result.status == CheckStatus.CHANGED

    def test_should_include_diff_text_when_changed(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        with patch.object(engine, "_fetch", return_value=HTML_V2):
            result = engine.check(target)
        engine.close()
        assert result.diff_text is not None
        assert len(result.diff_text) > 0

    def test_should_save_new_snapshot_when_changed(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        with patch.object(engine, "_fetch", return_value=HTML_V2):
            engine.check(target)
        snapshots = engine.storage.get_snapshots(target.id)
        engine.close()
        assert len(snapshots) == 2

    def test_should_trigger_notifier_when_changed(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.notifier = MagicMock()
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        with patch.object(engine, "_fetch", return_value=HTML_V2):
            engine.check(target)
        engine.close()
        engine.notifier.send.assert_called_once()


# ---------------------------------------------------------------------------
# PageMon.check — network error (ERROR)
# ---------------------------------------------------------------------------


class TestPageMonCheckError:
    def test_should_return_error_status_on_network_failure(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", side_effect=httpx.ConnectError("refused")):
            result = engine.check(target)
        engine.close()
        assert result.status == CheckStatus.ERROR

    def test_should_include_error_message_on_failure(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", side_effect=Exception("timeout")):
            result = engine.check(target)
        engine.close()
        assert "timeout" in result.error

    def test_should_not_save_snapshot_on_error(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", side_effect=httpx.TimeoutException("timeout")):
            engine.check(target)
        snapshot = engine.storage.get_latest_snapshot(target.id)
        engine.close()
        assert snapshot is None

    def test_should_not_trigger_notifier_on_error(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.notifier = MagicMock()
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", side_effect=Exception("error")):
            engine.check(target)
        engine.close()
        engine.notifier.send.assert_not_called()


# ---------------------------------------------------------------------------
# PageMon.check_all
# ---------------------------------------------------------------------------


class TestPageMonCheckAll:
    def test_should_return_empty_list_when_no_targets(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        results = engine.check_all()
        engine.close()
        assert results == []

    def test_should_return_result_for_each_target(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://a.com")
        engine.add("https://b.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            results = engine.check_all()
        engine.close()
        assert len(results) == 2

    def test_should_check_all_targets_even_when_one_errors(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        engine.add("https://a.com")
        engine.add("https://b.com")
        call_count = 0

        def fetch_side_effect(target: Target) -> str:
            nonlocal call_count
            call_count += 1
            if "a.com" in target.url:
                raise Exception("network error")
            return HTML_V1

        with patch.object(engine, "_fetch", side_effect=fetch_side_effect):
            results = engine.check_all()
        engine.close()
        assert len(results) == 2
        statuses = {r.target.url: r.status for r in results}
        assert statuses["https://a.com"] == CheckStatus.ERROR
        assert statuses["https://b.com"] == CheckStatus.NEW


# ---------------------------------------------------------------------------
# PageMon.get_history
# ---------------------------------------------------------------------------


class TestPageMonGetHistory:
    def test_should_return_empty_list_when_url_not_tracked(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        result = engine.get_history("https://unknown.com")
        engine.close()
        assert result == []

    def test_should_return_snapshots_for_known_url(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        result = engine.get_history("https://example.com")
        engine.close()
        assert len(result) == 1

    def test_should_respect_limit_parameter(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        contents = [f"<html><body><p>Content version {i}</p></body></html>" for i in range(5)]
        for html in contents:
            with patch.object(engine, "_fetch", return_value=html):
                engine.check(target)
                # Force each check to store by clearing hash cache
                engine.storage.get_latest_snapshot(target.id)
                # Directly add more snapshots
        # Add additional snapshots directly
        for i in range(5):
            c = f"content {i}"
            engine.storage.add_snapshot(
                Snapshot(
                    target_id=target.id,
                    content=c,
                    content_hash=Snapshot.hash_content(c),
                    status_code=200,
                    timestamp=f"2024-0{i + 1}-01T00:00:00",
                )
            )
        result = engine.get_history("https://example.com", limit=3)
        engine.close()
        assert len(result) == 3


# ---------------------------------------------------------------------------
# PageMon.get_diff
# ---------------------------------------------------------------------------


class TestPageMonGetDiff:
    def test_should_return_none_when_url_not_tracked(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        result = engine.get_diff("https://unknown.com")
        engine.close()
        assert result is None

    def test_should_return_none_when_only_one_snapshot(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        with patch.object(engine, "_fetch", return_value=HTML_V1):
            engine.check(target)
        result = engine.get_diff("https://example.com")
        engine.close()
        assert result is None

    def test_should_return_diff_string_when_two_snapshots_exist(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        # Add two snapshots directly to force two entries
        content_a = "Old content for page"
        content_b = "New content for page with changes"
        engine.storage.add_snapshot(
            Snapshot(
                target_id=target.id,
                content=content_a,
                content_hash=Snapshot.hash_content(content_a),
                status_code=200,
                timestamp="2024-01-01T00:00:00",
            )
        )
        engine.storage.add_snapshot(
            Snapshot(
                target_id=target.id,
                content=content_b,
                content_hash=Snapshot.hash_content(content_b),
                status_code=200,
                timestamp="2024-06-01T00:00:00",
            )
        )
        result = engine.get_diff("https://example.com")
        engine.close()
        assert result is not None
        assert isinstance(result, str)

    def test_should_return_diff_between_newest_and_second_newest(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = engine.add("https://example.com")
        content_old = "This is the old version"
        content_new = "This is the new version"
        engine.storage.add_snapshot(
            Snapshot(
                target_id=target.id,
                content=content_old,
                content_hash=Snapshot.hash_content(content_old),
                status_code=200,
                timestamp="2024-01-01T00:00:00",
            )
        )
        engine.storage.add_snapshot(
            Snapshot(
                target_id=target.id,
                content=content_new,
                content_hash=Snapshot.hash_content(content_new),
                status_code=200,
                timestamp="2024-06-01T00:00:00",
            )
        )
        result = engine.get_diff("https://example.com")
        engine.close()
        assert "-This is the old version" in result
        assert "+This is the new version" in result


# ---------------------------------------------------------------------------
# PageMon._fetch
# ---------------------------------------------------------------------------


class TestPageMonFetch:
    def test_should_send_user_agent_header(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = Target(url="https://example.com", id=1)
        captured_headers = {}

        def fake_get(url, headers, **kwargs):
            captured_headers.update(headers)
            resp = mock_http_response(HTML_V1)
            return resp

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = fake_get
            mock_client_cls.return_value = mock_client
            engine._fetch(target)

        engine.close()
        assert "User-Agent" in captured_headers

    def test_should_merge_custom_headers_with_defaults(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = Target(url="https://example.com", id=1, headers={"X-Custom": "value"})
        captured_headers = {}

        def fake_get(url, headers, **kwargs):
            captured_headers.update(headers)
            return mock_http_response(HTML_V1)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = fake_get
            mock_client_cls.return_value = mock_client
            engine._fetch(target)

        engine.close()
        assert "User-Agent" in captured_headers
        assert captured_headers.get("X-Custom") == "value"

    def test_should_raise_on_http_error_status(self, tmp_db: Path) -> None:
        engine = make_engine(tmp_db)
        target = Target(url="https://example.com", id=1)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                engine._fetch(target)

        engine.close()
