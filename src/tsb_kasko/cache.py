"""A small time to live cache for TSB reference data.

Brand and model lists change rarely but are requested on nearly every lookup, so
caching them keeps the number of round trips to TSB low and keeps MCP tool calls
responsive.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class TtlCache:
    """A JSON backed cache whose entries expire after a fixed lifetime.

    Attributes:
        directory: Directory the cache files are written to.
        ttl: Entry lifetime in seconds.
        enabled: When false, every operation becomes a no-op.
    """

    def __init__(self, directory: Path, ttl: int, *, enabled: bool = True) -> None:
        """Initialise the cache.

        Args:
            directory: Directory the cache files are written to.
            ttl: Entry lifetime in seconds.
            enabled: When false, every operation becomes a no-op.
        """
        self.directory = directory
        self.ttl = ttl
        self.enabled = enabled
        self._memory: dict[str, tuple[float, Any]] = {}

    def _path(self, key: str) -> Path:
        """Resolve the file backing a cache key.

        Args:
            key: Logical cache key.

        Returns:
            Path of the JSON file holding the entry.
        """
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.directory / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        """Read a cached value.

        Args:
            key: Logical cache key.

        Returns:
            The cached value, or ``None`` when absent or expired.
        """
        if not self.enabled:
            return None
        now = time.time()
        hit = self._memory.get(key)
        if hit is not None and hit[0] > now:
            return hit[1]
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        expires_at = float(payload.get("expires_at", 0))
        if expires_at <= now:
            return None
        value = payload.get("value")
        self._memory[key] = (expires_at, value)
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache.

        Args:
            key: Logical cache key.
            value: JSON serialisable value to persist.
        """
        if not self.enabled:
            return
        expires_at = time.time() + self.ttl
        self._memory[key] = (expires_at, value)
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._path(key).write_text(
                json.dumps({"expires_at": expires_at, "value": value}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            return

    def clear(self) -> int:
        """Remove every persisted entry.

        Returns:
            The number of cache files removed.
        """
        self._memory.clear()
        if not self.directory.is_dir():
            return 0
        removed = 0
        for path in self.directory.glob("*.json"):
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
        return removed
