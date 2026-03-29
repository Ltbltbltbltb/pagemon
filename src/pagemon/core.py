"""Core logic for pagemon - fetch, compare, store."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from pagemon.diff import clean_content, compute_diff, has_meaningful_change
from pagemon.models import CheckResult, CheckStatus, Snapshot, Target
from pagemon.notify import Notifier, get_notifier
from pagemon.storage import Storage

logger = logging.getLogger(__name__)


class PageMon:
    """Main pagemon engine."""

    def __init__(
        self,
        db_path: Path | None = None,
        webhook_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.storage = Storage(db_path)
        self.notifier: Notifier = get_notifier(webhook_url)
        self.timeout = timeout

    def add(
        self,
        url: str,
        name: str | None = None,
        selector: str | None = None,
        interval: int = 30,
        headers: dict[str, str] | None = None,
    ) -> Target:
        """Add a URL to monitor."""
        target = Target(
            url=url,
            name=name,
            selector=selector,
            interval_minutes=interval,
            headers=headers,
        )
        return self.storage.add_target(target)

    def remove(self, url: str) -> bool:
        """Remove a URL from monitoring."""
        return self.storage.remove_target(url)

    def list_targets(self) -> list[Target]:
        """List all monitored URLs."""
        return self.storage.list_targets()

    def check(self, target: Target) -> CheckResult:
        """Check a single target for changes."""
        try:
            html = self._fetch(target)
        except Exception as e:
            return CheckResult(
                target=target,
                status=CheckStatus.ERROR,
                error=str(e),
            )

        content = clean_content(html, target.selector)
        content_hash = Snapshot.hash_content(content)
        previous = self.storage.get_latest_snapshot(target.id)

        if previous is None:
            snapshot = Snapshot(
                target_id=target.id,
                content=content,
                content_hash=content_hash,
                status_code=200,
            )
            self.storage.add_snapshot(snapshot)
            return CheckResult(
                target=target,
                status=CheckStatus.NEW,
                new_snapshot=snapshot,
            )

        if content_hash == previous.content_hash:
            return CheckResult(target=target, status=CheckStatus.UNCHANGED)

        if not has_meaningful_change(previous.content, content):
            return CheckResult(target=target, status=CheckStatus.UNCHANGED)

        diff_text = compute_diff(previous.content, content)
        snapshot = Snapshot(
            target_id=target.id,
            content=content,
            content_hash=content_hash,
            status_code=200,
        )
        self.storage.add_snapshot(snapshot)

        result = CheckResult(
            target=target,
            status=CheckStatus.CHANGED,
            diff_text=diff_text,
            new_snapshot=snapshot,
        )
        self.notifier.send(result)
        return result

    def check_all(self) -> list[CheckResult]:
        """Check all targets for changes."""
        results = []
        for target in self.storage.list_targets():
            result = self.check(target)
            results.append(result)
        return results

    def get_history(self, url: str, limit: int = 10) -> list[Snapshot]:
        """Get snapshot history for a URL."""
        target = self.storage.get_target_by_url(url)
        if not target:
            return []
        return self.storage.get_snapshots(target.id, limit)

    def get_diff(self, url: str) -> str | None:
        """Get the diff between the two most recent snapshots."""
        target = self.storage.get_target_by_url(url)
        if not target:
            return None
        snapshots = self.storage.get_snapshots(target.id, limit=2)
        if len(snapshots) < 2:
            return None
        return compute_diff(snapshots[1].content, snapshots[0].content)

    def _fetch(self, target: Target) -> str:
        """Fetch the HTML content of a URL."""
        headers = {
            "User-Agent": "pagemon/0.1 (+https://github.com/Ltbltbltbltb/pagemon)",
            **(target.headers or {}),
        }
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.get(target.url, headers=headers)
            resp.raise_for_status()
            return resp.text

    def close(self) -> None:
        self.storage.close()
