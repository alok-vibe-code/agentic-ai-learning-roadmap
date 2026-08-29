from __future__ import annotations
import re
from models import GuardrailResult

INJECTION_PATTERNS = (
    r"\bignore (?:all|any|the|previous|prior) instructions\b",
    r"\bsystem prompt\b",
    r"\bdeveloper message\b",
    r"\breveal (?:your )?(?:prompt|instructions|secrets?)\b",
    r"\bdisable (?:security|guardrails?|policy)\b",
    r"\bbypass (?:approval|authorization|policy|security)\b",
)
SECRET_PATTERNS = (
    r"\bsk-[A-Za-z0-9_-]{12,}\b",
    r"\b(?:api[_ -]?key|password|secret|token)\s*[:=]\s*\S+",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
)
MALICIOUS_TOOL_OUTPUT_PATTERNS = (
    r"\bignore (?:all|previous|prior) instructions\b",
    r"\bexecute this command\b",
    r"\bexfiltrate\b",
    r"\breveal secrets?\b",
)

def _signals(text: str, patterns: tuple[str, ...], prefix: str) -> list[str]:
    return [
        f"{prefix}_{i}"
        for i, pattern in enumerate(patterns, start=1)
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]

def inspect_user_input(text: str, *, max_chars: int) -> GuardrailResult:
    if not isinstance(text, str):
        return GuardrailResult(False, "Input must be a string.", ("invalid_type",))
    normalized = " ".join(text.split())
    if not normalized:
        return GuardrailResult(False, "Input cannot be empty.", ("empty",))
    if len(normalized) > max_chars:
        return GuardrailResult(False, f"Input exceeds the {max_chars}-character limit.", ("too_long",))
    signals = _signals(normalized, INJECTION_PATTERNS, "injection")
    signals += _signals(normalized, SECRET_PATTERNS, "secret")
    if any(s.startswith("secret_") for s in signals):
        return GuardrailResult(False, "Potential secret or credential data was detected.", tuple(signals))
    if any(s.startswith("injection_") for s in signals):
        return GuardrailResult(False, "Prompt-injection-like instructions were detected.", tuple(signals))
    return GuardrailResult(True, "Input passed guardrail checks.", ())

def inspect_tool_output(text: str) -> GuardrailResult:
    if not isinstance(text, str):
        return GuardrailResult(False, "Tool output must be text in this demo.", ("invalid_tool_output",))
    signals = _signals(text, MALICIOUS_TOOL_OUTPUT_PATTERNS, "tool_injection")
    if signals:
        return GuardrailResult(False, "Untrusted tool output contains instruction-like content.", tuple(signals))
    return GuardrailResult(True, "Tool output passed guardrail checks.", ())
