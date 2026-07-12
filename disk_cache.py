"""Persistent disk cache backed by SQLite.

Stores cached results in ~/.factanchor/cache.db so they survive MCP server
restarts. Falls back gracefully to in-memory only if SQLite is unavailable.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

_DEFAULT_TTL = 86400  # 24 hours
_MAX_ENTRIES = 500


class DiskCache:
    """SQLite-backed cache with TTL expiration."""

    def __init__(self, cache_dir: str | Path | None = None, ttl: int = _DEFAULT_TTL):
        if cache_dir is None:
            cache_dir = Path.home() / ".factanchor"
        self._dir = Path(cache_dir)
        self._ttl = ttl
        self._db_path = self._dir / "cache.db"
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path), timeout=5)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "  key TEXT PRIMARY KEY,"
                "  value TEXT NOT NULL,"
                "  ts REAL NOT NULL"
                ")"
            )
            self._conn.commit()
            # Prune expired entries on startup
            self._conn.execute(
                "DELETE FROM cache WHERE ? - ts > ?",
                (time.time(), self._ttl),
            )
            # Enforce max entries
            self._conn.execute(
                "DELETE FROM cache WHERE key NOT IN "
                "  (SELECT key FROM cache ORDER BY ts DESC LIMIT ?)",
                (_MAX_ENTRIES,),
            )
            self._conn.commit()
        except Exception:
            self._conn = None

    def get(self, key: str) -> str | None:
        if self._conn is None:
            return None
        try:
            row = self._conn.execute(
                "SELECT value, ts FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            value, ts = row
            if (time.time() - ts) > self._ttl:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()
                return None
            return value
        except Exception:
            return None

    def set(self, key: str, value: str) -> None:
        if self._conn is None:
            return
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)",
                (key, value, time.time()),
            )
            self._conn.commit()
        except Exception:
            pass

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


# Module-level singleton (created lazily)
_disk_cache: DiskCache | None = None


def _get_disk_cache() -> DiskCache:
    global _disk_cache
    if _disk_cache is None:
        _disk_cache = DiskCache()
    return _disk_cache


def disk_get(query: str, count: int) -> str | None:
    """Retrieve cached result for a query+count pair."""
    key = f"{query}||{count}"
    return _get_disk_cache().get(key)


def disk_set(query: str, count: int, value: str) -> None:
    """Store result for a query+count pair."""
    key = f"{query}||{count}"
    _get_disk_cache().set(key, value)
