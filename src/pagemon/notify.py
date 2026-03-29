"""Notification backends for pagemon."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from urllib.request import Request, urlopen

from pagemon.models import CheckResult

logger = logging.getLogger(__name__)


class Notifier(ABC):
    """Base class for notification backends."""

    @abstractmethod
    def send(self, result: CheckResult) -> bool:
        """Send a notification. Returns True on success."""
        ...


class WebhookNotifier(Notifier):
    """Send notifications via HTTP webhook (POST JSON)."""

    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, result: CheckResult) -> bool:
        payload = {
            "url": result.target.url,
            "name": result.target.name or result.target.url,
            "status": result.status.value,
            "diff": result.diff_text,
            "timestamp": result.timestamp,
        }
        try:
            req = Request(
                self.url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                return resp.status < 400
        except Exception:
            logger.exception("Webhook notification failed for %s", self.url)
            return False


class ConsoleNotifier(Notifier):
    """Print notifications to the terminal (default)."""

    def send(self, result: CheckResult) -> bool:
        name = result.target.name or result.target.url
        print(f"[pagemon] {result.status.value.upper()}: {name}")
        if result.diff_text:
            print(result.diff_text[:500])
        return True


def get_notifier(webhook_url: str | None = None) -> Notifier:
    """Factory to get the appropriate notifier."""
    if webhook_url:
        return WebhookNotifier(webhook_url)
    return ConsoleNotifier()
