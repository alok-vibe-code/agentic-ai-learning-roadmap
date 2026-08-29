# Project 06: Agent Pattern Examples

This is the Week 6 working project in the **Agentic AI Learning Roadmap**.

Instead of building one increasingly complicated agent, this project isolates six common control-flow patterns so you can see what each one actually contributes.

The six runnable examples are:

1. Reflection
2. Planning
3. Routing
4. Parallelization
5. Evaluator-optimizer
6. Human-in-the-loop

All examples are:

- deterministic
- inspectable
- bounded
- framework-free
- API-key-free
- runnable with Python's standard library

## Why Patterns Matter

"Agentic" is not one architecture.

A task may need:

- one revision loop
- a plan
- a router
- independent parallel work
- an evaluator
- a human approval gate

It may not need all of them.

The design principle for this project is:

> **Use the smallest pattern that solves the control-flow problem.**

## Project Structure

```text
06-agent-pattern-examples/
├── README.md
├── main.py
├── models.py
├── test_agent_patterns.py
├── requirements.txt
├── sample_session.md
└── patterns/
    ├── __init__.py
    ├── reflection.py
    ├── planning.py
    ├── routing.py
    ├── evaluator_optimizer.py
    ├── parallelization.py
    └── human_in_loop.py
```

## Pattern 1: Reflection

Reflection adds a review loop around an initial result.

```text
Draft
  ↓
Critique
  ↓
Good enough?
 ↙       ↘
Yes       No
 ↓         ↓
Stop     Revise
           ↓
        Critique again
```

The example checks simple quality signals such as:

- sufficient detail
- explanation
- filler words
- punctuation
- repetition

The loop is bounded by `max_rounds`.

Run:

```bash
python main.py reflection "Agents help"
```

The trace shows each critique and revision step.

### When Reflection Helps

Use reflection when:

- one draft may need correction
- quality criteria are inspectable
- another pass has clear value
- iteration can be bounded

Avoid it when:

- the task is already deterministic
- there is no measurable review criterion
- repeated revisions add cost without quality gains

## Pattern 2: Planning

Planning decomposes a goal into ordered steps and explicit dependencies.

```text
Goal
 ↓
Clarify success
 ↓
Decompose
 ↓
Add dependencies
 ↓
Validate DAG
 ↓
Execute later
```

Run:

```bash
python main.py planning "Build a small agent evaluation tool"
```

The demo validates:

- unique step IDs
- valid dependencies
- no self-dependency
- no dependency cycles

### Why Validate a Plan?

A plan that contains impossible dependencies is not useful merely because it looks structured.

The validation layer makes the plan executable as a workflow later.

## Pattern 3: Routing

Routing chooses a specialist based on the request.

```text
Request
   ↓
Score possible routes
   ↓
Unique strong match?
  ↙             ↘
Yes              No
 ↓                ↓
Specialist      General fallback
```

The available routes are:

- `calculator`
- `text`
- `research`
- `general`

Run:

```bash
python main.py routing "Calculate 12 * 7"
```

The calculator uses a restricted AST evaluator rather than Python `eval()`.

### Safe Fallback

If no specialist matches clearly, the request goes to `general`.

The router does not force every input into a specialist.

## Pattern 4: Parallelization

Parallelization is useful when tasks are independent.

```text
Task A ─┐
Task B ─┼─ run concurrently ─→ collect
Task C ─┘
```

Run:

```bash
python main.py parallel alpha beta gamma
```

Failure isolation demo:

```bash
python main.py parallel alpha "fail:demo failure" gamma
```

The failed task does not erase successful results from the other tasks.

The returned list preserves input order even though completion order may differ.

### When Not to Parallelize

Do not parallelize tasks when:

- B depends on A
- order changes correctness
- shared mutable state creates race conditions
- the work is so small that concurrency overhead dominates

## Pattern 5: Evaluator-Optimizer

This pattern separates producing a candidate from scoring its quality.

```text
Candidate
   ↓
Evaluate
   ↓
Score high enough?
  ↙            ↘
Yes             No
 ↓               ↓
Stop          Optimize
                 ↓
             Evaluate again
```

Run:

```bash
python main.py evaluator "Useful automation"
```

The evaluator looks for:

- enough detail
- a clear subject
- a mechanism
- concise length
- punctuation

The optimizer attempts targeted corrections.

The loop stops when:

- the score reaches the quality threshold, or
- `max_rounds` is reached

### Reflection vs Evaluator-Optimizer

They are related but not identical.

**Reflection** focuses on critique and revision.

**Evaluator-optimizer** makes a measurable scoring function a first-class component.

If you can define a meaningful metric, the evaluator-optimizer pattern makes the stopping rule easier to inspect.

## Pattern 6: Human-in-the-Loop

Some actions should not execute merely because an agent selected them.

The example classifies actions as:

- low risk
- medium risk
- high risk

```text
Proposed action
      ↓
Classify risk
      ↓
Low risk?
 ↙          ↘
Yes          No
 ↓            ↓
Auto allow   Human approval?
               ↙        ↘
             Yes         No
              ↓           ↓
          Simulate      Block
```

Read-only actions such as:

```text
read
search
calculate
inspect
summarize
list
view
```

are low risk.

Actions such as:

```text
send
publish
delete
purchase
pay
transfer
deploy
modify
post
submit
```

require approval.

Run a blocked action:

```bash
python main.py hitl "publish the report"
```

Then simulate explicit approval:

```bash
python main.py hitl "publish the report" --approve
```

### Important Safety Choice

This project **does not perform a real external side effect**.

Even after approval it prints:

```text
SIMULATED ONLY
```

The purpose is to teach the approval boundary without publishing, deleting, sending, or purchasing anything.

## Run All Six Patterns

```bash
python main.py all
```

This gives a compact demonstration of the entire pattern lab.

## Run the Tests

```bash
python -m unittest test_agent_patterns.py
```

The test suite checks:

### Reflection

- empty draft handling
- strong draft acceptance
- weak draft revision
- bounded iteration
- invalid round limits

### Planning

- implementation plans
- research plans
- blank-goal rejection
- duplicate IDs
- unknown dependencies
- cycle detection

### Routing

- calculator routing
- research routing
- general fallback
- blank-request rejection
- calculator execution
- blocking unsupported calculator expressions

### Evaluator-Optimizer

- empty candidate scoring
- strong candidate acceptance
- weak candidate improvement
- bounded iteration
- invalid round limits

### Parallelization

- output order
- successful results
- failure isolation
- empty-task rejection
- invalid worker counts

### Human-in-the-Loop

- low-risk classification
- high-risk classification
- ambiguous-risk handling
- automatic low-risk approval
- blocking sensitive actions
- explicit human approval
- blank-action rejection

## Pattern Selection Guide

| Situation | Smallest useful pattern |
|---|---|
| Draft needs one or more review passes | Reflection |
| Goal needs ordered decomposition | Planning |
| Different specialists handle different request types | Routing |
| Independent subtasks can run at the same time | Parallelization |
| Output quality can be scored and improved | Evaluator-optimizer |
| Sensitive action requires consent | Human-in-the-loop |

## Pattern Composition

Real systems can combine patterns.

For example:

```text
User goal
   ↓
Planning
   ↓
Routing
   ↓
Parallel research
   ↓
Evaluator
   ↓
Sensitive publish step
   ↓
Human approval
```

But composition should be justified.

Every additional pattern creates more:

- state
- failure modes
- test cases
- latency
- observability requirements

Start with the smallest adequate design.

## What This Project Does Not Do

It does not:

- call an LLM
- use an agent framework
- make network requests
- perform real external actions
- pretend deterministic keyword routing is semantic reasoning
- claim the simple scoring functions are production evaluators

Those limitations are deliberate.

The goal is to make **control flow** visible before frameworks abstract it away.

## Exercises

### Beginner

Add a new `code` route to the routing example.

### Intermediate

Add a timeout to the parallelization example and represent timed-out work separately from ordinary failures.

### Challenge

Make the planner output two tasks that can run in parallel, then use the parallelization pattern to execute only those independent steps.

### Advanced Challenge

Compose:

```text
planning
→ routing
→ evaluator-optimizer
→ human-in-the-loop
```

for a small content-publishing workflow.

Keep the final publish step simulated.

## Next Step

Week 7 moves from pattern fundamentals to **Agent Frameworks and SDKs**.

Instead of asking which framework is "best," the next project will compare how a small common task is represented across a limited set of framework approaches and what tradeoffs each abstraction introduces.

Return to the [main roadmap](../../README.md).
