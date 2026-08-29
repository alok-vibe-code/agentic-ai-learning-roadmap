"""Memory write policy and privacy guardrails.

This is intentionally conservative and educational. It is not a complete
data-loss-prevention or secrets-classification system.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


ALLOWED_CATEGORIES = {
    "preference",
    "project",
    "workflow",
    "episode",
}

MAX_KEY_LENGTH = 80
MAX_VALUE_LENGTH = 500
MAX_RECORDS = 200

_SENSITIVE_PATTERNS = [
    (
        "credential",
        re.compile(
            r"\b(password|passcode|pin code|api[_ -]?key|access[_ -]?token|"
            r"refresh[_ -]?token|private[_ -]?key|client[_ -]?secret|secret key)\b",
            re.I,
        ),
    ),
    (
        "financial",
        re.compile(
            r"\b(credit card|debit card|cvv|bank account|routing number|"
            r"iban|swift code)\b",
            re.I,
        ),
    ),
    (
        "government_id",
        re.compile(
            r"\b(ssn|social security|aadhaar|aadhar|passport number|"
            r"driver'?s license number|tax identification number)\b",
            re.I,
        ),
    ),
    (
        "medical",
        re.compile(
            r"\b(diagnosed with|diagnosis|medical condition|prescription|"
            r"blood test|lab result|patient id)\b",
            re.I,
        ),
    ),
]

# Common secret-like token shapes. Kept deliberately narrow to avoid excessive
# false positives in an educational demo.
_SECRET_SHAPES = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


def normalize_category(category: str) -> str:
    normalized = category.strip().casefold().replace(" ", "-")
    if normalized not in ALLOWED_CATEGORIES:
        raise ValueError(
            "Unsupported category. Choose one of: "
            + ", ".join(sorted(ALLOWED_CATEGORIES))
        )
    return normalized


def normalize_key(key: str) -> str:
    normalized = " ".join(key.strip().split()).casefold()
    if not normalized:
        raise ValueError("Memory key cannot be empty.")
    if len(normalized) > MAX_KEY_LENGTH:
        raise ValueError(
            f"Memory key exceeds {MAX_KEY_LENGTH} characters."
        )
    return normalized


def validate_memory_content(key: str, value: str) -> PolicyDecision:
    normalized_key = " ".join(key.strip().split())
    normalized_value = " ".join(value.strip().split())

    if not normalized_value:
        return PolicyDecision(False, "Memory value cannot be empty.")
    if len(normalized_value) > MAX_VALUE_LENGTH:
        return PolicyDecision(
            False,
            f"Memory value exceeds {MAX_VALUE_LENGTH} characters."
        )

    combined = f"{normalized_key} {normalized_value}"

    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(combined):
            return PolicyDecision(
                False,
                f"Rejected by privacy policy: possible {label} data."
            )

    for pattern in _SECRET_SHAPES:
        if pattern.search(combined):
            return PolicyDecision(
                False,
                "Rejected by privacy policy: secret-like token detected."
            )

    return PolicyDecision(True, "Allowed non-sensitive memory.")
