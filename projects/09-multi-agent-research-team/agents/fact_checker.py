"""Fact checker agent."""

from __future__ import annotations
from models import Claim, Evidence, Source


class FactCheckerAgent:
    name = "fact_checker"

    def verify(
        self,
        evidence: list[Evidence],
        *,
        sources: list[Source],
    ) -> list[Claim]:
        source_map = {source.id: source for source in sources}
        claims: list[Claim] = []

        for index, item in enumerate(evidence, start=1):
            source = source_map.get(item.source_id)
            if source is None:
                claims.append(
                    Claim(
                        id=f"C{index}",
                        text=item.snippet,
                        source_id=item.source_id,
                        source_url=item.source_url,
                        task_id=item.task_id,
                        facet=item.facet,
                        verified=False,
                        reason="Referenced source is missing from the corpus.",
                    )
                )
                continue

            verified = item.snippet in source.content
            claims.append(
                Claim(
                    id=f"C{index}",
                    text=item.snippet,
                    source_id=item.source_id,
                    source_url=item.source_url,
                    task_id=item.task_id,
                    facet=item.facet,
                    verified=verified,
                    reason=(
                        "Snippet is present verbatim in the referenced local source."
                        if verified
                        else "Snippet is not present in the referenced local source."
                    ),
                )
            )

        return claims
