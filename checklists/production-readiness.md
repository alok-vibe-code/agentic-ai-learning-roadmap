# Production Readiness Checklist for AI Agents

Use this checklist before treating an agent prototype as production-ready.

## Scope and Architecture

- [ ] The task is clearly defined.
- [ ] Agent autonomy is necessary for the parts where it is used.
- [ ] Deterministic logic is used where deterministic logic is sufficient.
- [ ] Maximum agent steps are bounded.
- [ ] Failure and stopping conditions are explicit.

## Models and Prompts

- [ ] Model choice is configurable.
- [ ] Prompt changes are versioned.
- [ ] Structured outputs are validated.
- [ ] Refusals and incomplete responses are handled.
- [ ] Model fallbacks are defined when required.

## Tools

- [ ] Every tool has a narrow purpose.
- [ ] Tool arguments are validated.
- [ ] Tool permissions follow least privilege.
- [ ] Destructive or externally visible actions require appropriate approval.
- [ ] Tool timeouts are configured.
- [ ] Tool failures are handled gracefully.

## Retrieval and External Content

- [ ] Retrieved content is treated as untrusted.
- [ ] Prompt-injection risks are considered.
- [ ] Source provenance is retained where needed.
- [ ] Retrieval quality is evaluated.
- [ ] Sensitive data is not indexed without authorization.

## Memory and State

- [ ] Only necessary information is persisted.
- [ ] Sensitive data retention is documented.
- [ ] Users can correct or delete persistent information when appropriate.
- [ ] State corruption and stale memory have recovery paths.

## Evaluation

- [ ] Representative evaluation cases exist.
- [ ] Expected tool behavior is tested.
- [ ] Failure cases are included.
- [ ] Accuracy / groundedness criteria are defined.
- [ ] Regression testing is possible.
- [ ] Latency and cost are measured.

## Security

- [ ] Secrets are stored outside source code.
- [ ] Inputs are validated.
- [ ] Outputs are validated before sensitive use.
- [ ] Authentication is implemented where required.
- [ ] Authorization is enforced at the tool / resource boundary.
- [ ] Prompt-injection scenarios are tested.
- [ ] Rate limiting exists where appropriate.
- [ ] Human approval protects high-risk actions.
- [ ] Audit trails exist for important actions.

## Reliability

- [ ] Retries are bounded.
- [ ] Exponential backoff is used where appropriate.
- [ ] Timeouts exist.
- [ ] Partial failures are handled.
- [ ] Idempotency is considered for repeated actions.
- [ ] The system can fail safely.

## Observability

- [ ] Requests have trace or correlation IDs.
- [ ] Tool calls can be inspected.
- [ ] Errors are logged without leaking secrets.
- [ ] Token usage can be measured.
- [ ] Cost can be monitored.
- [ ] Key quality indicators are observable.

## Deployment

- [ ] Configuration is environment-specific.
- [ ] Dependencies are controlled.
- [ ] Health checks exist when relevant.
- [ ] Rollback is possible.
- [ ] Deployment permissions are restricted.
- [ ] Production credentials are separate from development credentials.

## Final Question

Before release, answer:

> If the model makes a plausible but wrong decision, what prevents that decision from causing unacceptable harm?

If the answer is unclear, the system is not ready.
