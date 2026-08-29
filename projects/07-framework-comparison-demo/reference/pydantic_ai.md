# Pydantic AI Reference Mapping

Official documentation: https://ai.pydantic.dev/

Official testing guide: https://pydantic.dev/docs/ai/guides/testing/

Verified for this educational comparison: **August 29, 2026**

## Same Task

The normalized task is:

```text
Receive a support request
→ choose a specialist route
→ inspect whether the requested action is sensitive
→ require approval when necessary
→ return a structured result
```

## Conceptual Mapping

A comparable Pydantic AI implementation would emphasize typed inputs and outputs:

```text
Agent
  ↓
instructions + dependencies
  ↓
typed tools
  ↓
validated structured output
  ↓
approval-aware/deferred actions where needed
```

The current documentation includes support for:

- agents
- dependencies
- typed outputs
- function tools and toolsets
- multiple model providers
- MCP
- instrumentation
- multi-agent patterns
- durable-execution integrations

## Offline Testing

Pydantic AI's official testing guide explicitly recommends `TestModel` or `FunctionModel` to avoid the usage, latency, and variability of real model calls.

It also documents `ALLOW_MODEL_REQUESTS=False` as a way to prevent accidental calls to non-test models during tests.

That makes offline testing a useful comparison point.

## What to Compare

Ask:

- Is typed validation central to my system?
- Do I want strong schema-driven tool and output ergonomics?
- Which provider will I use?
- Do I need a separate workflow/orchestration layer?
- How will I test provider-independent application logic?

Always check the current official documentation before implementing production code.
