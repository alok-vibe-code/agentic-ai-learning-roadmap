"""Bounded zero-cost research agent.

The agent follows a real multi-step loop:
plan -> search -> collect evidence -> evaluate -> refine/stop -> synthesize.

It uses a bundled local corpus so learners can run and test it without paid APIs.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from models import Evidence, ResearchState
from search import LocalCorpus, tokenize


DEFAULT_MAX_STEPS = 6
MIN_UNIQUE_SOURCES = 3


def infer_required_facets(question: str) -> list[str]:
    terms = set(tokenize(question))

    if {"framework", "frameworks", "sdk", "sdks"} & terms:
        facets = ["framework", "tool-use", "state"]
    elif {"protocol", "mcp", "interoperability"} & terms:
        facets = ["protocol", "tool-use"]
    elif {"evaluation", "eval", "testing", "reliability"} & terms:
        facets = ["evaluation", "testing"]
    elif {"security", "guardrails", "safe", "safety"} & terms:
        facets = ["security", "tool-use"]
    elif {"loop", "loops", "react", "reasoning", "acting"} & terms:
        facets = ["agent-loop", "reasoning", "tool-use"]
    else:
        facets = ["architecture", "tool-use"]

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(facets))


def build_research_plan(question: str, required_facets: Iterable[str]) -> list[str]:
    facets = list(required_facets)

    plan = [
        f"Find sources directly relevant to: {question}",
        "Collect evidence from multiple independent source types.",
        "Check whether the evidence covers the important facets: "
        + ", ".join(facets) + ".",
        "Refine the search if important facets are missing.",
        "Stop when evidence is sufficient or the maximum step limit is reached.",
        "Synthesize only from collected evidence and cite every source used.",
    ]
    return plan


def build_initial_queries(question: str, required_facets: list[str]) -> list[str]:
    queries = [question]
    for facet in required_facets:
        queries.append(f"{question} {facet}")
    return list(dict.fromkeys(queries))


def missing_facets(state: ResearchState) -> list[str]:
    covered = state.covered_tags
    return [facet for facet in state.required_facets if facet not in covered]


def evidence_is_sufficient(state: ResearchState) -> bool:
    if len(state.source_ids) < MIN_UNIQUE_SOURCES:
        return False

    missing = missing_facets(state)

    # A framework comparison should cover most requested facets.
    allowed_missing = 1 if len(state.required_facets) >= 4 else 0
    return len(missing) <= allowed_missing


def _add_evidence(state: ResearchState, query: str, hits) -> int:
    added = 0
    existing = state.source_ids

    for hit in hits:
        if hit.source.id in existing:
            continue
        state.evidence.append(
            Evidence(
                source=hit.source,
                score=hit.score,
                query=query,
                matched_terms=hit.matched_terms,
            )
        )
        existing.add(hit.source.id)
        added += 1

    return added


def _next_query(state: ResearchState) -> str | None:
    while state.pending_queries:
        query = state.pending_queries.pop(0).strip()
        if query and query not in state.searched_queries:
            return query

    missing = missing_facets(state)
    if missing:
        refined = f"{state.question} {' '.join(missing)}"
        if refined not in state.searched_queries:
            return refined

    return None


def synthesize_report(state: ResearchState) -> str:
    evidence = sorted(
        state.evidence,
        key=lambda item: (-item.score, item.source.title.casefold())
    )

    lines: list[str] = []
    lines.append("# Research Report")
    lines.append("")
    lines.append(f"**Question:** {state.question}")
    lines.append("")
    lines.append(
        f"**Agent status:** `{state.stop_reason or 'unknown'}` after "
        f"{state.step} research step(s)."
    )
    lines.append("")

    lines.append("## Research Plan")
    lines.append("")
    for index, item in enumerate(state.plan, start=1):
        lines.append(f"{index}. {item}")
    lines.append("")

    lines.append("## Findings")
    lines.append("")

    if not evidence:
        lines.append(
            "No relevant evidence was found in the bundled local corpus. "
            "This demo intentionally does not invent an answer."
        )
    else:
        for index, item in enumerate(evidence, start=1):
            source = item.source
            lines.append(f"### [S{index}] {source.title}")
            lines.append("")
            lines.append(source.summary)
            lines.append("")
            for point in source.key_points:
                lines.append(f"- {point}")
            lines.append("")
            lines.append(
                f"**Source type:** {source.source_type} · "
                f"**Matched:** {', '.join(item.matched_terms) or 'n/a'}"
            )
            lines.append("")

    lines.append("## Evidence Coverage")
    lines.append("")
    covered = sorted(state.covered_tags)
    missing = missing_facets(state)
    lines.append(
        f"- Unique sources collected: **{len(state.source_ids)}**"
    )
    lines.append(
        "- Required facets: " + ", ".join(state.required_facets)
    )
    lines.append(
        "- Covered tags: " + (", ".join(covered) if covered else "none")
    )
    lines.append(
        "- Missing required facets: " + (", ".join(missing) if missing else "none")
    )
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    for index, item in enumerate(evidence, start=1):
        lines.append(f"- [S{index}] [{item.source.title}]({item.source.url})")
    if not evidence:
        lines.append("- No sources cited.")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- This project searches a small bundled educational corpus, not the live web."
    )
    lines.append(
        "- Source summaries are concise teaching notes and may become outdated as projects evolve."
    )
    lines.append(
        "- The deterministic synthesizer organizes evidence but does not perform LLM-based interpretation."
    )
    lines.append(
        "- A production research agent would need live source retrieval, freshness checks, stronger ranking, provenance controls, and evaluation."
    )
    lines.append("")

    return "\n".join(lines)


class ResearchAgent:
    def __init__(
        self,
        corpus: LocalCorpus,
        max_steps: int = DEFAULT_MAX_STEPS,
        top_k: int = 4,
    ):
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1.")
        if top_k < 1:
            raise ValueError("top_k must be >= 1.")
        self.corpus = corpus
        self.max_steps = max_steps
        self.top_k = top_k

    def run(self, question: str) -> tuple[ResearchState, str]:
        question = question.strip()
        if not question:
            raise ValueError("Research question cannot be empty.")

        required_facets = infer_required_facets(question)
        plan = build_research_plan(question, required_facets)
        state = ResearchState(
            question=question,
            plan=plan,
            required_facets=required_facets,
            pending_queries=build_initial_queries(question, required_facets),
            max_steps=self.max_steps,
        )

        while state.step < state.max_steps:
            if evidence_is_sufficient(state):
                state.stop_reason = "enough_evidence"
                break

            query = _next_query(state)
            if query is None:
                state.stop_reason = "no_more_queries"
                break

            state.step += 1
            state.searched_queries.append(query)

            hits = self.corpus.search(query, top_k=self.top_k)
            added = _add_evidence(state, query, hits)

            event = {
                "step": state.step,
                "action": "search",
                "query": query,
                "hits": len(hits),
                "new_evidence": added,
                "unique_sources": len(state.source_ids),
                "missing_facets": missing_facets(state),
            }
            state.events.append(event)

        if state.stop_reason is None:
            state.stop_reason = (
                "enough_evidence"
                if evidence_is_sufficient(state)
                else "max_steps_reached"
            )

        return state, synthesize_report(state)
