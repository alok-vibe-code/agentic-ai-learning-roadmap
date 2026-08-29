"""Small vendor-neutral trace collector for the demo."""

from __future__ import annotations
from hashlib import sha256
from models import MutableTrace, TraceEvent


class TraceCollector:
    def __init__(self, seed: str) -> None:
        digest = sha256(seed.encode("utf-8")).hexdigest()[:16]
        self._trace = MutableTrace(trace_id=f"trace-{digest}")
        self._span_counter = 0

    @property
    def trace_id(self) -> str:
        return self._trace.trace_id

    def span_id(self) -> str:
        self._span_counter += 1
        return f"span-{self._span_counter:03d}"

    def record(
        self,
        *,
        span_id: str,
        parent_span_id: str | None,
        kind: str,
        name: str,
        **attributes,
    ) -> None:
        self._trace.events.append(
            TraceEvent(
                sequence=len(self._trace.events) + 1,
                trace_id=self.trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                kind=kind,
                name=name,
                attributes=dict(attributes),
            )
        )

    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._trace.events)


def validate_trace(events: tuple[TraceEvent, ...]) -> tuple[bool, str]:
    if not events:
        return False, "trace is empty"

    trace_ids = {event.trace_id for event in events}
    if len(trace_ids) != 1:
        return False, "multiple trace IDs found"

    sequences = [event.sequence for event in events]
    if sequences != list(range(1, len(events) + 1)):
        return False, "event sequence is not contiguous"

    span_ids = {event.span_id for event in events}
    roots = [event for event in events if event.parent_span_id is None]
    if not roots:
        return False, "trace has no root span"

    for event in events:
        if event.parent_span_id is not None and event.parent_span_id not in span_ids:
            return False, f"missing parent span for {event.name}"

    kinds = {event.kind for event in events}
    if "run" not in kinds:
        return False, "trace has no run event"

    return True, "trace structure is valid"
