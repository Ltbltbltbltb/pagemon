"""SQLite storage backend for pagemon."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pagemon.models import Snapshot, Target

DEFAULT_DB_PATH = Path.home() / ".pagemon" / "pagemon.db"


class Storage:
    """SQLite-based storage for targets and snapshots."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                name TEXT,
                selector TEXT,
                interval_minutes INTEGER DEFAULT 30,
                headers TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_target
                ON snapshots(target_id, timestamp DESC);
        """)
        self._conn.commit()

    def add_target(self, target: Target) -> Target:
        cur = self._conn.execute(
            """INSERT INTO targets (url, name, selector, interval_minutes, headers, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                target.url,
                target.name,
                target.selector,
                target.interval_minutes,
                json.dumps(target.headers) if target.headers else None,
                target.created_at,
            ),
        )
        self._conn.commit()
        target.id = cur.lastrowid
        return target

    def get_target_by_url(self, url: str) -> Target | None:
        row = self._conn.execute("SELECT * FROM targets WHERE url = ?", (url,)).fetchone()
        return self._row_to_target(row) if row else None

    def get_target_by_id(self, target_id: int) -> Target | None:
        row = self._conn.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
        return self._row_to_target(row) if row else None

    def list_targets(self) -> list[Target]:
        rows = self._conn.execute("SELECT * FROM targets ORDER BY created_at DESC").fetchall()
        return [self._row_to_target(row) for row in rows]

    def remove_target(self, url: str) -> bool:
        cur = self._conn.execute("DELETE FROM targets WHERE url = ?", (url,))
        self._conn.commit()
        return cur.rowcount > 0

    def add_snapshot(self, snapshot: Snapshot) -> Snapshot:
        cur = self._conn.execute(
            """INSERT INTO snapshots (target_id, content, content_hash, status_code, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (
                snapshot.target_id,
                snapshot.content,
                snapshot.content_hash,
                snapshot.status_code,
                snapshot.timestamp,
            ),
        )
        self._conn.commit()
        snapshot.id = cur.lastrowid
        return snapshot

    def get_latest_snapshot(self, target_id: int) -> Snapshot | None:
        row = self._conn.execute(
            "SELECT * FROM snapshots WHERE target_id = ? ORDER BY timestamp DESC LIMIT 1",
            (target_id,),
        ).fetchone()
        return self._row_to_snapshot(row) if row else None

    def get_snapshots(self, target_id: int, limit: int = 10) -> list[Snapshot]:
        rows = self._conn.execute(
            "SELECT * FROM snapshots WHERE target_id = ? ORDER BY timestamp DESC LIMIT ?",
            (target_id, limit),
        ).fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_target(row: sqlite3.Row) -> Target:
        headers_raw = row["headers"]
        return Target(
            id=row["id"],
            url=row["url"],
            name=row["name"],
            selector=row["selector"],
            interval_minutes=row["interval_minutes"],
            headers=json.loads(headers_raw) if headers_raw else None,
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> Snapshot:
        return Snapshot(
            id=row["id"],
            target_id=row["target_id"],
            content=row["content"],
            content_hash=row["content_hash"],
            status_code=row["status_code"],
            timestamp=row["timestamp"],
        )
