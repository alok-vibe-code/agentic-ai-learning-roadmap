"""Simpler single-agent baseline."""

from __future__ import annotations
from models import RunResult
from search import load_sources, search_sources


class SingleAgentResearcher:
    def run(self, question: str, *, top_k: int = 4) -> RunResult:
        if not isinstance(question, str):
            raise TypeError("question must be a string.")
        normalized = " ".join(question.split())
        if not normalized:
            raise ValueError("question cannot be empty.")
        if len(normalized) > 1_500:
            raise ValueError(
                "question exceeds the 1,500-character demo limit."
            )

        sources = load_sources()
        results = search_sources(
            normalized,
            top_k=top_k,
            sources=sources,
        )

        lines = [
            "# Single-Agent Research Report",
            "",
            f"**Question:** {normalized}",
            "",
            "## Findings",
            "",
        ]

        source_ids: list[str] = []
        for source, _, snippet in results:
            lines.append(f"- {snippet} [{source.id}]")
            if source.id not in source_ids:
                source_ids.append(source.id)

        if not results:
            lines.append("- No matching evidence was found.")

        lines.extend(["", "## Sources", ""])
        source_map = {source.id: source for source in sources}

        for source_id in source_ids:
            source = source_map[source_id]
            lines.append(f"- [{source.id}] {source.title} ({source.url})")

        if not source_ids:
            lines.append("- No sources.")

        return RunResult(
            mode="single-agent",
            question=normalized,
            report="\n".join(lines).strip() + "\n",
            status="completed",
            metrics={
                "roles_used": 1,
                "planned_tasks": 1,
                "evidence_items": len(results),
                "verified_claims": len(results),
                "unique_sources": len(source_ids),
                "covered_tasks": 1 if results else 0,
                "coverage_ratio": 1.0 if results else 0.0,
                "coordination_messages": 0,
                "worker_failures": 0,
            },
            trace=(),
            failures=(),
        )
