"""Persistent JSON memory store with bounded size and atomic writes."""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from models import MemoryMatch, MemoryRecord, to_iso, utc_now
from policy import (
    MAX_RECORDS,
    normalize_category,
    normalize_key,
    validate_memory_content,
)


_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", re.I)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "for", "from", "how",
    "i", "in", "is", "it", "my", "of", "on", "or", "the", "to", "what",
    "which", "with"
}


def tokenize(text: str) -> list[str]:
    return [
        token.casefold()
        for token in _TOKEN_RE.findall(text)
        if token.casefold() not in _STOPWORDS and len(token) > 1
    ]


def default_store_path() -> Path:
    return (
        Path.home()
        / ".agentic-ai-learning-roadmap"
        / "project05-memory.json"
    )


class JSONMemoryStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_store_path()

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_raw(self) -> list[dict]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Memory store is corrupted and was not overwritten: {self.path}"
            ) from exc

        if not isinstance(payload, list):
            raise ValueError("Memory store must contain a JSON list.")
        return payload

    def _load_records(self) -> list[MemoryRecord]:
        return [MemoryRecord.from_dict(item) for item in self._load_raw()]

    def _write_records(self, records: list[MemoryRecord]) -> None:
        self._ensure_parent()
        payload = [record.to_dict() for record in records]
        serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

        fd, temp_name = tempfile.mkstemp(
            prefix=".memory-",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())

            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass

            os.replace(temp_name, self.path)

            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def purge_expired(
        self,
        now: datetime | None = None,
    ) -> int:
        current = now or utc_now()
        records = self._load_records()
        kept = [record for record in records if not record.is_expired(current)]
        removed = len(records) - len(kept)
        if removed:
            self._write_records(kept)
        return removed

    def list_records(
        self,
        category: str | None = None,
        now: datetime | None = None,
    ) -> list[MemoryRecord]:
        current = now or utc_now()
        records = [
            record
            for record in self._load_records()
            if not record.is_expired(current)
        ]

        if category is not None:
            normalized = normalize_category(category)
            records = [
                record for record in records
                if record.category == normalized
            ]

        records.sort(
            key=lambda record: (
                record.category,
                record.key,
                record.created_at,
            )
        )
        return records

    def upsert(
        self,
        category: str,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
        now: datetime | None = None,
    ) -> tuple[MemoryRecord, bool]:
        normalized_category = normalize_category(category)
        normalized_key = normalize_key(key)
        decision = validate_memory_content(normalized_key, value)
        if not decision.allowed:
            raise ValueError(decision.reason)

        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero.")

        current = now or utc_now()
        active_records = [
            record
            for record in self._load_records()
            if not record.is_expired(current)
        ]

        expires_at = (
            to_iso(current + timedelta(seconds=ttl_seconds))
            if ttl_seconds is not None
            else None
        )

        for index, record in enumerate(active_records):
            if (
                record.category == normalized_category
                and record.key == normalized_key
            ):
                updated = MemoryRecord(
                    id=record.id,
                    category=record.category,
                    key=record.key,
                    value=" ".join(value.strip().split()),
                    created_at=record.created_at,
                    updated_at=to_iso(current),
                    expires_at=expires_at,
                    source="explicit-user-command",
                )
                active_records[index] = updated
                self._write_records(active_records)
                return updated, False

        if len(active_records) >= MAX_RECORDS:
            raise ValueError(
                f"Memory store limit reached ({MAX_RECORDS} active records)."
            )

        created = MemoryRecord(
            id=str(uuid.uuid4()),
            category=normalized_category,
            key=normalized_key,
            value=" ".join(value.strip().split()),
            created_at=to_iso(current),
            updated_at=to_iso(current),
            expires_at=expires_at,
            source="explicit-user-command",
        )
        active_records.append(created)
        self._write_records(active_records)
        return created, True

    def get(
        self,
        category: str,
        key: str,
        now: datetime | None = None,
    ) -> MemoryRecord | None:
        normalized_category = normalize_category(category)
        normalized_key = normalize_key(key)
        current = now or utc_now()

        for record in self._load_records():
            if (
                record.category == normalized_category
                and record.key == normalized_key
                and not record.is_expired(current)
            ):
                return record
        return None

    def search(
        self,
        query: str,
        top_k: int = 5,
        now: datetime | None = None,
    ) -> list[MemoryMatch]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1.")

        query_terms = set(tokenize(query))
        if not query_terms:
            return []

        matches: list[MemoryMatch] = []
        for record in self.list_records(now=now):
            key_terms = set(tokenize(record.key))
            value_terms = set(tokenize(record.value))
            category_terms = set(tokenize(record.category))

            matched = (
                (query_terms & key_terms)
                | (query_terms & value_terms)
                | (query_terms & category_terms)
            )
            if not matched:
                continue

            score = (
                3.0 * len(query_terms & key_terms)
                + 1.5 * len(query_terms & value_terms)
                + 1.0 * len(query_terms & category_terms)
            )
            score += 0.1 * len(matched)

            matches.append(
                MemoryMatch(
                    record=record,
                    score=score,
                    matched_terms=tuple(sorted(matched)),
                )
            )

        matches.sort(
            key=lambda match: (
                -match.score,
                match.record.category,
                match.record.key,
            )
        )
        return matches[:top_k]

    def delete(self, category: str, key: str) -> bool:
        normalized_category = normalize_category(category)
        normalized_key = normalize_key(key)
        records = self._load_records()

        kept = [
            record
            for record in records
            if not (
                record.category == normalized_category
                and record.key == normalized_key
            )
        ]
        if len(kept) == len(records):
            return False

        self._write_records(kept)
        return True

    def clear(self) -> int:
        records = self._load_records()
        count = len(records)
        self._write_records([])
        return count
