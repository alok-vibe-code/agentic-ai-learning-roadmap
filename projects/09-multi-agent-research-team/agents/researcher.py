"""Researcher agent."""

from __future__ import annotations
from models import Evidence, ResearchTask, Source
from search import search_sources


class ResearcherAgent:
    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id
        self.name = f"researcher:{worker_id}"

    def research(
        self,
        task: ResearchTask,
        *,
        sources: list[Source],
        top_k: int = 2,
    ) -> list[Evidence]:
        if "[fail-research]" in task.query.casefold():
            raise RuntimeError(
                f"Simulated research failure for {task.id}."
            )

        results = search_sources(
            task.query,
            top_k=top_k,
            sources=sources,
        )
        return [
            Evidence(
                source_id=source.id,
                source_title=source.title,
                source_url=source.url,
                task_id=task.id,
                facet=task.facet,
                researcher=self.name,
                snippet=snippet,
                score=score,
            )
            for source, score, snippet in results
        ]
