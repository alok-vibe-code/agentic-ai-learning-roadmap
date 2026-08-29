"""Data models for Project 07: Framework Comparison Demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CAPABILITY_KEYS = (
    "state_management",
    "tool_calling",
    "structured_outputs",
    "human_approval",
    "tracing",
    "mcp",
    "multi_agent",
    "provider_flexibility",
    "durable_execution",
    "offline_testing",
)

CAPABILITY_STATUSES = {
    "native",
    "supported",
    "strong",
    "integration",
    "provider-dependent",
    "limited",
    "not-core",
}


@dataclass(frozen=True)
class FrameworkProfile:
    id: str
    name: str
    kind: str
    verified_date: str
    docs_url: str
    install: str
    runtime_note: str
    capabilities: dict[str, str]
    task_mapping: dict[str, str]
    strengths: tuple[str, ...]
    watch_items: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FrameworkProfile":
        capabilities = dict(payload["capabilities"])
        missing = set(CAPABILITY_KEYS) - set(capabilities)
        extra = set(capabilities) - set(CAPABILITY_KEYS)
        if missing or extra:
            raise ValueError(
                f"Invalid capability keys for {payload.get('id')}: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )

        invalid = {
            key: value
            for key, value in capabilities.items()
            if value not in CAPABILITY_STATUSES
        }
        if invalid:
            raise ValueError(
                f"Invalid capability status values: {invalid}"
            )

        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            kind=str(payload["kind"]),
            verified_date=str(payload["verified_date"]),
            docs_url=str(payload["docs_url"]),
            install=str(payload["install"]),
            runtime_note=str(payload["runtime_note"]),
            capabilities=capabilities,
            task_mapping=dict(payload["task_mapping"]),
            strengths=tuple(payload["strengths"]),
            watch_items=tuple(payload["watch_items"]),
        )


@dataclass(frozen=True)
class SupportTriageResult:
    route: str
    risk: str
    requires_human: bool
    next_action: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Recommendation:
    framework_id: str
    framework_name: str
    eligible: bool
    preference_score: int
    matched_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    matched_preferences: tuple[str, ...]
