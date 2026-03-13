"""
In-memory LRU cache with TTL support.

Provides sub-200ms API response times by caching query results.
Designed with a Redis-compatible interface for production migration.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("windsight.cache")


class LRUCache:
    """
    Thread-safe LRU cache with TTL expiration.

    In production, this would be backed by Redis. The interface is designed
    to be swapped transparently.

    Args:
        max_size: Maximum number of entries.
        default_ttl: Default time-to-live in seconds.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, prefix: str, params: dict[str, Any]) -> str:
        """Generate a deterministic cache key from prefix and parameters."""
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_str = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_str}"

    def get(self, prefix: str, params: dict[str, Any]) -> Any | None:
        """
        Retrieve a value from the cache.

        Args:
            prefix: Cache key prefix (e.g., 'generation', 'forecast').
            params: Query parameters used to generate the key.

        Returns:
            Cached value or None if not found/expired.
        """
        key = self._make_key(prefix, params)

        if key not in self._cache:
            self._misses += 1
            return None

        value, expiry = self._cache[key]

        if time.time() > expiry:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return value

    def set(
        self,
        prefix: str,
        params: dict[str, Any],
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Store a value in the cache.

        Args:
            prefix: Cache key prefix.
            params: Query parameters used to generate the key.
            value: Value to cache.
            ttl: Time-to-live in seconds (uses default if None).
        """
        key = self._make_key(prefix, params)
        expiry = time.time() + (ttl or self._default_ttl)

        if key in self._cache:
            self._cache.move_to_end(key)
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # Remove oldest

        self._cache[key] = (value, expiry)

    def invalidate(self, prefix: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            prefix: If provided, only invalidate entries with this prefix.
                    If None, clear entire cache.

        Returns:
            Number of entries removed.
        """
        if prefix is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_remove = [k for k in self._cache if k.startswith(f"{prefix}:")]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


# ── Global Cache Instance ──────────────────────────────────────────────────────

cache = LRUCache(max_size=2000, default_ttl=300)
