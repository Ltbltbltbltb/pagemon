"""Shared fixtures for pagemon tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pagemon.models import CheckResult, CheckStatus, Snapshot, Target
from pagemon.storage import Storage

SAMPLE_HTML_V1 = """
<html>
<head><title>Test Page</title></head>
<body>
  <header>Site Header</header>
  <nav>Nav links</nav>
  <main>
    <h1>Hello World</h1>
    <p>This is the original content.</p>
    <p>Price: $10.00</p>
  </main>
  <footer>Footer text</footer>
  <script>console.log('noise');</script>
</body>
</html>
"""

SAMPLE_HTML_V2 = """
<html>
<head><title>Test Page</title></head>
<body>
  <header>Site Header</header>
  <nav>Nav links</nav>
  <main>
    <h1>Hello World</h1>
    <p>This is the updated content.</p>
    <p>Price: $12.00</p>
  </main>
  <footer>Footer text</footer>
  <script>console.log('noise');</script>
</body>
</html>
"""

SAMPLE_HTML_WITH_SELECTOR = """
<html>
<body>
  <div class="price">$99.99</div>
  <div class="description">Product description here.</div>
  <div class="noise">Last updated: 12:00 PM</div>
</body>
</html>
"""


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Path to a temporary SQLite database file."""
    return tmp_path / "test_pagemon.db"


@pytest.fixture()
def storage(tmp_db: Path) -> Storage:
    """A Storage instance backed by a tmp SQLite database."""
    s = Storage(tmp_db)
    yield s
    s.close()


@pytest.fixture()
def sample_target() -> Target:
    """A basic Target with known field values."""
    return Target(
        url="https://example.com",
        name="Example",
        selector=None,
        interval_minutes=60,
    )


@pytest.fixture()
def stored_target(storage: Storage, sample_target: Target) -> Target:
    """A Target that has already been persisted to the tmp storage."""
    return storage.add_target(sample_target)


@pytest.fixture()
def sample_snapshot(stored_target: Target) -> Snapshot:
    """A Snapshot for the stored_target with known content."""
    content = "Hello World\nThis is the original content.\nPrice: $10.00"
    return Snapshot(
        target_id=stored_target.id,
        content=content,
        content_hash=Snapshot.hash_content(content),
        status_code=200,
    )


@pytest.fixture()
def stored_snapshot(storage: Storage, sample_snapshot: Snapshot) -> Snapshot:
    """A Snapshot that has already been persisted to the tmp storage."""
    return storage.add_snapshot(sample_snapshot)


@pytest.fixture()
def check_result_changed(stored_target: Target, sample_snapshot: Snapshot) -> CheckResult:
    """A CheckResult with CHANGED status."""
    return CheckResult(
        target=stored_target,
        status=CheckStatus.CHANGED,
        diff_text="--- previous\n+++ current\n-old line\n+new line",
        new_snapshot=sample_snapshot,
    )
