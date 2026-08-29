# Sample Session: Project 03 Research Agent

## Command

```bash
python main.py "Compare approaches used by major Agentic AI frameworks and SDKs." --trace
```

## Example Agent Trace

```text
[agent] {"step": 1, "action": "search", "query": "Compare approaches used by major Agentic AI frameworks and SDKs.", "hits": 0, "new_evidence": 0, "unique_sources": 0, "missing_facets": ["framework", "tool-use", "state"]}
[agent] {"step": 2, "action": "search", "query": "Compare approaches used by major Agentic AI frameworks and SDKs. framework", "hits": 4, "new_evidence": 4, "unique_sources": 4, "missing_facets": []}
```

The first broad search is intentionally allowed to fail. The agent keeps state, recognizes that important evidence is still missing, and continues with the next planned query.

## Example Report Shape

```text
# Research Report

Question: Compare approaches used by major Agentic AI frameworks and SDKs.

Agent status: enough_evidence after 2 research step(s).

## Research Plan
...

## Findings

### [S1] Microsoft Agent Framework
...

### [S2] Pydantic AI
...

### [S3] CrewAI
...

### [S4] Google Agent Development Kit (ADK)
...

## Evidence Coverage
- Unique sources collected: 4
- Required facets: framework, tool-use, state
- Missing required facets: none

## Sources
- [S1] ...
- [S2] ...

## Limitations
- This project searches a bundled corpus, not the live web.
...
```

The exact ranking and source order can change if the corpus or search weights are updated.
