# Sample Session

## Success

```bash
python main.py demo success
```

Expected:

```text
status: ok
provider: mock-primary
degraded: false
```

## Retry Recovery

```bash
python main.py demo retry
```

Expected:

```text
transient failure
retry
timeout
retry
success
```

## Fallback

```bash
python main.py demo fallback
```

Expected:

```text
provider: local-fallback
degraded: true
```

## Fresh Cache

```bash
python main.py demo cache
```

Expected on the second response:

```text
cache_status: fresh
```

## Stale-if-Error

```bash
python main.py demo stale
```

Expected:

```text
status: degraded
cache_status: stale
```

## Circuit Breaker

```bash
python main.py demo circuit
```

The health output shows the provider circuit state after repeated failures.

## Complete Outage

```bash
python main.py demo unavailable
```

Expected:

```text
status: unavailable
```

## Structured Logs

```bash
python main.py demo retry --trace
```

Each emitted JSON event uses the same trace ID for that request.
