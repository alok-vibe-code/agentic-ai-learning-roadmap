# Project 10: Agent Evaluation Harness

This is the Week 10 working project in the **Agentic AI Learning Roadmap**.

The project turns expected agent behavior into repeatable evaluation cases and observable traces.

A good-looking answer is not enough.

The harness asks:

- Did the agent complete the intended task?
- Did it choose the correct tool?
- Did it include required content?
- Did it avoid forbidden content?
- Did it cite when citations were required?
- Were citations grounded in sources actually returned by tools?
- Did the run stay within its step budget?
- Is the trace structurally valid?
- Did the candidate regress against an accepted baseline?

## Why This Project Is Offline

The goal is to understand **evaluation mechanics** without requiring:

- an API key
- a model provider
- a tracing vendor
- a network request
- a paid service

The project uses two deterministic candidates:

```text
good
broken
```

The **good** candidate satisfies the suite.

The **broken** candidate intentionally creates:

- a calculator-routing regression
- ungrounded citation regressions

That is important.

An evaluation harness that can only produce green reports has not demonstrated that it can detect failures.

## Evaluation Case Format

Each case is stored in:

```text
data/eval_cases.json
```

Example:

```json
{
  "id": "mcp_spec",
  "query": "Find the official MCP specification.",
  "expected_status": "completed",
  "expected_tool": "local_search",
  "must_include": [
    "Model Context Protocol",
    "specification"
  ],
  "must_not_include": [],
  "must_cite_source": true,
  "allowed_source_ids": [
    "MCP-SPEC"
  ],
  "max_steps": 4
}
```

## Case-Level Checks

For every run, the evaluator checks:

```text
expected status
correct tool
required / forbidden content
citation requirement
citation groundedness
step budget
trace integrity
unexpected error
```

Each check produces:

```text
name
passed
detail
```

The case also receives a normalized score.

## Groundedness

This project uses a deliberately strict mechanical definition:

> A citation is grounded only when the cited source ID was actually returned by an observed tool call and is permitted by the evaluation case.

That means a candidate cannot pass by inventing a plausible-looking citation.

Example:

```text
tool returned: MCP-SPEC
candidate cited: MCP-SPEC
→ grounded

tool returned: MCP-SPEC
candidate cited: UNOBSERVED-SOURCE
→ not grounded
```

This is not a complete semantic factuality grader, but it is a useful deterministic foundation.

## Observability

Every candidate run produces a vendor-neutral trace.

A trace event includes:

```text
sequence
trace_id
span_id
parent_span_id
kind
name
attributes
```

Example structure:

```text
agent.run
├── local_search
└── agent.response
```

The harness validates:

- a trace exists
- all events share one trace ID
- sequence numbers are contiguous
- parent span references exist
- a root span exists
- a run event exists

## Metrics

The suite aggregates:

```text
case_pass_rate
task_completion_accuracy
tool_selection_accuracy
content_check_pass_rate
citation_pass_rate
groundedness_pass_rate
trace_integrity_pass_rate
failure_rate
average_latency_ms
estimated_tokens
reported_cost_usd
```

### Important Measurement Note

`average_latency_ms` is observed wall-clock runtime for this local demo.

`estimated_tokens` is a provider-independent approximation.

`reported_cost_usd` is zero because the bundled candidate makes no model call.

These are operational signals, not universal quality metrics.

## Regression Checking

The versioned baseline is stored in:

```text
data/baseline.json
```

It supports:

```text
metric_floors
metric_ceilings
```

Example:

```json
{
  "metric_floors": {
    "case_pass_rate": 1.0,
    "groundedness_pass_rate": 1.0
  },
  "metric_ceilings": {
    "failure_rate": 0.0,
    "reported_cost_usd": 0.0
  }
}
```

A regression check fails when a required floor or ceiling is violated.

## Run the Good Candidate

```bash
python main.py evaluate \
  --candidate good \
  --format markdown \
  --regression
```

Expected:

```text
8/8 cases pass
case_pass_rate = 1.0
groundedness_pass_rate = 1.0
regression = passed
```

## Run the Broken Candidate

```bash
python main.py evaluate \
  --candidate broken \
  --format markdown
```

This command is expected to exit non-zero because the candidate fails evaluation cases.

Typical detected problems:

```text
wrong calculator tool
ungrounded citations
disallowed source IDs
```

## JSON Output

```bash
python main.py evaluate \
  --candidate good \
  --format json \
  --regression
```

This produces machine-readable results suitable for CI integration.

## Evaluate One Case

```bash
python main.py case mcp_spec --candidate good
```

Broken version:

```bash
python main.py case mcp_spec --candidate broken
```

## Inspect a Trace

```bash
python main.py trace mcp_spec --candidate good
```

## List Cases

```bash
python main.py cases
```

## Project Structure

```text
10-agent-evaluation-harness/
├── README.md
├── main.py
├── models.py
├── cases.py
├── demo_agent.py
├── observability.py
├── evaluator.py
├── metrics.py
├── regression.py
├── reporters.py
├── test_evaluation_harness.py
├── requirements.txt
├── sample_session.md
└── data/
    ├── eval_cases.json
    └── baseline.json
```

## Safety and Reliability Boundaries

The bundled candidate:

- makes no network request
- executes no shell command
- uses a restricted AST calculator
- does not evaluate arbitrary Python
- does not access private user data
- abstains from live-data questions
- caps input length
- reports zero model cost because it makes no model call

The evaluator:

- treats candidate output as data
- does not execute output
- uses bounded versioned cases
- exposes exact failed checks
- keeps regression thresholds explicit

## Tests

Run:

```bash
python -m unittest test_evaluation_harness.py
```

The tests cover:

- evaluation-case validation
- duplicate IDs
- trace creation
- trace validation
- parent span integrity
- calculator safety
- candidate routing
- abstention
- citations
- groundedness
- required and forbidden content
- step budgets
- case scoring
- aggregate metrics
- baseline loading
- regression floors
- regression ceilings
- Markdown reporting
- JSON reporting
- good-candidate behavior
- broken-candidate detection
- deterministic trace IDs
- zero-cost metadata
- offline behavior

## Exercises

### Beginner

Add an evaluation case for a new local-search topic.

### Intermediate

Add a `max_cost_usd` requirement at the case level.

### Challenge

Add a semantic grader interface that can be implemented either deterministically or by an external model.

### Advanced

Wrap a real agent behind the same `AgentRun` contract and execute this harness in CI.

## Next Step

Week 11 introduces a **Secure Approval-Based Agent** with explicit risk classification, least privilege, and human approval gates.

Return to the [main roadmap](../../README.md).
