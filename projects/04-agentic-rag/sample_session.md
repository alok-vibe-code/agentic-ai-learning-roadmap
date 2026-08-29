# Sample Session: Project 04 Agentic RAG

## Command

```bash
python main.py "What makes Agentic RAG different from a fixed RAG pipeline?" --trace
```

## Example Trace Shape

```text
[rag] {"action": "route", "retrieval_needed": true}
[rag] {"action": "retrieve", "round": 1, "query": "...", "new_hits": 4, "total_unique_chunks": 4, "metrics": {"top_score": 0.4, "query_coverage": 0.5, "unique_documents": 4, "reason": "sufficient"}}
```

## Example Answer Shape

```text
## Grounded Answer

- Agentic RAG adds decision points around retrieval. [C1]
- The agent can inspect evidence, rewrite a weak query, and retrieve again. [C1]
- A robust workflow should abstain when evidence is insufficient. [C2]

## Retrieved Sources

- [C1] Agentic RAG Control Flow (...)
- [C2] Grounding, Citations, and Abstention (...)

## Grounding Note

This answer is assembled only from retrieved local context.
```

## Unsupported Question

```bash
python main.py "Explain medieval glassmaking recipes from fourteenth-century Venice." --trace
```

Expected behavior:

```text
I do not have enough evidence in the bundled knowledge base to answer that question reliably.

The retrieval loop stopped at its configured maximum number of rounds instead of inventing an answer.
```
