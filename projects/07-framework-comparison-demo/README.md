# Project 07: Framework Comparison Demo

This is the Week 7 working project in the **Agentic AI Learning Roadmap**.

The purpose of this project is **not** to declare a universal "best agent framework."

Instead, it creates a repeatable way to compare framework choices against:

1. the same task
2. the same capability vocabulary
3. the same hard requirements
4. the same preferences

The comparison currently covers:

- **OpenAI Agents SDK**
- **LangGraph**
- **Pydantic AI**

Framework data was checked against official documentation on **August 29, 2026**.

## Why This Project Is Different

Framework APIs change quickly.

A comparison repository becomes misleading if it:

- installs old SDK versions
- copies outdated examples
- silently makes paid API calls
- scores frameworks using unexplained opinions
- treats integrations as identical to native primitives
- declares a universal winner

This project therefore separates two concerns:

### Core comparison

Fully runnable with Python's standard library.

It includes:

- framework profiles
- capability matrix
- requirement filtering
- preference ranking
- normalized task
- framework architecture mappings

### Live framework execution

Not required for the core project.

Reference notes explain how the same task maps to each framework, but this repository does not automatically install framework packages or call paid model APIs.

That keeps the project:

- free
- deterministic
- testable
- transparent about what is and is not being executed

## The Common Task

All frameworks are compared against one support-triage problem:

```text
Support request
      ↓
Choose route
 ┌────┼────────┬─────────┐
billing technical account general
      ↓
Classify requested action risk
      ↓
Sensitive action?
   ↙          ↘
 no            yes
 ↓              ↓
continue     human approval
      ↓
structured triage result
```

Example:

```text
I was charged twice and need a refund.
```

Normalized result:

```text
route = billing
risk = high
requires_human = true
```

This task is deliberately small.

A framework should not receive extra credit merely because the demo task is made artificially complicated.

## Project Structure

```text
07-framework-comparison-demo/
├── README.md
├── main.py
├── models.py
├── profiles.py
├── comparison.py
├── common_task.py
├── test_framework_comparison.py
├── requirements.txt
├── sample_session.md
├── data/
│   └── frameworks.json
└── reference/
    ├── openai_agents_sdk.md
    ├── langgraph.md
    └── pydantic_ai.md
```

## Requirements

- Python 3.10+
- no API key
- no framework installation
- no paid service
- no network access at runtime

## Run the Common Task

```bash
python main.py task "I was charged twice and need a refund."
```

Example output:

```json
{
  "route": "billing",
  "risk": "high",
  "requires_human": true
}
```

The actual output also includes the proposed next action and reasons.

## Print the Capability Matrix

```bash
python main.py matrix
```

Capabilities include:

- state management
- tool calling
- structured outputs
- human approval
- tracing
- MCP
- multi-agent support
- provider flexibility
- durable execution
- offline testing

The values intentionally distinguish between:

```text
native
strong
supported
integration
provider-dependent
limited
not-core
```

Those words are not interchangeable.

For example, a capability available through an adjacent integration is not labeled as if it were the framework's core primitive.

## Inspect One Framework

OpenAI Agents SDK:

```bash
python main.py profile openai-agents-sdk
```

LangGraph:

```bash
python main.py profile langgraph
```

Pydantic AI:

```bash
python main.py profile pydantic-ai
```

## Requirement-Based Filtering

Suppose your application requires:

- human approval
- MCP

and you prefer:

- provider flexibility
- offline testing

Run:

```bash
python main.py recommend \
  --require human_approval mcp \
  --prefer provider_flexibility offline_testing
```

The algorithm works in two stages:

```text
Hard requirements
      ↓
Eligible?
  ↙        ↘
 no        yes
 ↓          ↓
exclude   score preferences
             ↓
          rank eligible
```

This is intentionally simple and explainable.

## Important: A Ranking Is Not a Verdict

The preference score is only a deterministic transformation of the bundled capability statuses.

It does **not** measure:

- framework quality
- reliability
- community size
- latency
- cost
- code quality
- long-term maintenance
- production suitability for every workload

Use it as a decision aid, not a leaderboard.

## Compare the Same Task Mapping

```bash
python main.py compare-task \
  "The API integration is returning timeout errors."
```

The command first runs the framework-neutral task.

It then shows how that task maps conceptually into each framework.

### OpenAI Agents SDK

Typical mapping:

```text
Agent + Runner
→ tools / specialist agents
→ handoffs or agents-as-tools
→ guardrails / approvals
→ structured result
```

### LangGraph

Typical mapping:

```text
StateGraph
→ nodes
→ conditional edges
→ explicit state
→ interrupt / human decision
→ compiled graph result
```

### Pydantic AI

Typical mapping:

```text
Agent
→ dependencies
→ typed tools
→ validated structured output
→ approval-aware action flow
```

## Current Comparison Snapshot

### OpenAI Agents SDK

Official docs:

https://openai.github.io/openai-agents-python/

The current SDK documentation describes a lightweight set of primitives around agents, tools, handoffs, guardrails, sessions, human-in-the-loop flows, MCP, and tracing.

The official quickstart uses an OpenAI API key for normal model-backed runs.

Therefore this repository does not automatically execute a live OpenAI model call.

### LangGraph

Official docs:

https://docs.langchain.com/oss/python/langgraph/overview

The current documentation describes LangGraph as a low-level orchestration framework/runtime for long-running, stateful agents.

Its focus includes:

- explicit orchestration
- durable execution
- persistence
- streaming
- human-in-the-loop
- memory
- mixing deterministic and model-driven nodes

A deterministic graph can run without making an LLM call.

### Pydantic AI

Official docs:

https://ai.pydantic.dev/

Testing guide:

https://pydantic.dev/docs/ai/guides/testing/

The current testing documentation recommends `TestModel` or `FunctionModel` for tests that should avoid live model usage.

It also documents disabling real model requests during tests.

## Why Only Three Frameworks?

The main roadmap lists more frameworks and SDKs.

This project intentionally limits the working comparison to three distinct styles:

| Framework | Primary comparison angle |
|---|---|
| OpenAI Agents SDK | managed agent runtime / compact primitives |
| LangGraph | explicit graph orchestration |
| Pydantic AI | typed agent and validation ergonomics |

Adding eight frameworks at once would make the first comparison shallow and harder to maintain.

More frameworks can be added later using the same profile schema.

## Add Another Framework

Edit:

```text
data/frameworks.json
```

Every profile must define the same capability keys.

Then add a reference note under:

```text
reference/
```

Before publishing the update:

1. use official documentation
2. record the verification date
3. distinguish native capabilities from integrations
4. do not infer features only from marketing language
5. run the tests

## Run the Tests

```bash
python -m unittest test_framework_comparison.py
```

The tests validate:

- framework profile schema
- unique IDs
- HTTPS documentation URLs
- capability vocabulary
- common task routing
- risk classification
- human-approval behavior
- capability aliases
- invalid capability rejection
- hard requirement filtering
- preference ranking
- deterministic ordering
- matrix completeness
- framework task mappings
- official reference-note presence

## Security and Cost Boundaries

This project:

- does not read API keys
- does not write secrets
- does not install third-party packages
- does not call external APIs
- does not send prompts to a model
- does not make purchases or paid requests
- does not execute copied framework snippets

The reference documents are educational architecture notes.

Re-check current official framework documentation before adapting them to production code.

## Exercises

### Beginner

Add `streaming` as a normalized comparison capability.

### Intermediate

Add Google Agent Development Kit as a fourth validated profile.

### Challenge

Create two scenarios:

```text
long-running stateful workflow
typed single-agent service
```

Give each scenario different hard requirements and preferences.

Observe how the filtered result changes.

### Advanced

Add an optional adapter layer that can execute installed frameworks locally.

Keep the zero-cost core as the default and require explicit opt-in for any provider-backed model call.

## Next Step

Week 8 introduces the **Model Context Protocol (MCP)** and builds an SEO-focused MCP server.

Return to the [main roadmap](../../README.md).
