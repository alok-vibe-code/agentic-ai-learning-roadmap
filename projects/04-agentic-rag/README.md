# Project 04: Agentic RAG

This is the Week 4 working project in the **Agentic AI Learning Roadmap**.

It demonstrates a complete **Agentic Retrieval-Augmented Generation (Agentic RAG)** control loop:

**route → rewrite → retrieve → evaluate → retry or stop → grounded answer**

The project is deliberately designed to be **100% runnable without a paid API key**.

It uses:

- a bundled local knowledge base
- deterministic chunking
- an in-memory TF-IDF sparse vector store
- cosine-similarity ranking
- query rewriting
- evidence-sufficiency checks
- bounded retrieval rounds
- grounded extractive answers
- citations
- abstention when evidence is weak

No OpenAI API key, embedding API, hosted vector database, or third-party Python package is required.

## Why This Comes After the Research Agent

Project 03 introduced the general agent loop:

```text
plan → search → evaluate → refine → stop
```

Project 04 specializes that idea for retrieval:

```text
question
   ↓
need retrieval?
   ↓
rewrite query
   ↓
retrieve chunks
   ↓
is evidence sufficient?
   ↓
retry or stop
   ↓
grounded answer
```

The key idea is that **retrieval is not automatically trusted**.

The agent evaluates the retrieved evidence before answering.

## RAG vs Agentic RAG

A simple RAG pipeline can look like:

```text
Question
   ↓
Retrieve once
   ↓
Generate answer
```

Agentic RAG adds decisions:

```text
Question
   ↓
Need retrieval?
  ↙        ↘
No         Yes
↓           ↓
Direct     Rewrite
response      ↓
           Retrieve
              ↓
      Evidence sufficient?
        ↙          ↘
      Yes           No
       ↓             ↓
   Grounded      Rewrite /
    answer       retrieve again
       ↓             ↓
    Citations ← bounded loop
```

The retrieval loop cannot continue forever because the application enforces `max_rounds`.

## Project Files

```text
04-agentic-rag/
├── README.md
├── main.py
├── models.py
├── chunking.py
├── vector_store.py
├── agentic_rag.py
├── test_agentic_rag.py
├── requirements.txt
├── sample_session.md
└── data/
    └── knowledge_base.json
```

## What You Will Learn

- Why documents are chunked before retrieval
- The tradeoff between chunk size and overlap
- How text becomes a vector representation
- What TF-IDF means
- How cosine similarity ranks vectors
- What a vector-store interface does
- Why dense embeddings are different from lexical TF-IDF
- How an agent decides whether retrieval is needed
- How query rewriting can improve retrieval
- How to evaluate evidence sufficiency
- Why retrieval results should not automatically be trusted
- How citations support traceability
- Why abstention is better than unsupported generation
- How maximum retrieval rounds bound agent behavior

## Zero-Cost Retrieval Model

Production RAG systems commonly use **dense embedding models**.

Dense embeddings can represent semantic similarity even when two texts use different words.

This project intentionally uses **TF-IDF sparse vectors** instead.

Why?

1. The math is inspectable.
2. It runs with Python's standard library.
3. It requires no model API.
4. It requires no vector-database account.
5. The agent-level control flow is still realistic.

The architecture separates retrieval control from the vector implementation, so a later version could replace `LocalVectorStore` with an embedding-backed vector store.

## Knowledge Base

`data/knowledge_base.json` contains educational source notes covering:

- RAG foundations
- Agentic RAG
- chunking
- embeddings and vector retrieval
- TF-IDF
- query rewriting
- grounding and citations
- retrieval evaluation
- vector stores
- hybrid retrieval

Each document contains:

- stable source ID
- title
- source URL
- tags
- educational text

The demo does **not** fetch the URLs while running.

The URLs exist so the final answer can preserve source provenance.

## Step 1: Chunking

Documents are divided into overlapping word windows.

Default configuration:

```text
chunk size: 70 words
overlap:    15 words
```

The overlap preserves some context across neighboring chunks.

The chunker rejects invalid configurations such as overlap being equal to or larger than the chunk size.

## Step 2: Sparse Vectorization

The local vector store:

1. tokenizes each chunk
2. calculates document frequency
3. creates TF-IDF term weights
4. stores an in-memory sparse vector for each chunk

No external package is used.

## Step 3: Cosine Similarity

At retrieval time:

1. the query is converted into a TF-IDF vector
2. cosine similarity is calculated against each chunk
3. chunks are sorted by similarity score
4. the top `k` results are returned

## Step 4: Retrieval Routing

Not every request needs retrieval.

For example:

```bash
python main.py "hello" --trace
```

The agent routes this directly without searching the knowledge base.

A knowledge question such as:

```bash
python main.py "What makes Agentic RAG different from a fixed RAG pipeline?" --trace
```

uses retrieval.

## Step 5: Query Rewriting

User wording and corpus wording may differ.

The demo expands terms such as:

```text
RAG
→ retrieval augmented generation

Agentic RAG
→ agentic retrieval augmented generation
   query rewriting
   evidence sufficiency
```

Later retrieval rounds add terms related to:

- grounding
- retrieval quality
- citations
- chunking
- embeddings
- vector stores
- abstention

The rewrites are deterministic so learners can inspect exactly why a query changed.

## Step 6: Evidence Sufficiency

Retrieval is evaluated using transparent signals:

- top similarity score
- query-term coverage
- unique source-document count

If the evidence is weak, the agent performs another bounded retrieval round.

This is a simplified teaching rule, not a universal production threshold.

## Step 7: Grounded Answer

The demo does not call an LLM.

Instead, it selects sentences only from retrieved chunks and cites them:

```text
[C1]
[C2]
[C3]
```

This ensures the example cannot silently invent information outside the retrieved context.

## Step 8: Abstention

For an unrelated question such as:

```bash
python main.py "Explain medieval glassmaking recipes from fourteenth-century Venice." --trace
```

the agent should eventually stop with a message explaining that the bundled knowledge base does not contain enough evidence.

This is intentional.

A RAG system should not treat irrelevant retrieved text as permission to answer.

## Run the Tests

From this project directory:

```bash
python -m unittest test_agentic_rag.py
```

The offline tests verify:

- unique document IDs
- chunk creation
- invalid chunk-overlap rejection
- tokenization
- RAG retrieval
- embeddings/vector retrieval
- similarity score ordering
- retrieval routing
- query rewriting
- grounded answers
- citation output
- abstention
- maximum-round enforcement
- exposed retrieval-quality metrics
- chunk deduplication
- no-hit evidence rejection

## Run the Agentic RAG Demo

Default question:

```bash
python main.py
```

Custom question:

```bash
python main.py "What makes Agentic RAG different from basic RAG?"
```

Show the full decision trace:

```bash
python main.py "How do query rewriting and evidence sufficiency work in Agentic RAG?" --trace
```

Ask about embeddings:

```bash
python main.py "How are embeddings and cosine similarity used in vector retrieval?" --trace
```

Ask about vector stores:

```bash
python main.py "What does a vector store do in a RAG system?" --trace
```

Limit retrieval:

```bash
python main.py "Explain Agentic RAG." --max-rounds 1 --trace
```

## Example Trace

```text
[rag] {"action": "route", "retrieval_needed": true}
[rag] {
  "action": "retrieve",
  "round": 1,
  "query": "...",
  "new_hits": 4,
  "total_unique_chunks": 4,
  "metrics": {
    "top_score": 0.42,
    "query_coverage": 0.50,
    "unique_documents": 4,
    "reason": "sufficient"
  }
}
```

If evidence is weak, another retrieval event appears with a rewritten query.

## Agent State

`RAGState` keeps the run inspectable:

```text
question
retrieval_needed
max_rounds
round
queries
hits
events
stop_reason
sufficient
```

Useful stop reasons are:

### `retrieval_not_needed`

The agent decided the request did not require the knowledge base.

### `evidence_sufficient`

Retrieved evidence passed the demo's sufficiency check.

### `max_rounds_reached`

The agent used all allowed retrieval rounds without sufficient evidence.

## Security and Reliability Choices

### No network requests

The runtime never fetches arbitrary URLs.

### No API keys

No secrets are required.

### No shell execution

The agent does not run operating-system commands.

### Bounded retrieval loop

`max_rounds` prevents uncontrolled searching.

### Explicit local corpus

The searchable information is reviewable before execution.

### Grounded synthesis

The answer is assembled only from retrieved chunks.

### Abstention

Insufficient evidence produces a refusal to invent an answer.

### Source provenance

Retrieved chunks preserve their source URL.

## Important Limitation

TF-IDF is **not the same as neural semantic embeddings**.

It relies heavily on overlapping terminology.

That limitation is part of the lesson: learners can observe why modern RAG systems often use dense embeddings, hybrid search, reranking, or stronger retrieval models.

## Exercises

### Beginner

Change the chunk size from 70 to 50 words and compare the top retrieval results.

### Intermediate

Add a new document to `knowledge_base.json` about reranking.

Write a test proving that the new source is retrieved for a reranking query.

### Challenge

Implement a small **hybrid retriever** that combines:

- TF-IDF cosine score
- exact tag matching

Then compare ranking behavior against the current vector store.

### Advanced Challenge

Define a provider interface:

```text
Retriever
├── LocalTfidfRetriever
└── FutureEmbeddingRetriever
```

Keep TF-IDF as the default so tests remain free.

## Next Step

Week 5 will add **Agent Memory**.

That project will distinguish working memory from persistent memory and will introduce explicit rules for what should and should not be stored.

Return to the [main roadmap](../../README.md).
