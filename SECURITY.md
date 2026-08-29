# Security Policy

This repository contains educational code that interacts with external AI APIs.

## Protect Your Credentials

- Store API keys in local environment variables.
- Use `.env` locally and keep it ignored by Git.
- Never place real credentials in `.env.example`, screenshots, issues, commits, or pull requests.
- Use separate development credentials where possible.
- Apply minimum necessary permissions to external services.

## If You Accidentally Commit a Secret

1. Revoke or rotate the secret immediately.
2. Remove it from the current repository state.
3. Remove it from Git history when necessary.
4. Check provider logs for unexpected use.
5. Do not assume deleting the latest file version makes the secret safe.

## AI-Specific Security

Examples in this roadmap should treat these as untrusted:

- User input
- Retrieved webpages
- Documents
- Tool output
- Model-generated arguments

Before adding projects that can take external actions, use:

- Input validation
- Tool argument validation
- Allowlisted capabilities
- Least privilege
- Timeouts and step limits
- Human approval for sensitive actions
- Audit logging where appropriate

## Vulnerability Reports

Do not publish API keys, credentials, or exploit details in a public issue.

If you discover a vulnerability in code from this repository, contact the repository maintainer privately through an appropriate private channel before public disclosure.
