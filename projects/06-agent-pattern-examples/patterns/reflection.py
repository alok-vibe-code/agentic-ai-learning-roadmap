"""Reflection pattern: critique -> revise -> stop.

The implementation is deterministic so the control loop can be inspected
without an LLM. It deliberately bounds the number of revision rounds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from models import PatternTrace


@dataclass(frozen=True)
class Critique:
    issues: tuple[str, ...]
    score: int

    @property
    def passed(self) -> bool:
        return self.score >= 80 and not self.issues


def critique_text(text: str) -> Critique:
    stripped = " ".join(text.strip().split())
    if not stripped:
        return Critique(("empty",), 0)

    issues: list[str] = []
    words = re.findall(r"[A-Za-z0-9'-]+", stripped)

    if len(words) < 8:
        issues.append("too_short")
    if stripped[-1:] not in ".!?":
        issues.append("missing_terminal_punctuation")
    if not re.search(r"\b(because|so that|which|therefore|helps?|allows?)\b", stripped, re.I):
        issues.append("weak_explanation")
    if re.search(r"\b(very|really|basically|obviously)\b", stripped, re.I):
        issues.append("filler_words")
    if len(words) != len({word.casefold() for word in words}) and len(words) < 18:
        issues.append("repetition")

    score = max(0, 100 - 20 * len(issues))
    return Critique(tuple(issues), score)


def revise_text(text: str, critique: Critique) -> str:
    revised = " ".join(text.strip().split())

    if "filler_words" in critique.issues:
        revised = re.sub(
            r"\b(very|really|basically|obviously)\b\s*",
            "",
            revised,
            flags=re.I,
        ).strip()

    if "repetition" in critique.issues:
        words = revised.split()
        deduped: list[str] = []
        for word in words:
            if not deduped or word.casefold() != deduped[-1].casefold():
                deduped.append(word)
        revised = " ".join(deduped)

    if "too_short" in critique.issues:
        if revised and revised[-1:] in ".!?":
            revised = revised[:-1]
        revised += (
            " because a bounded review loop can identify predictable quality "
            "problems before the result is accepted"
        )

    if "weak_explanation" in critique.issues and "because" not in revised.casefold():
        if revised and revised[-1:] in ".!?":
            revised = revised[:-1]
        revised += (
            " because explicit critique makes the reason for each revision visible"
        )

    revised = " ".join(revised.split()).strip()
    if revised and revised[-1:] not in ".!?":
        revised += "."
    return revised


def run_reflection(
    draft: str,
    max_rounds: int = 3,
) -> tuple[str, PatternTrace]:
    if max_rounds < 1:
        raise ValueError("max_rounds must be >= 1.")

    current = draft
    trace = PatternTrace(pattern="reflection")

    for step in range(1, max_rounds + 1):
        critique = critique_text(current)
        trace.add(
            step,
            "critique",
            score=critique.score,
            issues=list(critique.issues),
        )

        if critique.passed:
            trace.stop_reason = "quality_threshold_met"
            return current, trace

        revised = revise_text(current, critique)
        trace.add(step, "revise", changed=revised != current)
        current = revised

    final = critique_text(current)
    trace.add(
        max_rounds + 1,
        "final_check",
        score=final.score,
        issues=list(final.issues),
    )
    trace.stop_reason = (
        "quality_threshold_met"
        if final.passed
        else "max_rounds_reached"
    )
    return current, trace
