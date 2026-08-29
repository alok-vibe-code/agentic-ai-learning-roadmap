"""Small LRU TTL cache with stale-if-error support."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from models import ProviderResponse


@dataclass
class CacheEntry:
    value: ProviderResponse
    stored_at_ms: float


class TTLCache:
    def __init__(self, ttl_ms: int, stale_ttl_ms: int, max_entries: int) -> None:
        if ttl_ms < 1 or stale_ttl_ms < ttl_ms or max_entries < 1:
            raise ValueError("Invalid cache configuration.")
        self.ttl_ms = ttl_ms
        self.stale_ttl_ms = stale_ttl_ms
        self.max_entries = max_entries
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()

    def set(self, key: str, value: ProviderResponse, now_ms: float) -> None:
        self._data.pop(key, None)
        self._data[key] = CacheEntry(value=value, stored_at_ms=now_ms)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)

    def get_fresh(self, key: str, now_ms: float) -> ProviderResponse | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        age = now_ms - entry.stored_at_ms
        if age <= self.ttl_ms:
            self._data.move_to_end(key)
            return entry.value
        return None

    def get_stale(self, key: str, now_ms: float) -> ProviderResponse | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        age = now_ms - entry.stored_at_ms
        if self.ttl_ms < age <= self.stale_ttl_ms:
            self._data.move_to_end(key)
            return entry.value
        return None

    def purge_expired(self, now_ms: float) -> int:
        expired = [
            key
            for key, entry in self._data.items()
            if now_ms - entry.stored_at_ms > self.stale_ttl_ms
        ]
        for key in expired:
            self._data.pop(key, None)
        return len(expired)

    def __len__(self) -> int:
        return len(self._data)
