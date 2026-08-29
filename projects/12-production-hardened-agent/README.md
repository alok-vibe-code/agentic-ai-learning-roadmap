# Project 12: Production-Hardened Agent

This is the Week 12 working project in the **Agentic AI Learning Roadmap**.

The goal is not to add another clever agent pattern. The goal is to take a bounded research-style agent and add the operational controls that separate a happy-path prototype from a service that can fail predictably.

The project runs entirely offline.

No model API, API key, network access, or paid service is required.

---

## What "Production Hardened" Means Here

The project demonstrates a reliability envelope around provider calls:

```text
Request
   ↓
Validation
   ↓
Rate limiting
   ↓
Fresh cache?
   ├── Yes → return
   └── No
        ↓
Request budget
        ↓
Overall deadline
        ↓
Primary provider
        ↓
Retryable failure?
   ├── Yes → bounded retry + backoff + jitter
   └── No / exhausted
        ↓
Circuit breaker
        ↓
Fallback provider
        ↓
Fallback succeeds?
   ├── Yes → degraded success
   └── No
        ↓
Stale cache?
   ├── Yes → stale-if-error response
   └── No → explicit unavailable response
```

The system does not turn an outage into fabricated success.

---

# Reliability Controls

## 1. Bounded Retries

Only failures classified as retryable are retried:

- transient provider errors
- provider timeouts

Permanent failures are not retried.

The default policy allows:

```text
3 attempts per provider
```

Retries are also bounded by the request-level provider-attempt budget.

---

## 2. Exponential Backoff

Backoff grows by attempt:

```text
base × 2^(attempt - 1)
```

and is capped by:

```text
max_backoff_ms
```

---

## 3. Jitter

A configurable jitter ratio can move a backoff value slightly up or down.

This reduces synchronized retry storms when many workers fail at the same time.

The deterministic demo injects a fixed random value so tests are reproducible.

---

## 4. Per-Attempt Timeout Contract

Every provider call receives:

```text
attempt_timeout_ms
```

The local provider simulator honors this timeout contract deterministically.

A production HTTP or model SDK integration should additionally configure transport-level:

- connection timeouts
- read timeouts
- cancellation
- request deadlines

---

## 5. Overall Request Deadline

Retries and fallbacks do not have unlimited time.

Before every provider attempt and retry backoff, the resilience layer checks the overall request deadline.

This prevents a chain of individually reasonable retries from creating an unreasonable end-to-end latency.

---

## 6. Circuit Breaker

Each provider has an independent circuit breaker.

States:

```text
CLOSED
   ↓ repeated failures
OPEN
   ↓ cooldown expires
HALF_OPEN
   ↓ success
CLOSED
```

A failed half-open probe returns the circuit to `OPEN`.

An open primary circuit does not automatically make the entire agent unavailable because the fallback provider has its own circuit.

---

## 7. Provider Fallback

The agent prefers:

```text
mock-primary
```

If the primary fails, the agent can route to:

```text
local-fallback
```

A fallback answer is marked:

```json
{
  "degraded": true
}
```

so availability does not hide reduced service quality.

---

## 8. Fresh Cache

Successful provider responses are cached by normalized query hash.

A fresh cache hit:

- avoids another provider call
- consumes zero provider-attempt budget
- reduces latency
- reduces simulated cost

---

## 9. Stale-if-Error

After the normal TTL expires, a cached value may remain usable inside the larger stale window.

If both providers fail during that period, the agent can return:

```text
status = degraded
cache_status = stale
```

This is explicit graceful degradation.

Once the stale window also expires, the cache cannot mask the outage.

---

## 10. Rate Limiting

Requests are limited per principal using a sliding time window.

Default:

```text
20 requests / 60 seconds / principal
```

This protects shared capacity and prevents one caller from consuming all provider resources.

---

## 11. Request Budgets

Each request receives independent limits for:

- provider attempts
- estimated tokens
- simulated provider cost

Default:

```text
max provider attempts: 5
max estimated tokens: 2500
max simulated cost: $0.02
```

The monetary value is **simulation metadata only**. Nothing is charged.

A fallback cannot continue indefinitely after the budget has been exhausted.

---

## 12. Structured Logging

Operational events are represented as JSON-compatible records.

Examples:

```text
provider_attempt
retry_scheduled
provider_failure
provider_success
fallback_selected
cache_hit
stale_cache_used
request_unavailable
```

Each record includes the same `trace_id`.

---

## 13. Trace IDs

Every request receives a trace ID.

The ID is propagated through:

- provider attempts
- retries
- fallback selection
- cache decisions
- completion events

This makes a single request reconstructable from logs.

---

## 14. Metrics

The in-memory registry tracks counters such as:

```text
requests
requests_succeeded
requests_unavailable
provider_attempts
provider_success
provider_retryable_failure
provider_permanent_failure
provider_timeout
retries
fallback_attempted
fallback_success
cache_hit_fresh
cache_hit_stale
rate_limited
circuit_opened
budget_exceeded
deadline_exceeded
graceful_degradation
```

A production deployment would export equivalent metrics to an observability backend.

---

## 15. Health Snapshot

The agent exposes a bounded health snapshot containing:

- overall health
- primary circuit state
- fallback circuit state
- cache size
- current metric counters

The demo uses:

```text
healthy
degraded
unhealthy
```

based on circuit state.

---

## 16. Configuration Validation

Operational behavior is stored in:

```text
config/default.json
```

The loader validates:

- required sections
- positive integer fields
- retry/backoff relationships
- jitter range
- cache stale window
- provider names
- budget values

Invalid configuration fails at startup rather than producing surprising runtime behavior.

---

# Local Failure Injection

`ScriptedProvider` supports deterministic outcomes:

```text
success
transient
timeout
permanent
```

Example:

```python
["transient", "timeout", "success"]
```

means:

1. first call fails transiently
2. second call times out
3. third call succeeds

This makes reliability behavior testable without deliberately breaking a real API.

---

# Graceful Degradation

The fallback order is:

```text
fresh cache
→ primary
→ fallback
→ stale cache
→ explicit unavailable response
```

If no trustworthy answer is available, the final response is:

```text
The agent is temporarily unavailable.
No unsupported answer was generated.
```

This is intentional.

Production hardening is not about making every request appear successful.

---

# Run the Project

## Happy Path

```bash
python main.py demo success
```

## Retry Recovery

```bash
python main.py demo retry
```

Expected flow:

```text
primary transient failure
↓
retry
↓
primary timeout
↓
retry
↓
primary success
```

## Provider Fallback

```bash
python main.py demo fallback
```

Expected:

```text
primary permanent failure
↓
fallback success
↓
degraded = true
```

## Fresh Cache

```bash
python main.py demo cache
```

The second request should return:

```text
cache_status = fresh
```

## Stale-if-Error

```bash
python main.py demo stale
```

Expected:

```text
providers unavailable
↓
stale cached answer
↓
status = degraded
```

## Circuit Breaker

```bash
python main.py demo circuit
```

## Complete Outage

```bash
python main.py demo unavailable
```

Expected:

```text
status = unavailable
```

## Structured Trace Output

```bash
python main.py demo retry --trace
```

The terminal will include JSON structured operational events.

## Direct Query

```bash
python main.py ask "Why are circuit breakers useful?"
```

## Health Snapshot

```bash
python main.py health
```

---

# Project Structure

```text
12-production-hardened-agent/
├── README.md
├── main.py
├── models.py
├── errors.py
├── config.py
├── circuit_breaker.py
├── cache.py
├── rate_limit.py
├── budget.py
├── telemetry.py
├── service.py
├── resilience.py
├── agent.py
├── health.py
├── test_production_agent.py
├── requirements.txt
├── sample_session.md
├── config/
│   └── default.json
└── data/
    └── knowledge.json
```

---

# Testing

Run:

```bash
python -m unittest test_production_agent.py
```

The test suite covers:

- configuration validation
- exponential backoff
- jitter bounds
- transient retries
- timeout retries
- permanent failures
- request deadlines
- attempt budgets
- token budgets
- simulated-cost budgets
- circuit CLOSED / OPEN / HALF_OPEN transitions
- independent provider circuits
- fallback routing
- fresh cache behavior
- stale-if-error
- LRU eviction
- cache expiry
- per-principal rate limiting
- structured logs
- trace propagation
- metric counters
- health snapshots
- query normalization
- cache-key stability
- failure injection
- graceful unavailable responses
- successful primary recovery
- provider fallback recovery

---

# Deployment Notes

This project deliberately stops before pretending that an in-memory demo is a complete production platform.

A real deployment should additionally evaluate:

- process supervision
- container resource limits
- autoscaling
- durable distributed caches
- distributed rate limiting
- distributed circuit-breaker semantics where appropriate
- durable metrics and traces
- centralized logs
- secrets management
- TLS
- authentication and authorization
- database transactions
- idempotency across workers
- queue semantics
- network egress restrictions
- dependency SLAs
- regional failover
- model/provider-specific error taxonomies
- load testing
- chaos testing
- incident response
- alert thresholds
- SLOs and error budgets
- rollback procedures

---

# Production Readiness Checklist

Review the repository's:

[Production Readiness Checklist](../../checklists/production-readiness.md)

against this project.

The most important lesson is that reliability controls interact.

Retries without budgets can amplify load.

Fallbacks without observability can hide degraded quality.

Caching without expiry can preserve stale data indefinitely.

Circuit breakers without recovery probes can turn transient failures into permanent outages.

Production engineering is the discipline of making those trade-offs explicit and testable.

Return to the [main roadmap](../../README.md).
