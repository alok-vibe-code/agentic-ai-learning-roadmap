"""Zero-cost Agentic RAG control loop.

The goal is to make retrieval decisions visible:
need retrieval -> rewrite -> retrieve -> evaluate -> retry/stop -> grounded answer.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from models import RAGState, RetrievalHit
from vector_store import LocalVectorStore, tokenize


DEFAULT_MAX_ROUNDS = 3
MIN_TOP_SCORE = 0.16
MIN_QUERY_COVERAGE = 0.28
MIN_UNIQUE_DOCUMENTS = 1


_ALIAS_EXPANSIONS = {
    "rag": "retrieval augmented generation",
    "agentic rag": "agentic retrieval augmented generation query rewriting evidence sufficiency",
    "vector db": "vector store vector database indexing retrieval",
    "vector database": "vector store vector database indexing retrieval",
    "semantic search": "semantic retrieval embeddings vectors similarity",
    "mcp": "model context protocol",
}


_DIRECT_PATTERNS = (
    re.compile(r"^\s*(hi|hello|hey|thanks|thank you)[!. ]*$", re.I),
    re.compile(r"^\s*what is \d+(?:\.\d+)?\s*[\+\-\*/]\s*\d+(?:\.\d+)?\??\s*$", re.I),
)


def needs_retrieval(question: str) -> bool:
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty.")
    return not any(pattern.match(question) for pattern in _DIRECT_PATTERNS)


def direct_response(question: str) -> str:
    normalized = question.strip().casefold()
    if normalized in {"hi", "hello", "hey", "hi!", "hello!", "hey!"}:
        return "Hello. Ask me a question about the bundled Agentic RAG knowledge base."

    arithmetic = re.match(
        r"^\s*what is (\d+(?:\.\d+)?)\s*([\+\-\*/])\s*(\d+(?:\.\d+)?)\??\s*$",
        question,
        re.I,
    )
    if arithmetic:
        left = float(arithmetic.group(1))
        operator = arithmetic.group(2)
        right = float(arithmetic.group(3))
        if operator == "+":
            result = left + right
        elif operator == "-":
            result = left - right
        elif operator == "*":
            result = left * right
        else:
            if right == 0:
                return "Division by zero is not allowed."
            result = left / right
        return f"{result:g}"

    return "This request does not require retrieval."


def rewrite_query(question: str, round_number: int) -> str:
    cleaned = " ".join(question.strip().split())
    lowered = cleaned.casefold()

    expansions: list[str] = []
    for alias, expansion in _ALIAS_EXPANSIONS.items():
        if alias in lowered:
            expansions.append(expansion)

    if round_number >= 2:
        expansions.extend([
            "grounding retrieval quality citations",
            "chunking embeddings vector store query rewrite"
        ])
    if round_number >= 3:
        expansions.extend([
            "evidence sufficient abstention cosine similarity"
        ])

    if not expansions:
        if round_number == 1:
            expansions.append("retrieval rag grounding")
        elif round_number == 2:
            expansions.append("query rewriting retrieval quality")
        else:
            expansions.append("evidence citations abstention")

    return " ".join([cleaned] + expansions)


def _query_content_terms(question: str) -> set[str]:
    terms = set(tokenize(question))
    # Remove broad request words that are usually not evidence facets.
    terms.difference_update({
        "explain", "compare", "difference", "different", "describe",
        "major", "approaches", "approach", "used", "uses"
    })
    return terms


def evaluate_evidence(
    question: str,
    hits: list[RetrievalHit],
) -> tuple[bool, dict]:
    if not hits:
        return False, {
            "top_score": 0.0,
            "query_coverage": 0.0,
            "unique_documents": 0,
            "reason": "no_hits",
        }

    top_score = hits[0].score
    query_terms = _query_content_terms(question)
    matched_terms: set[str] = set()
    for hit in hits:
        matched_terms.update(hit.matched_terms)

    coverage = (
        len(query_terms & matched_terms) / len(query_terms)
        if query_terms
        else 1.0
    )
    unique_documents = len({hit.chunk.document_id for hit in hits})

    sufficient = (
        top_score >= MIN_TOP_SCORE
        and coverage >= MIN_QUERY_COVERAGE
        and unique_documents >= MIN_UNIQUE_DOCUMENTS
    )

    return sufficient, {
        "top_score": round(top_score, 4),
        "query_coverage": round(coverage, 4),
        "unique_documents": unique_documents,
        "reason": "sufficient" if sufficient else "weak_evidence",
    }


def _merge_hits(
    existing: list[RetrievalHit],
    new_hits: list[RetrievalHit],
) -> list[RetrievalHit]:
    best_by_chunk: OrderedDict[str, RetrievalHit] = OrderedDict()

    for hit in existing + new_hits:
        current = best_by_chunk.get(hit.chunk.id)
        if current is None or hit.score > current.score:
            best_by_chunk[hit.chunk.id] = hit

    merged = list(best_by_chunk.values())
    merged.sort(
        key=lambda hit: (
            -hit.score,
            hit.chunk.title.casefold(),
            hit.chunk.position,
        )
    )
    return merged


def _sentence_candidates(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    # Word-window chunks can end in the middle of a sentence. Keep only
    # complete sentences so grounded output does not expose clipped fragments.
    return [
        part.strip()
        for part in parts
        if part.strip()
        and part.strip()[-1:] in {".", "!", "?"}
    ]


def _grounded_answer(question: str, hits: list[RetrievalHit]) -> str:
    if not hits:
        return (
            "I do not have enough evidence in the bundled knowledge base "
            "to answer that question reliably."
        )

    question_terms = _query_content_terms(question)
    candidates: list[tuple[float, str, str]] = []

    # Rank sentences by overlap with the original question, while preserving source IDs.
    for index, hit in enumerate(hits, start=1):
        for sentence in _sentence_candidates(hit.chunk.text):
            sentence_terms = set(tokenize(sentence))
            overlap = len(question_terms & sentence_terms)
            score = overlap + hit.score
            candidates.append((score, sentence, f"C{index}"))

    candidates.sort(key=lambda item: -item[0])

    selected: list[tuple[str, str]] = []
    seen_sentences: set[str] = set()

    for _, sentence, citation in candidates:
        key = sentence.casefold()
        if key in seen_sentences:
            continue
        seen_sentences.add(key)
        selected.append((sentence, citation))
        if len(selected) >= 4:
            break

    if not selected:
        return (
            "I retrieved context but could not identify enough grounded evidence "
            "to formulate a reliable answer."
        )

    lines = ["## Grounded Answer", ""]
    for sentence, citation in selected:
        lines.append(f"- {sentence} [{citation}]")

    lines.extend(["", "## Retrieved Sources", ""])
    for index, hit in enumerate(hits, start=1):
        lines.append(
            f"- [C{index}] [{hit.chunk.title}]({hit.chunk.source_url}) "
            f"(score: {hit.score:.3f}, chunk: {hit.chunk.position})"
        )

    lines.extend([
        "",
        "## Grounding Note",
        "",
        "This answer is assembled only from retrieved local context. "
        "The demo does not use an LLM to add unsupported information."
    ])

    return "\n".join(lines)


class AgenticRAG:
    def __init__(
        self,
        store: LocalVectorStore,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        top_k: int = 4,
    ):
        if max_rounds < 1:
            raise ValueError("max_rounds must be >= 1.")
        if top_k < 1:
            raise ValueError("top_k must be >= 1.")
        self.store = store
        self.max_rounds = max_rounds
        self.top_k = top_k

    def run(self, question: str) -> tuple[RAGState, str]:
        question = question.strip()
        retrieval_needed = needs_retrieval(question)

        state = RAGState(
            question=question,
            retrieval_needed=retrieval_needed,
            max_rounds=self.max_rounds,
        )

        if not retrieval_needed:
            state.sufficient = True
            state.stop_reason = "retrieval_not_needed"
            state.events.append({
                "action": "route",
                "retrieval_needed": False,
            })
            return state, direct_response(question)

        state.events.append({
            "action": "route",
            "retrieval_needed": True,
        })

        for round_number in range(1, self.max_rounds + 1):
            state.round = round_number
            query = rewrite_query(question, round_number)
            state.queries.append(query)

            new_hits = self.store.search(query, top_k=self.top_k)
            state.hits = _merge_hits(state.hits, new_hits)

            sufficient, metrics = evaluate_evidence(question, state.hits)
            state.events.append({
                "action": "retrieve",
                "round": round_number,
                "query": query,
                "new_hits": len(new_hits),
                "total_unique_chunks": len(state.unique_chunk_ids),
                "metrics": metrics,
            })

            if sufficient:
                state.sufficient = True
                state.stop_reason = "evidence_sufficient"
                break

        if not state.sufficient:
            state.stop_reason = "max_rounds_reached"
            return state, (
                "I do not have enough evidence in the bundled knowledge base "
                "to answer that question reliably.\n\n"
                "The retrieval loop stopped at its configured maximum number "
                "of rounds instead of inventing an answer."
            )

        return state, _grounded_answer(question, state.hits)
