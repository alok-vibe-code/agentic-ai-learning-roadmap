# Project 09: Multi-Agent Research Team

This is the Week 9 working project in the **Agentic AI Learning Roadmap**.

It demonstrates a multi-agent research architecture without hiding coordination behind a framework.

## Roles

- **Planner**: decomposes a question into bounded research facets
- **Researcher workers**: search independent facets in parallel
- **Fact Checker**: verifies evidence provenance
- **Writer**: synthesizes only verified claims
- **Reviewer**: applies explicit acceptance criteria

A coordinator owns shared state and records every delegation, result, and failure.

## Architecture

```text
Question
   ↓
Coordinator
   ↓
Planner
   ↓
Research tasks
   ↓
Researcher 1 ─┐
Researcher 2 ─┼─→ Shared evidence
Researcher N ─┘
   ↓
Fact Checker
   ↓
Verified claims
   ↓
Writer
   ↓
Reviewer
   ↓
Approved or rejected report
```

## Why It Is Offline

Week 9 focuses on coordination mechanics, so every role is deterministic.

The project uses:

- Python standard library
- a bundled local corpus
- no API key
- no model calls
- no network requests
- no paid service

This makes delegation, shared state, review gates, and failure handling inspectable before adding LLM variability.

## Shared State

The coordinator owns:

```text
question
plan
evidence
claims
draft
report
review
messages
failures
status
metrics
```

Workers return results instead of mutating all shared state directly.

## Explicit Communication

Every handoff is represented as:

```text
sender
recipient
kind
content
```

The trace shows:

```text
coordinator -> planner [delegate]
planner -> coordinator [result]
coordinator -> researcher:1 [delegate]
researcher:1 -> coordinator [result]
coordinator -> fact_checker [delegate]
...
```

## Parallel Research

Independent research facets run in a bounded thread pool.

Worker completion order can vary internally, but the coordinator reassembles evidence and trace results in plan order so the final report remains deterministic.

## Failure Policy

Researcher failures are isolated and recorded.

Critical quality stages are fail-closed.

The project includes a deterministic test hook:

```text
[fail-research]
```

for exercising worker-failure handling. It never executes user code.

## Single-Agent Baseline

The same corpus and search logic are also used by:

```text
single_agent.py
```

The baseline uses one role and no coordination messages.

That makes it possible to compare:

```text
Multi-agent
+ explicit specialization
+ task-level coverage
+ independent review boundaries
- more roles
- more messages
- more failure surfaces

Single-agent
+ simpler
+ lower coordination overhead
- fewer specialized checks
- no independent review role
```

## Run the Team

```bash
python main.py team \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling."
```

With trace:

```bash
python main.py team \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling." \
  --trace
```

## Run the Baseline

```bash
python main.py single \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling."
```

## Compare Architectures

```bash
python main.py compare \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling."
```

Try a simpler question too:

```bash
python main.py compare "What is agent handoff?"
```

The project deliberately does not claim that multi-agent is always better.

## Project Structure

```text
09-multi-agent-research-team/
├── README.md
├── main.py
├── models.py
├── search.py
├── coordinator.py
├── single_agent.py
├── comparison.py
├── test_multi_agent_team.py
├── requirements.txt
├── sample_session.md
├── data/
│   └── sources.json
└── agents/
    ├── __init__.py
    ├── planner.py
    ├── researcher.py
    ├── fact_checker.py
    ├── writer.py
    └── reviewer.py
```

## Metrics

The comparison exposes:

- roles used
- planned tasks
- evidence items
- verified claims
- unique sources
- covered tasks
- coverage ratio
- coordination messages
- worker failures

These metrics describe this demo's mechanics. They are not a universal multi-agent benchmark.

## Safety Boundaries

The project:

- executes no code from the question
- makes no network requests
- invokes no shell command
- uses no model API
- caps question length
- caps plan size
- caps worker concurrency
- uses a read-only local corpus
- records failures explicitly
- writes only verified evidence into the team report

## Tests

```bash
python -m unittest test_multi_agent_team.py
```

The test suite covers corpus validation, search, planning, bounded tasks, complexity scoring, provenance, fact checking, citations, review gates, deterministic ordering, concurrency, failure handling, baseline behavior, comparison logic, and safety boundaries.

## Exercises

### Beginner
Add a `security` planning facet.

### Intermediate
Add a source-diversity researcher strategy.

### Challenge
Require two sources before accepting selected high-risk claims.

### Advanced
Replace only one deterministic role with an LLM and compare output variation, cost, and test stability.

## Next Step

Week 10 builds an **Agent Evaluation Harness** so the roadmap can measure behavior systematically.

Return to the [main roadmap](../../README.md).
