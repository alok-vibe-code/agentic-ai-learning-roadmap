"""High-level memory-aware assistant behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from models import MemoryMatch, MemoryRecord
from store import JSONMemoryStore


@dataclass
class WorkingMemory:
    """Ephemeral session memory. Never written to persistent storage."""

    items: dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: str) -> None:
        normalized = " ".join(key.strip().split()).casefold()
        if not normalized:
            raise ValueError("Working-memory key cannot be empty.")
        self.items[normalized] = " ".join(value.strip().split())

    def get(self, key: str) -> str | None:
        normalized = " ".join(key.strip().split()).casefold()
        return self.items.get(normalized)

    def clear(self) -> None:
        self.items.clear()


class MemoryAwareAssistant:
    def __init__(self, store: JSONMemoryStore):
        self.store = store
        self.working = WorkingMemory()

    def remember(
        self,
        category: str,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
        now: datetime | None = None,
    ) -> str:
        record, created = self.store.upsert(
            category=category,
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            now=now,
        )
        action = "Saved" if created else "Updated"
        expiry = (
            f" Expires at {record.expires_at}."
            if record.expires_at
            else ""
        )
        return (
            f"{action} memory [{record.category}] "
            f"{record.key} = {record.value}.{expiry}"
        )

    def recall(
        self,
        query: str,
        top_k: int = 5,
        now: datetime | None = None,
    ) -> list[MemoryMatch]:
        return self.store.search(query, top_k=top_k, now=now)

    def forget(self, category: str, key: str) -> str:
        deleted = self.store.delete(category, key)
        return (
            "Memory deleted."
            if deleted
            else "No matching persistent memory found."
        )

    def clear_persistent_memory(self) -> str:
        count = self.store.clear()
        return f"Cleared {count} persistent memory record(s)."
