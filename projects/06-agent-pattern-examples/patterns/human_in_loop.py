"""Human-in-the-loop pattern: risk classification + explicit approval gate.

This demo never performs real external side effects. It only returns an
execution decision so the approval boundary is safe to inspect.
"""

from __future__ import annotations

import re

from models import ApprovalDecision, PatternTrace


_HIGH_RISK = {
    "send", "email", "publish", "delete", "remove", "purchase", "buy",
    "pay", "transfer", "deploy", "modify", "write", "post", "submit",
}
_LOW_RISK = {
    "read", "search", "calculate", "inspect", "summarize", "list", "view",
}


def classify_risk(action: str) -> tuple[str, str]:
    normalized = " ".join(action.strip().split())
    if not normalized:
        raise ValueError("Action cannot be empty.")

    terms = set(re.findall(r"[a-z0-9_-]+", normalized.casefold()))

    if terms & _HIGH_RISK:
        return "high", "Action may create, modify, publish, send, delete, or spend."
    if terms & _LOW_RISK:
        return "low", "Action is read-only or computational."
    return "medium", "Risk is ambiguous; require human approval by default."


def request_action(
    action: str,
    approved: bool = False,
) -> tuple[ApprovalDecision, PatternTrace]:
    risk, reason = classify_risk(action)
    trace = PatternTrace(pattern="human-in-the-loop")
    trace.add(1, "classify_risk", risk=risk, reason=reason)

    if risk == "low":
        decision = ApprovalDecision(
            action=action,
            risk=risk,
            approved=True,
            reason="Low-risk action is allowed automatically.",
        )
        trace.add(2, "decision", approved=True, approval_required=False)
        trace.stop_reason = "auto_approved_low_risk"
        return decision, trace

    if not approved:
        decision = ApprovalDecision(
            action=action,
            risk=risk,
            approved=False,
            reason="Explicit human approval is required before execution.",
        )
        trace.add(2, "decision", approved=False, approval_required=True)
        trace.stop_reason = "waiting_for_human_approval"
        return decision, trace

    decision = ApprovalDecision(
        action=action,
        risk=risk,
        approved=True,
        reason="Human approval was explicitly supplied.",
    )
    trace.add(2, "decision", approved=True, approval_required=True)
    trace.stop_reason = "human_approved"
    return decision, trace


def simulate_execution(decision: ApprovalDecision) -> str:
    if not decision.approved:
        return "BLOCKED: action was not approved."
    return (
        f"SIMULATED ONLY: approved {decision.risk}-risk action "
        f"would execute here: {decision.action}"
    )
