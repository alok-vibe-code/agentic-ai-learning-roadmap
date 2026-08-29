"""Writer agent."""

from __future__ import annotations
from collections import defaultdict
from models import Claim, ResearchPlan, Source


class WriterAgent:
    name = "writer"

    def write(
        self,
        question: str,
        plan: ResearchPlan,
        claims: list[Claim],
        *,
        sources: list[Source],
    ) -> str:
        verified = [claim for claim in claims if claim.verified]
        by_task: dict[str, list[Claim]] = defaultdict(list)

        for claim in verified:
            by_task[claim.task_id].append(claim)

        lines = [
            "# Research Report",
            "",
            f"**Question:** {question}",
            "",
        ]

        for task in plan.tasks:
            lines.append(f"## {task.facet.replace('_', ' ').title()}")
            task_claims = by_task.get(task.id, [])

            if not task_claims:
                lines.append(
                    "No verified evidence was available for this facet."
                )
                lines.append("")
                continue

            seen_text: set[str] = set()
            for claim in task_claims:
                if claim.text in seen_text:
                    continue
                seen_text.add(claim.text)
                lines.append(f"- {claim.text} [{claim.source_id}]")
            lines.append("")

        used_ids: list[str] = []
        for claim in verified:
            if claim.source_id not in used_ids:
                used_ids.append(claim.source_id)

        source_map = {source.id: source for source in sources}
        lines.extend(["## Sources", ""])

        for source_id in used_ids:
            source = source_map[source_id]
            lines.append(f"- [{source.id}] {source.title} ({source.url})")

        if not used_ids:
            lines.append("- No verified sources.")

        return "\n".join(lines).strip() + "\n"
