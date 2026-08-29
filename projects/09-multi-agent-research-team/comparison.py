"""Architecture comparison."""

from __future__ import annotations
from agents.planner import complexity_score
from coordinator import MultiAgentResearchTeam
from single_agent import SingleAgentResearcher


def compare_architectures(question: str) -> dict:
    team = MultiAgentResearchTeam().run(question)
    single = SingleAgentResearcher().run(question)
    score = complexity_score(question)

    if score >= 4 and team.status == "approved":
        recommendation = (
            "Multi-agent coordination may be justified because the question "
            "has several separable facets and the reviewed team run completed."
        )
    else:
        recommendation = (
            "Prefer the simpler single-agent baseline unless explicit role "
            "separation or independent review boundaries are required."
        )

    return {
        "question": question,
        "question_complexity_score": score,
        "multi_agent": {
            "status": team.status,
            "metrics": team.metrics,
        },
        "single_agent": {
            "status": single.status,
            "metrics": single.metrics,
        },
        "coordination_overhead": {
            "additional_roles": (
                team.metrics["roles_used"]
                - single.metrics["roles_used"]
            ),
            "additional_messages": (
                team.metrics["coordination_messages"]
                - single.metrics["coordination_messages"]
            ),
            "additional_planned_tasks": (
                team.metrics["planned_tasks"]
                - single.metrics["planned_tasks"]
            ),
        },
        "recommendation": recommendation,
        "note": (
            "This comparison measures the mechanics of this deterministic demo. "
            "It does not prove that multi-agent systems are universally better "
            "or worse."
        ),
    }
