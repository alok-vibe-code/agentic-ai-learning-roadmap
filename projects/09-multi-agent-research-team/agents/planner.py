"""Planner agent."""

from __future__ import annotations
from models import ResearchPlan, ResearchTask
from search import tokenize

MAX_QUESTION_CHARS = 1_500
MAX_TASKS = 4

FACETS = (
    ("architecture", {"architecture", "design", "system", "workflow", "agent"}),
    ("benefits", {"benefit", "advantages", "value", "useful", "strength"}),
    ("risks", {"risk", "failure", "problem", "drawback", "weakness"}),
    ("reliability", {"reliability", "reliable", "failure", "quality", "review"}),
    ("coordination", {"coordination", "handoff", "message", "shared", "state"}),
    ("cost_complexity", {"cost", "complexity", "overhead", "simple", "simpler"}),
    ("parallelism", {"parallel", "latency", "concurrent", "independent"}),
    ("decision", {"when", "choose", "decision", "worth", "versus", "vs", "compare"}),
)


def normalize_question(question: str) -> str:
    if not isinstance(question, str):
        raise TypeError("question must be a string.")
    normalized = " ".join(question.split())
    if not normalized:
        raise ValueError("question cannot be empty.")
    if len(normalized) > MAX_QUESTION_CHARS:
        raise ValueError(
            f"question exceeds the {MAX_QUESTION_CHARS}-character demo limit."
        )
    return normalized


def complexity_score(question: str) -> int:
    normalized = normalize_question(question)
    terms = tokenize(normalized)
    score = 0
    if len(terms) >= 8:
        score += 1
    if any(token in terms for token in {"compare", "versus", "vs"}):
        score += 2
    score += min(
        sum(bool(terms & keywords) for _, keywords in FACETS),
        4,
    )
    if " and " in normalized.casefold():
        score += 1
    return score


class PlannerAgent:
    name = "planner"

    def plan(self, question: str) -> ResearchPlan:
        normalized = normalize_question(question)
        terms = tokenize(normalized)

        selected: list[str] = []
        for facet, keywords in FACETS:
            if terms & keywords:
                selected.append(facet)

        if any(token in terms for token in {"compare", "versus", "vs"}):
            for facet in (
                "architecture",
                "reliability",
                "cost_complexity",
                "decision",
            ):
                if facet not in selected:
                    selected.append(facet)

        if not selected:
            selected = ["architecture", "decision"]

        selected = selected[:MAX_TASKS]
        tasks = tuple(
            ResearchTask(
                id=f"T{index}",
                facet=facet,
                query=f"{normalized} {facet.replace('_', ' ')}",
            )
            for index, facet in enumerate(selected, start=1)
        )

        score = complexity_score(normalized)
        return ResearchPlan(
            question=normalized,
            tasks=tasks,
            complexity_score=score,
            rationale=(
                f"Decomposed the question into {len(tasks)} bounded facet(s). "
                f"Complexity score: {score}."
            ),
        )
