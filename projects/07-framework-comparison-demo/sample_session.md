# Sample Session: Project 07 Framework Comparison Demo

## 1. Capability Matrix

```bash
python main.py matrix
```

Use this to compare the same capability vocabulary across all bundled profiles.

## 2. Run the Common Task

```bash
python main.py task "I was charged twice and need a refund."
```

Expected characteristics:

```text
route: billing
risk: high
requires_human: true
```

## 3. Technical Request

```bash
python main.py task "Our API integration returns timeout errors."
```

Expected characteristics:

```text
route: technical
risk: low
requires_human: false
```

## 4. Inspect LangGraph

```bash
python main.py profile langgraph
```

## 5. Filter by Requirements

```bash
python main.py recommend \
  --require human_approval mcp \
  --prefer provider_flexibility offline_testing
```

The command does not declare a universal winner.

It filters hard requirements first, then uses the bundled preference-strength values for deterministic ordering.

## 6. Compare Task Architecture

```bash
python main.py compare-task \
  "The API integration is returning timeout errors."
```

This shows the normalized result and the conceptual mapping for:

- OpenAI Agents SDK
- LangGraph
- Pydantic AI
