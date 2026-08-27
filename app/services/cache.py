import time
from typing import Protocol


class CacheBackend[T](Protocol):
    def get(self, key: str) -> T | None: ...

    def set(self, key: str, value: T, ttl_seconds: int) -> None: ...


class InMemoryTTLCache[T]:
    """Simple in-memory TTL cache keyed by slug."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[T, float]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: T, ttl_seconds: int) -> None:
        expires_at = time.monotonic() + ttl_seconds
        self._store[key] = (value, expires_at)

    def clear(self) -> None:
        self._store.clear()
