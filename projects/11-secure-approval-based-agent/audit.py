from __future__ import annotations
import hashlib, json, time
from models import AuditEvent, Principal

class AuditLog:
    def __init__(self, *, clock=time.time) -> None:
        self.clock = clock
        self._events: list[AuditEvent] = []

    def append(self, principal: Principal, event_type: str, *, action_type: str | None, outcome: str, details: dict | None = None) -> AuditEvent:
        sequence = len(self._events) + 1
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        timestamp = float(self.clock())
        clean_details = dict(details or {})
        serialized = json.dumps({
            "sequence": sequence, "timestamp": timestamp,
            "principal_id": principal.id, "event_type": event_type,
            "action_type": action_type, "outcome": outcome,
            "details": clean_details, "previous_hash": previous_hash,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        event_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        event = AuditEvent(
            sequence, timestamp, principal.id, event_type, action_type,
            outcome, clean_details, previous_hash, event_hash
        )
        self._events.append(event)
        return event

    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def verify_chain(self) -> tuple[bool, str]:
        previous_hash = "GENESIS"
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence:
                return False, "Audit sequence is invalid."
            if event.previous_hash != previous_hash:
                return False, "Audit hash chain is broken."
            serialized = json.dumps({
                "sequence": event.sequence, "timestamp": event.timestamp,
                "principal_id": event.principal_id, "event_type": event.event_type,
                "action_type": event.action_type, "outcome": event.outcome,
                "details": event.details, "previous_hash": event.previous_hash,
            }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if event.event_hash != hashlib.sha256(serialized.encode("utf-8")).hexdigest():
                return False, "Audit event hash does not match content."
            previous_hash = event.event_hash
        return True, "Audit chain is valid."
