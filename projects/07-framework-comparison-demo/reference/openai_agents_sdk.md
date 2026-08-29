# OpenAI Agents SDK Reference Mapping

Official documentation: https://openai.github.io/openai-agents-python/

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

A comparable OpenAI Agents SDK implementation would typically map the task to:

```text
Agent
  ↓
Runner
  ↓
function tools / specialist agents
  ↓
handoff or agent-as-tool routing
  ↓
guardrails / approval boundary
  ↓
RunResult or structured output
```

Relevant SDK primitives documented by OpenAI include:

- `Agent`
- `Runner`
- function tools
- handoffs
- agents-as-tools
- guardrails
- sessions
- human-in-the-loop flows
- tracing
- MCP tools

## Cost / Runtime Note

The official quickstart configures an OpenAI API key for normal model-backed runs.

This repository therefore **does not automatically run a live OpenAI Agents SDK model call**.

That is intentional: the zero-cost comparison should not create API spend merely to prove that an SDK can call a model.

## What to Compare

When evaluating this SDK for a real project, ask:

- Do I want the runtime to manage the agent loop?
- Are tools, handoffs, guardrails, sessions, and tracing useful built-ins for my design?
- Am I comfortable with the runtime abstractions around turns and tool execution?
- Which model/provider will I use and what will it cost?
- Which actions need explicit approval?

Always check the current official documentation before implementing production code.
