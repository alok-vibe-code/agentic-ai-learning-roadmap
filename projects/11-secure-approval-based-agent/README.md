# Project 11: Secure Approval-Based Agent

This is the Week 11 working project in the **Agentic AI Learning Roadmap**.

The project demonstrates a central security rule for agent systems:

> A tool being available does not mean the agent should be allowed to execute it.

The implementation separates **planning, policy, authorization, approval, execution, and audit** so no single component silently grants itself authority.

## Policy Levels

### LOW

May execute automatically after authorization.

- local search
- allowlisted resource read
- bounded calculation

### SENSITIVE

Requires authorization **and** human approval.

- send email
- publish content
- delete a file
- modify an external record
- financial transfer

### FORBIDDEN

Never executes.

- shell execution
- secret access

### UNKNOWN

Fails closed.

## Workflow

```text
User request
   ↓
Input guardrails
   ↓
Planner
   ↓
Policy classification
   ↓
Authorization
   ↓
LOW ─────────────→ sandbox execution
   ↓
SENSITIVE
   ↓
Approval request
   ↓
Human approves exact action
   ↓
One-time signed approval token
   ↓
Token/action/principal/expiry validation
   ↓
Sandbox execution
   ↓
Hash-chained audit event
```

## Least Privilege Roles

### viewer

- `search`
- `read`
- `calculate`

### operator

Viewer permissions plus:

- `email.send`
- `content.publish`
- `external.modify`

### admin

Operator permissions plus:

- `file.delete`
- `finance.transfer`

Even `admin` cannot execute tools classified as `FORBIDDEN`.

## Approval Binding

Approval is bound to a canonical SHA-256 digest of:

- action type
- exact parameters
- idempotency key

The token is additionally bound to:

- approval request ID
- principal ID
- issue time
- expiry
- one-time nonce
- signed approver identity

Changing the destination, body, amount, path, or any other parameter after approval invalidates the approval.

## Replay Protection

Approval tokens are one-time use.

A successful sensitive execution consumes the nonce. Reusing the token is blocked.

## Approval Expiry

Approval requests have a configurable TTL.

The bundled policy uses:

```text
300 seconds
```

Expired requests cannot be approved, and expired tokens cannot execute an action.

## Prompt-Injection Signals

The input guardrail detects a bounded educational set of high-signal phrases such as:

- `ignore previous instructions`
- `reveal your system prompt`
- `disable security`
- `bypass approval`

This is not presented as a complete prompt-injection detector. The stronger protection is architectural: least privilege, constrained tools, authorization, approvals, and fail-closed execution.

## Secret Handling

Credential-like inputs are rejected, including patterns resembling:

- API keys
- passwords
- tokens
- private keys

The demo never requires or stores a real credential.

## Untrusted Tool Output

Allowlisted local resource content is treated as data.

Instruction-like output such as `ignore previous instructions` or `execute this command` is blocked rather than followed.

## Allowlisted Resource Reads

The demo can read only:

- `security-guide`
- `agent-policy`
- `deployment-checklist`

Arbitrary filesystem reads are not supported.

## Sandboxed Side Effects

All consequential tools are simulated in memory.

The project does **not**:

- send real email
- publish real content
- delete real files
- mutate real external systems
- transfer real money

This keeps the approval lifecycle runnable without creating real-world side effects.

## Financial Safety Limit

The bundled policy caps simulated transfers at:

```text
1000
```

Approval cannot override the executor's safety limit.

## Safe Calculator

The calculator parses a restricted arithmetic AST supporting only:

- addition
- subtraction
- multiplication
- division
- numeric constants
- unary negative values

It does not evaluate arbitrary Python.

## Rate Limiting

The bundled policy uses:

```text
10 requests / 60 seconds / principal
```

This is an in-memory educational rate limiter, not a distributed production implementation.

## Audit Log

Security-relevant events are stored in an append-only in-memory log:

- input guardrail decisions
- policy decisions
- authorization results
- approval requests
- approval grants/rejections
- execution outcomes
- rate-limit blocks

Each audit record includes the hash of the previous record, creating a tamper-evident chain.

## Idempotency

The sandbox executor supports optional idempotency keys.

A duplicate operation with the same key returns the previously stored result instead of duplicating the simulated side effect.

Idempotency does not bypass authorization or approval.

## Run Examples

### Low-Risk Auto Execution

```bash
python main.py demo low-risk
```

### Full Approval Lifecycle

```bash
python main.py demo approval
```

### Post-Approval Tampering

```bash
python main.py demo tamper
```

Expected:

```text
blocked
Action changed after approval.
```

### Forbidden Tool

```bash
python main.py demo forbidden
```

### Prompt Injection

```bash
python main.py demo injection
```

### Unauthorized Sensitive Action

```bash
python main.py demo unauthorized
```

## Direct Request Syntax

```text
search QUERY
read RESOURCE
calculate EXPRESSION
send email to ADDRESS subject SUBJECT body BODY
publish CONTENT
delete file PATH
modify record ID set FIELD=VALUE
transfer AMOUNT to DESTINATION
execute shell COMMAND
read secret NAME
```

The grammar is deliberately narrow to make the security boundaries inspectable.

## Project Structure

```text
11-secure-approval-based-agent/
├── README.md
├── main.py
├── models.py
├── guardrails.py
├── policy.py
├── planner.py
├── approvals.py
├── authorization.py
├── rate_limit.py
├── audit.py
├── executor.py
├── secure_agent.py
├── test_secure_agent.py
├── requirements.txt
├── sample_session.md
└── data/
    ├── policy.json
    └── knowledge.json
```

## Tests

```bash
python -m unittest test_secure_agent.py
```

The suite covers policy classification, least privilege, prompt-injection and secret signals, forbidden tools, approval binding, tampering, signatures, expiry, replay protection, cross-principal rejection, rejection workflow, allowlisted reads, malicious resource output, safe calculation, sandbox paths, financial limits, idempotency, rate limiting, audit-chain integrity, and complete low-risk and approval-gated workflows.

## Important Limitations

This is an educational security architecture, not a production identity or authorization product.

A production system should additionally consider external identity providers, MFA, approver authorization, durable transactional storage, cryptographic key management, distributed replay protection, distributed rate limiting, secret managers, network egress controls, stronger sandboxes, DLP, SIEM integration, incident response, compliance requirements, and adversarial security testing.

## Next Step

Week 12 upgrades an earlier agent into a **Production-Hardened Agent** with retries, timeouts, circuit breakers, configuration, structured logging, and graceful degradation.

Return to the [main roadmap](../../README.md).
