"""Structured logs, metrics, and trace IDs."""

from __future__ import annotations

from collections import defaultdict
import json
import uuid


class MetricsRegistry:
    def __init__(self) -> None:
        self._values: dict[str, float] = defaultdict(float)

    def inc(self, name: str, value: float = 1.0) -> None:
        self._values[name] += value

    def set(self, name: str, value: float) -> None:
        self._values[name] = value

    def snapshot(self) -> dict[str, int | float]:
        result: dict[str, int | float] = {}
        for key, value in sorted(self._values.items()):
            result[key] = int(value) if value.is_integer() else round(value, 8)
        return result


class StructuredLogger:
    def __init__(self, *, echo: bool = False) -> None:
        self.echo = echo
        self.records: list[dict] = []

    def emit(self, event: str, *, trace_id: str, **fields) -> dict:
        record = {
            "event": event,
            "trace_id": trace_id,
            **fields,
        }
        self.records.append(record)
        if self.echo:
            print(json.dumps(record, sort_keys=True, ensure_ascii=False))
        return record


def new_trace_id() -> str:
    return uuid.uuid4().hex
