"""Planning pattern: decompose a goal into validated dependency-aware steps."""

from __future__ import annotations

import re

from models import PatternTrace, PlanStep


def build_plan(goal: str) -> tuple[list[PlanStep], PatternTrace]:
    normalized = " ".join(goal.strip().split())
    if not normalized:
        raise ValueError("Goal cannot be empty.")

    trace = PatternTrace(pattern="planning")
    lowered = normalized.casefold()

    steps: list[PlanStep] = [
        PlanStep("P1", f"Clarify success criteria for: {normalized}"),
    ]

    if any(term in lowered for term in ("research", "compare", "evaluate", "learn")):
        steps.append(
            PlanStep(
                "P2",
                "Gather relevant evidence and constraints",
                ("P1",),
            )
        )
        steps.append(
            PlanStep(
                "P3",
                "Compare findings against the success criteria",
                ("P2",),
            )
        )
    elif any(term in lowered for term in ("build", "create", "implement", "develop")):
        steps.append(
            PlanStep(
                "P2",
                "Define the smallest testable implementation",
                ("P1",),
            )
        )
        steps.append(
            PlanStep(
                "P3",
                "Implement the smallest testable version",
                ("P2",),
            )
        )
        steps.append(
            PlanStep(
                "P4",
                "Test expected behavior and failure cases",
                ("P3",),
            )
        )
    else:
        steps.append(
            PlanStep(
                "P2",
                "Identify required inputs and constraints",
                ("P1",),
            )
        )
        steps.append(
            PlanStep(
                "P3",
                "Execute the task and verify the result",
                ("P2",),
            )
        )

    last_id = steps[-1].id
    final_id = f"P{len(steps) + 1}"
    steps.append(
        PlanStep(
            final_id,
            "Review the result and record the next action",
            (last_id,),
        )
    )

    validate_plan(steps)
    trace.add(
        1,
        "decompose",
        goal=normalized,
        step_count=len(steps),
    )
    trace.add(
        2,
        "validate",
        acyclic=True,
        dependency_count=sum(len(step.depends_on) for step in steps),
    )
    trace.stop_reason = "valid_plan_created"
    return steps, trace


def validate_plan(steps: list[PlanStep]) -> None:
    if not steps:
        raise ValueError("Plan must contain at least one step.")

    ids = [step.id for step in steps]
    if len(ids) != len(set(ids)):
        raise ValueError("Plan step IDs must be unique.")

    by_id = {step.id: step for step in steps}

    for step in steps:
        for dependency in step.depends_on:
            if dependency not in by_id:
                raise ValueError(
                    f"Unknown dependency {dependency!r} for step {step.id}."
                )
            if dependency == step.id:
                raise ValueError(f"Step {step.id} cannot depend on itself.")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visited:
            return
        if step_id in visiting:
            raise ValueError("Plan contains a dependency cycle.")
        visiting.add(step_id)
        for dependency in by_id[step_id].depends_on:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in ids:
        visit(step_id)
