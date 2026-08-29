# Sample Session

## Team

```bash
python main.py team \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling." \
  --trace
```

Expected:

```text
status: approved
roles_used: 5
coverage_ratio: 1.0
coordination_messages: > 0
```

## Single-Agent Baseline

```bash
python main.py single \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling."
```

Expected:

```text
roles_used: 1
coordination_messages: 0
```

## Compare

```bash
python main.py compare \
  "Compare single-agent and multi-agent research systems for reliability, coordination overhead, and failure handling."
```

## Simple Question

```bash
python main.py compare "What is agent handoff?"
```

The simpler baseline should remain the conservative recommendation.

## Sources

```bash
python main.py sources
```

All source URLs use `local://`, confirming that the demo is offline.
