"""Capability matrix and requirement-based comparison logic."""

from __future__ import annotations

from models import (
    CAPABILITY_KEYS,
    FrameworkProfile,
    Recommendation,
)


STATUS_STRENGTH = {
    "native": 4,
    "strong": 4,
    "supported": 3,
    "integration": 2,
    "provider-dependent": 1,
    "limited": 1,
    "not-core": 0,
}

# Hard requirements accept statuses at or above this level.
HARD_REQUIREMENT_MIN = 2


def normalize_capability(value: str) -> str:
    normalized = value.strip().casefold().replace("-", "_")
    aliases = {
        "state": "state_management",
        "tools": "tool_calling",
        "tool": "tool_calling",
        "structured": "structured_outputs",
        "structured_output": "structured_outputs",
        "hitl": "human_approval",
        "human_in_the_loop": "human_approval",
        "multiagent": "multi_agent",
        "multi_agent_systems": "multi_agent",
        "provider": "provider_flexibility",
        "providers": "provider_flexibility",
        "durable": "durable_execution",
        "offline": "offline_testing",
        "testing": "offline_testing",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in CAPABILITY_KEYS:
        raise ValueError(
            f"Unknown capability {value!r}. Choose from: "
            + ", ".join(CAPABILITY_KEYS)
        )
    return normalized


def evaluate_framework(
    profile: FrameworkProfile,
    required: list[str] | tuple[str, ...] = (),
    preferred: list[str] | tuple[str, ...] = (),
) -> Recommendation:
    required_norm = tuple(
        dict.fromkeys(normalize_capability(item) for item in required)
    )
    preferred_norm = tuple(
        dict.fromkeys(normalize_capability(item) for item in preferred)
    )

    matched_required: list[str] = []
    missing_required: list[str] = []

    for capability in required_norm:
        strength = STATUS_STRENGTH[profile.capabilities[capability]]
        if strength >= HARD_REQUIREMENT_MIN:
            matched_required.append(capability)
        else:
            missing_required.append(capability)

    matched_preferences = [
        capability
        for capability in preferred_norm
        if STATUS_STRENGTH[profile.capabilities[capability]] >= 2
    ]

    preference_score = sum(
        STATUS_STRENGTH[profile.capabilities[capability]]
        for capability in preferred_norm
    )

    return Recommendation(
        framework_id=profile.id,
        framework_name=profile.name,
        eligible=not missing_required,
        preference_score=preference_score,
        matched_requirements=tuple(matched_required),
        missing_requirements=tuple(missing_required),
        matched_preferences=tuple(matched_preferences),
    )


def recommend(
    profiles: list[FrameworkProfile],
    required: list[str] | tuple[str, ...] = (),
    preferred: list[str] | tuple[str, ...] = (),
) -> list[Recommendation]:
    recommendations = [
        evaluate_framework(profile, required, preferred)
        for profile in profiles
    ]
    recommendations.sort(
        key=lambda item: (
            not item.eligible,
            -item.preference_score,
            item.framework_name.casefold(),
        )
    )
    return recommendations


def capability_matrix(
    profiles: list[FrameworkProfile],
) -> list[list[str]]:
    rows: list[list[str]] = []
    for capability in CAPABILITY_KEYS:
        rows.append(
            [capability]
            + [
                profile.capabilities[capability]
                for profile in profiles
            ]
        )
    return rows
