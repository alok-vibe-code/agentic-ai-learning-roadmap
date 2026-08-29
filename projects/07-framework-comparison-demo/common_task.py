"""A framework-neutral support-triage task.

The task is intentionally deterministic so every framework can be discussed
against the same behavior without paying for or depending on an LLM.
"""

from __future__ import annotations

import re

from models import SupportTriageResult


ROUTE_KEYWORDS = {
    "billing": {
        "billing", "invoice", "refund", "payment", "charged", "charge",
        "subscription", "price", "pricing"
    },
    "technical": {
        "bug", "error", "api", "timeout", "crash", "broken",
        "integration", "webhook", "exception"
    },
    "account": {
        "account", "login", "sign-in", "signin", "access", "username",
        "profile"
    },
}

SENSITIVE_ACTION_TERMS = {
    "refund",
    "delete",
    "remove",
    "cancel",
    "chargeback",
    "transfer",
    "reset password",
    "change email",
}


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", text.casefold()))


def triage_request(request: str) -> SupportTriageResult:
    normalized = " ".join(request.strip().split())
    if not normalized:
        raise ValueError("Request cannot be empty.")

    terms = tokenize(normalized)
    scores = {
        route: len(terms & keywords)
        for route, keywords in ROUTE_KEYWORDS.items()
    }

    best_score = max(scores.values())
    winners = [
        route for route, score in scores.items()
        if score == best_score and score > 0
    ]

    if len(winners) == 1:
        route = winners[0]
        route_reason = f"Matched {best_score} {route} keyword(s)."
    else:
        route = "general"
        route_reason = (
            "No unique specialist route matched."
            if not winners
            else "Multiple specialist routes tied; use general triage."
        )

    lowered = normalized.casefold()
    matched_sensitive = sorted(
        term for term in SENSITIVE_ACTION_TERMS
        if term in lowered
    )
    requires_human = bool(matched_sensitive)

    risk = "high" if requires_human else "low"
    if requires_human:
        next_action = (
            f"Route to {route} specialist, prepare context, and request "
            "human approval before the sensitive action."
        )
        risk_reason = (
            "Sensitive action term(s): " + ", ".join(matched_sensitive)
        )
    else:
        next_action = (
            f"Route to {route} specialist and continue with a read-only "
            "diagnostic or informational response."
        )
        risk_reason = "No configured sensitive action was detected."

    return SupportTriageResult(
        route=route,
        risk=risk,
        requires_human=requires_human,
        next_action=next_action,
        reasons=(route_reason, risk_reason),
    )
