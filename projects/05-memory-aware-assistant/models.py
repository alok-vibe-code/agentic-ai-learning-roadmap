"""Data models for Project 05: Memory-Aware Assistant."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def from_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass
class MemoryRecord:
    id: str
    category: str
    key: str
    value: str
    created_at: str
    updated_at: str
    expires_at: str | None
    source: str = "explicit-user-command"

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        current = now or utc_now()
        expiry = from_iso(self.expires_at)
        return bool(expiry and current >= expiry)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryRecord":
        required = {
            "id", "category", "key", "value",
            "created_at", "updated_at", "expires_at"
        }
        missing = required.difference(payload)
        if missing:
            raise ValueError(f"Memory record missing fields: {sorted(missing)}")

        return cls(
            id=str(payload["id"]),
            category=str(payload["category"]),
            key=str(payload["key"]),
            value=str(payload["value"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            expires_at=(
                None if payload["expires_at"] is None
                else str(payload["expires_at"])
            ),
            source=str(payload.get("source", "explicit-user-command")),
        )


@dataclass(frozen=True)
class MemoryMatch:
    record: MemoryRecord
    score: float
    matched_terms: tuple[str, ...]
