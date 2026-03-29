"""Data models for pagemon."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CheckStatus(Enum):
    """Result status of a page check."""

    CHANGED = "changed"
    UNCHANGED = "unchanged"
    ERROR = "error"
    NEW = "new"


@dataclass
class Target:
    """A URL being monitored for changes."""

    url: str
    name: str | None = None
    selector: str | None = None
    interval_minutes: int = 30
    headers: dict[str, str] | None = None
    created_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Snapshot:
    """A captured state of a web page at a point in time."""

    target_id: int
    content: str
    content_hash: str
    status_code: int
    timestamp: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @staticmethod
    def hash_content(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class CheckResult:
    """Result of checking a target for changes."""

    target: Target
    status: CheckStatus
    diff_text: str | None = None
    error: str | None = None
    new_snapshot: Snapshot | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
