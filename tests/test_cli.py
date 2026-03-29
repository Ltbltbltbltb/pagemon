"""Tests for pagemon.cli: CLI commands via CliRunner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from pagemon.cli import cli
from pagemon.models import CheckResult, CheckStatus, Snapshot, Target


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_runner() -> CliRunner:
    return CliRunner()


def make_target(url: str = "https://example.com", **kwargs) -> Target:
    defaults = {"name": None, "selector": None, "interval_minutes": 30, "id": 1}
    defaults.update(kwargs)
    return Target(url=url, **defaults)


def make_snapshot(target_id: int = 1, content: str = "page content") -> Snapshot:
    return Snapshot(
        target_id=target_id,
        content=content,
        content_hash=Snapshot.hash_content(content),
        status_code=200,
        timestamp="2024-06-01T10:00:00",
        id=1,
    )


def make_check_result(
    target: Target,
    status: CheckStatus = CheckStatus.UNCHANGED,
    **kwargs,
) -> CheckResult:
    return CheckResult(target=target, status=status, **kwargs)


# ---------------------------------------------------------------------------
# `pagemon add`
# ---------------------------------------------------------------------------


class TestCliAdd:
    def test_should_exit_0_when_url_added_successfully(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        assert result.exit_code == 0

    def test_should_print_added_url_to_output(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        assert "https://example.com" in result.output

    def test_should_print_interval_to_output(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["add", "https://example.com", "--interval", "60", "--db", str(tmp_db)])
        assert "60m" in result.output

    def test_should_print_selector_when_provided(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(
            cli, ["add", "https://example.com", "--selector", ".price", "--db", str(tmp_db)]
        )
        assert ".price" in result.output

    def test_should_not_print_selector_when_not_provided(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        assert "Selector" not in result.output

    def test_should_exit_1_when_duplicate_url_added(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        assert result.exit_code == 1

    def test_should_print_error_when_duplicate_url_added(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# `pagemon rm`
# ---------------------------------------------------------------------------


class TestCliRemove:
    def test_should_exit_0_when_url_removed_successfully(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["rm", "https://example.com", "--db", str(tmp_db)])
        assert result.exit_code == 0

    def test_should_print_removed_url(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["rm", "https://example.com", "--db", str(tmp_db)])
        assert "https://example.com" in result.output

    def test_should_exit_1_when_url_not_found(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["rm", "https://nonexistent.com", "--db", str(tmp_db)])
        assert result.exit_code == 1

    def test_should_print_not_found_message_when_url_missing(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["rm", "https://nonexistent.com", "--db", str(tmp_db)])
        assert "Not found" in result.output


# ---------------------------------------------------------------------------
# `pagemon ls`
# ---------------------------------------------------------------------------


class TestCliList:
    def test_should_print_no_targets_message_when_empty(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["ls", "--db", str(tmp_db)])
        assert "No targets" in result.output

    def test_should_exit_0_when_no_targets(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["ls", "--db", str(tmp_db)])
        assert result.exit_code == 0

    def test_should_show_added_url_in_table(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["ls", "--db", str(tmp_db)])
        assert "https://example.com" in result.output

    def test_should_output_valid_json_when_json_flag_set(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--name", "Test", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["ls", "--json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)

    def test_should_include_url_in_json_output(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["ls", "--json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert parsed[0]["url"] == "https://example.com"

    def test_should_include_all_targets_in_json_output(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://a.com", "--db", str(tmp_db)])
        runner.invoke(cli, ["add", "https://b.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["ls", "--json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert len(parsed) == 2

    def test_should_show_name_in_table_when_set(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--name", "My Site", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["ls", "--db", str(tmp_db)])
        assert "My Site" in result.output

    def test_should_show_selector_in_table_when_set(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(
            cli, ["add", "https://example.com", "--selector", ".price", "--db", str(tmp_db)]
        )
        result = runner.invoke(cli, ["ls", "--db", str(tmp_db)])
        assert ".price" in result.output


# ---------------------------------------------------------------------------
# `pagemon check`
# ---------------------------------------------------------------------------


class TestCliCheck:
    def test_should_print_no_targets_message_when_checking_all_with_none(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["check", "--all", "--db", str(tmp_db)])
        assert "No targets" in result.output

    def test_should_exit_0_when_no_targets_to_check(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["check", "--all", "--db", str(tmp_db)])
        assert result.exit_code == 0

    def test_should_exit_1_when_url_not_tracked(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["check", "https://unknown.com", "--db", str(tmp_db)])
        assert result.exit_code == 1

    def test_should_print_not_found_when_url_not_tracked(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["check", "https://unknown.com", "--db", str(tmp_db)])
        assert "Not found" in result.output

    def test_should_show_new_status_on_first_check(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        html = "<html><body><p>Hello</p></body></html>"
        with patch("pagemon.core.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = runner.invoke(cli, ["check", "https://example.com", "--db", str(tmp_db)])
        assert "NEW" in result.output

    def test_should_output_valid_json_when_json_flag_set(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        html = "<html><body><p>Content</p></body></html>"
        with patch("pagemon.core.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = runner.invoke(
                cli, ["check", "--all", "--json", "--db", str(tmp_db)]
            )
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)

    def test_should_include_status_field_in_json_output(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        html = "<html><body><p>Content</p></body></html>"
        with patch("pagemon.core.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = runner.invoke(
                cli, ["check", "--all", "--json", "--db", str(tmp_db)]
            )
        parsed = json.loads(result.output)
        assert "status" in parsed[0]

    def test_should_check_all_targets_when_all_flag_used(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://a.com", "--db", str(tmp_db)])
        runner.invoke(cli, ["add", "https://b.com", "--db", str(tmp_db)])
        html = "<html><body><p>Content</p></body></html>"
        with patch("pagemon.core.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = runner.invoke(cli, ["check", "--all", "--json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert len(parsed) == 2


# ---------------------------------------------------------------------------
# `pagemon diff`
# ---------------------------------------------------------------------------


class TestCliDiff:
    def test_should_print_no_diff_available_when_only_one_snapshot(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        html = "<html><body><p>Content</p></body></html>"
        with patch("pagemon.core.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            runner.invoke(cli, ["check", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["diff", "https://example.com", "--db", str(tmp_db)])
        assert "No diff available" in result.output

    def test_should_print_no_diff_when_url_not_tracked(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["diff", "https://unknown.com", "--db", str(tmp_db)])
        assert "No diff available" in result.output


# ---------------------------------------------------------------------------
# `pagemon history`
# ---------------------------------------------------------------------------


class TestCliHistory:
    def test_should_print_no_history_when_no_snapshots(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["history", "https://example.com", "--db", str(tmp_db)])
        assert "No history" in result.output

    def test_should_print_no_history_when_url_not_tracked(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["history", "https://unknown.com", "--db", str(tmp_db)])
        assert "No history" in result.output

    def test_should_show_snapshot_in_table_when_one_exists(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        html = "<html><body><p>Content</p></body></html>"
        with patch("pagemon.core.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.text = html
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            runner.invoke(cli, ["check", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["history", "https://example.com", "--db", str(tmp_db)])
        assert "History" in result.output


# ---------------------------------------------------------------------------
# `pagemon export`
# ---------------------------------------------------------------------------


class TestCliExport:
    def test_should_output_valid_json_when_format_is_json(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["export", "--format", "json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)

    def test_should_include_url_in_json_export(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["export", "--format", "json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert parsed[0]["url"] == "https://example.com"

    def test_should_output_csv_header_when_format_is_csv(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["export", "--format", "csv", "--db", str(tmp_db)])
        first_line = result.output.splitlines()[0]
        assert "url" in first_line

    def test_should_include_url_in_csv_row(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["export", "--format", "csv", "--db", str(tmp_db)])
        assert "https://example.com" in result.output

    def test_should_output_empty_json_array_when_no_targets(self, tmp_db: Path) -> None:
        runner = make_runner()
        result = runner.invoke(cli, ["export", "--format", "json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert parsed == []

    def test_should_include_last_check_as_none_when_no_snapshots(self, tmp_db: Path) -> None:
        runner = make_runner()
        runner.invoke(cli, ["add", "https://example.com", "--db", str(tmp_db)])
        result = runner.invoke(cli, ["export", "--format", "json", "--db", str(tmp_db)])
        parsed = json.loads(result.output)
        assert parsed[0]["last_check"] is None
