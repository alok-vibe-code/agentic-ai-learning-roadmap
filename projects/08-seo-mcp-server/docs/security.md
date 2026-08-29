# Security Notes for the SEO MCP Server

## Primary Trust Boundary

The server accepts **HTML supplied by the MCP host**.

That HTML is untrusted content.

The parser:

- does not execute JavaScript
- does not load images
- does not follow links
- does not fetch external resources
- does not evaluate page text as instructions

## Why There Is No `fetch_url` Tool

MCP tools are model-callable capabilities.

An unrestricted network fetcher would create additional risks such as:

- SSRF against private/internal services
- access to cloud metadata endpoints
- redirects to unexpected hosts
- DNS rebinding
- large or slow responses
- credential leakage through URLs/headers
- accidental crawling
- robots/compliance questions
- page-level prompt injection being mixed with control instructions

For a learning project, the safer architecture is:

```text
trusted host / separate fetch layer
        ↓
validated HTML snapshot
        ↓
SEO MCP Server
```

If live fetching is added later, implement it as a separately reviewed component with:

- HTTP/HTTPS allowlisting
- private-IP blocking
- redirect limits
- response-size limits
- timeouts
- DNS-rebinding protections
- explicit user authorization
- no inherited browser cookies
- logging and rate limits

## Input Limits

The demo limits HTML input to 1,000,000 characters.

It also caps stored links/headings during parsing.

These are educational denial-of-service safeguards, not production tuning values.

## SEO Caveat

The project reports deterministic markup facts and clearly labeled review heuristics.

It does not claim:

- title length is a direct ranking factor
- meta-description length determines rankings
- one H1 is required by search engines
- a numerical SEO score predicts performance
