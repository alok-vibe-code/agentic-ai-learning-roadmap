# Sample Session: Project 06 Agent Pattern Examples

## Run All Patterns

```bash
python main.py all
```

Expected sections:

```text
=== Reflection ===
=== Planning ===
=== Routing ===
=== Parallelization ===
=== Evaluator-Optimizer ===
=== Human-in-the-Loop ===
```

## Reflection

```bash
python main.py reflection "Agents help"
```

Expected behavior:

- critique weak draft
- revise it
- stop when the deterministic threshold is met or the round limit is reached

## Planning

```bash
python main.py planning "Build a small agent evaluation tool"
```

Expected behavior:

- produce dependency-aware steps
- validate the plan

## Routing

```bash
python main.py routing "Calculate 12 * 7"
```

Expected:

```text
route=calculator ...
Calculator result: 84
```

## Parallelization

```bash
python main.py parallel alpha "fail:demo failure" gamma
```

Expected:

- alpha succeeds
- the requested demo task returns an error result
- gamma succeeds
- all task outcomes are retained in input order

## Evaluator-Optimizer

```bash
python main.py evaluator "Useful automation"
```

Expected behavior:

- weak candidate is evaluated
- targeted improvements are applied
- final score is printed

## Human-in-the-Loop

Blocked by default:

```bash
python main.py hitl "publish the report"
```

Expected:

```text
BLOCKED: action was not approved.
```

Explicit approval:

```bash
python main.py hitl "publish the report" --approve
```

Expected:

```text
SIMULATED ONLY
```

No real publishing occurs.
