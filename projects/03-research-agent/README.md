# Project 03: Research Agent

This is the Week 3 working project in the **Agentic AI Learning Roadmap**.

It introduces the first complete **bounded agent loop** in the repository:

**plan → search → collect evidence → evaluate → refine or stop → synthesize**

Most importantly, this version is designed to be **100% runnable without a paid API key**.

It uses a small bundled educational source corpus and Python's standard library, so you can run the project and all tests in GitHub Codespaces without paying OpenAI or another model provider.

## What You Will Build

A research agent that:

1. Accepts a research question.
2. Infers the important research facets.
3. Creates a research plan.
4. Generates an initial queue of search actions.
5. Searches a local source corpus.
6. Stores unique evidence in explicit state.
7. Checks whether the evidence is sufficient.
8. Identifies missing facets.
9. Refines the query if more evidence is needed.
10. Stops when evidence is sufficient or the step limit is reached.
11. Produces a Markdown report with source citations and limitations.

## Why This Is an Agent

Project 02 demonstrated a model requesting individual tools.

Project 03 adds **state and repeated decision cycles**.

The application keeps track of:

- what question it is researching
- what it planned
- what it already searched
- what evidence it collected
- what facets are still missing
- how many steps it has used
- why it stopped

That creates a bounded Observe → Decide → Act → Observe loop.

## Architecture

```text
Research question
      ↓
Infer required facets
      ↓
Build plan + search queue
      ↓
┌──────────────────────────────┐
│        AGENT LOOP            │
│                              │
│ Choose next query            │
│        ↓                     │
│ Search local corpus          │
│        ↓                     │
│ Add unique evidence          │
│        ↓                     │
│ Evaluate coverage            │
│        ↓                     │
│ Enough? ── Yes ──> Stop     │
│   │                          │
│   No                         │
│   ↓                          │
│ Refine query                 │
│   ↓                          │
│ Next bounded step            │
└──────────────────────────────┘
      ↓
Synthesize cited report
```

## Project Files

```text
03-research-agent/
├── README.md
├── main.py
├── models.py
├── search.py
├── research_agent.py
├── test_research_agent.py
├── requirements.txt
├── sample_session.md
└── data/
    └── sources.json
```

## Requirements

- Python 3.10+
- No API key
- No paid service
- No third-party Python packages
- No network access required after the repository is available

## Source Corpus

`data/sources.json` contains concise educational records for sources such as:

- ReAct research paper
- OpenAI Agents SDK
- LangGraph
- Google ADK
- Microsoft Agent Framework
- Pydantic AI
- CrewAI
- Model Context Protocol specification
- Agent evaluation guidance

Each record contains:

- title
- source URL
- source type
- tags
- a short educational summary
- key points

The agent **does not download these webpages**. It searches only the bundled source records.

This is deliberate: Week 3 focuses on the agent loop, state, stopping conditions, and evidence handling without introducing web scraping, third-party search APIs, prompt injection from live webpages, or paid model calls.

## Run the Tests

From this project folder:

```bash
python -m unittest test_research_agent.py
```

The tests verify:

- corpus loading
- source ID uniqueness
- lexical search
- framework-facet planning
- security-facet planning
- collection of multiple sources
- bounded maximum steps
- citations in the final report
- no fabricated evidence for an unrelated query
- deduplication of evidence
- deterministic missing-facet handling

## Run the Research Agent

Default example:

```bash
python main.py
```

This researches:

```text
Compare approaches used by major Agentic AI frameworks and SDKs.
```

Custom question:

```bash
python main.py "How do Agentic AI frameworks approach state and tool use?"
```

Show the agent's step-by-step actions:

```bash
python main.py "Compare major Agentic AI frameworks." --trace
```

Limit the agent to three research steps:

```bash
python main.py "Compare major Agentic AI frameworks." --max-steps 3
```

## Example Trace

The `--trace` flag prints state transitions to standard error:

```text
[agent] {"step": 1, "action": "search", "query": "Compare approaches used by major Agentic AI frameworks and SDKs.", "hits": 0, "new_evidence": 0, "unique_sources": 0, "missing_facets": ["framework", "tool-use", "state"]}
[agent] {"step": 2, "action": "search", "query": "Compare approaches used by major Agentic AI frameworks and SDKs. framework", "hits": 4, "new_evidence": 4, "unique_sources": 4, "missing_facets": []}
```

This example shows why an agent loop matters: the first broad search is insufficient, so the agent continues with a more targeted query rather than pretending it already has enough evidence.

The exact results depend on the question, corpus, and ranking scores.

## Research State

`ResearchState` stores the changing state of the run:

```text
question
plan
required_facets
pending_queries
step
searched_queries
evidence
events
stop_reason
```

This makes the loop inspectable instead of hiding behavior inside a single function call.

## Stopping Conditions

The agent stops for one of three reasons.

### `enough_evidence`

The agent collected enough unique sources and covered the required research facets.

### `no_more_queries`

The agent cannot generate another useful unseen query.

### `max_steps_reached`

The configured maximum number of steps was used before the evidence threshold was satisfied.

The maximum-step limit is a key safety property. The agent cannot loop forever.

## Evidence Sufficiency

This demo uses a transparent deterministic rule:

- at least **3 unique sources**
- required research facets must be covered, with limited tolerance for one missing facet in broader framework-comparison questions

This is intentionally simple.

Later evaluation projects can replace a fixed rule with stronger task-specific evaluation.

## Source Handling

Evidence is deduplicated by stable source ID.

The final report includes:

```text
[S1] Source title
[S2] Source title
...
```

and a separate **Sources** section containing URLs.

If no relevant evidence exists, the agent does not fabricate a source-backed answer.

## Security and Reliability Choices

### No shell execution

The agent never executes operating-system commands.

### No arbitrary file access

The project reads only the bundled `data/sources.json` file.

### No live web requests

This avoids SSRF, uncontrolled downloads, and indirect prompt injection in this week's example.

### No API keys

Nothing sensitive needs to be stored.

### Bounded loop

`max_steps` prevents unbounded autonomous execution.

### Source allowlist

The searchable source set is explicit and inspectable.

### No invented citations

Reports are generated only from evidence objects collected from the corpus.

## What This Project Does Not Do

It does not:

- search the live web
- crawl websites
- call an LLM
- generate embeddings
- use a vector database
- verify that a source changed after the bundled corpus was created
- claim that deterministic summaries are equivalent to expert research

Those limitations are explicit.

Week 4 will introduce retrieval concepts in **Agentic RAG**.

## Exercises

### Beginner

Add two new records to `data/sources.json` and verify that search can retrieve them.

### Intermediate

Change the lexical ranking formula so source titles and tags receive different weights. Add a unit test for the new ranking behavior.

### Challenge

Add a **freshness policy**:

1. Give sources a `checked_at` date.
2. Mark records older than a configurable threshold as stale.
3. Make the final report warn when important evidence is stale.
4. Do not silently treat stale evidence as current.

### Advanced Challenge

Add an optional provider interface:

```text
ResearchProvider
├── LocalCorpusProvider
└── FutureWebSearchProvider
```

Keep the local provider as the default so the project remains free and testable.

## Next Step

Week 4 will build **Agentic RAG**, where the agent decides whether retrieval is necessary and whether retrieved context is sufficient before answering.

Return to the [main roadmap](../../README.md).
