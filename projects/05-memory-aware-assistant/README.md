# Project 05: Memory-Aware Assistant

This is the Week 5 working project in the **Agentic AI Learning Roadmap**.

It demonstrates a core principle of production-oriented agent memory:

> **Do not persist everything merely because you can.**

The project separates **working memory** from **persistent memory** and gives the user explicit control over what is stored, retrieved, expired, updated, forgotten, and cleared.

It is designed to be **100% runnable without an API key or paid service**.

## What This Project Demonstrates

The assistant supports:

- temporary working memory
- persistent JSON memory
- explicit `remember` actions
- allowlisted memory categories
- basic sensitive-data rejection
- deterministic memory retrieval
- upsert instead of uncontrolled duplication
- TTL expiration
- manual expiration purge
- deletion of one memory
- clearing all persistent memory
- atomic file writes
- corrupted-store detection
- bounded record and value sizes

## Memory Architecture

```text
Conversation / task
      ↓
Working memory
(process only)
      ↓
Should this persist?
      ↓
Only an explicit remember command
      ↓
Validate category + content
      ↓
Sensitive?
  ↙          ↘
Yes           No
 ↓             ↓
Reject       Upsert
                ↓
        Optional TTL expiry
                ↓
       Local persistent store
                ↓
       Search / retrieve later
                ↓
       Forget / clear / expire
```

## Working Memory vs Persistent Memory

### Working memory

Working memory exists only in the current Python process.

Example:

```text
current task = Test Project 05
```

It disappears when the process ends.

### Persistent memory

Persistent memory is written only after an explicit `remember` command.

By default it is stored at:

```text
~/.agentic-ai-learning-roadmap/project05-memory.json
```

This path is outside the Git repository.

That choice reduces the risk of accidentally committing runtime memory to GitHub.

## Important Privacy Note

The demo persistent store is **plain JSON**.

It is not encrypted.

Therefore:

- do not store passwords
- do not store API keys
- do not store access tokens
- do not store financial account data
- do not store government IDs
- do not store medical data
- do not store secrets merely because the demo accepts some text

The built-in sensitive-data detector blocks several obvious patterns, but it is intentionally simple.

It is **not** a replacement for:

- secrets managers
- encryption at rest
- enterprise DLP
- data classification
- authorization
- retention governance
- consent management

The correct lesson is data minimization.

## Allowed Persistent Categories

The demo allows four categories:

```text
preference
project
workflow
episode
```

### `preference`

Example:

```text
preferred editor = VS Code
```

This approximates long-lived semantic preference memory.

### `project`

Example:

```text
current demo = Memory-Aware Assistant
```

### `workflow`

Example:

```text
test command = python -m unittest
```

### `episode`

Example:

```text
temporary task = Review Project 05
```

Episode-style memories are good candidates for a TTL because events become stale.

## Project Files

```text
05-memory-aware-assistant/
├── README.md
├── main.py
├── models.py
├── policy.py
├── store.py
├── assistant.py
├── test_memory_assistant.py
├── requirements.txt
└── sample_session.md
```

## Requirements

- Python 3.10+
- no API key
- no database server
- no third-party Python packages
- no network access

## Run the Tests

From this project folder:

```bash
python -m unittest test_memory_assistant.py
```

The tests cover:

- ordinary non-sensitive memory
- password rejection
- API-key rejection
- secret-token pattern rejection
- financial-data rejection
- oversized-value rejection
- memory-category allowlisting
- key normalization
- persistent create/read
- upsert without duplicates
- expiration
- purging expired data
- lexical retrieval
- deletion
- clearing
- corrupted-store protection
- refusal to persist sensitive content
- deterministic tokenization
- ephemeral working memory
- no automatic persistence
- assistant recall
- assistant forget
- assistant clear

## Find the Runtime Memory File

```bash
python main.py where
```

Expected path:

```text
~/.agentic-ai-learning-roadmap/project05-memory.json
```

The exact home directory depends on your environment.

## Save an Explicit Memory

```bash
python main.py remember \
  --category preference \
  --key "preferred editor" \
  --value "VS Code"
```

Expected output:

```text
Saved memory [preference] preferred editor = VS Code.
```

Run it again with a new value:

```bash
python main.py remember \
  --category preference \
  --key "preferred editor" \
  --value "Zed"
```

The same logical memory is updated rather than duplicated.

## Recall Memory

```bash
python main.py recall "Which editor do I prefer?"
```

Example output:

```text
1. [preference] preferred editor = Zed (...)
```

## List Active Memories

```bash
python main.py list
```

Filter by category:

```bash
python main.py list --category preference
```

## Add an Expiring Memory

```bash
python main.py remember \
  --category episode \
  --key "temporary task" \
  --value "Review Project 05" \
  --ttl-seconds 60
```

After the TTL passes, the memory is no longer returned as active.

Remove expired records from the JSON file:

```bash
python main.py purge-expired
```

## Forget One Memory

```bash
python main.py forget \
  --category preference \
  --key "preferred editor"
```

## Clear All Persistent Memory

Clearing requires an explicit confirmation flag:

```bash
python main.py clear --yes
```

Without `--yes`, the CLI refuses to clear the store.

## Test Sensitive-Data Rejection

Try:

```bash
python main.py remember \
  --category preference \
  --key "api key" \
  --value "abc123"
```

Expected behavior:

```text
Rejected: Rejected by privacy policy: possible credential data.
```

Try a token-like value:

```bash
python main.py remember \
  --category project \
  --key "service credential" \
  --value "sk-abcdefghijklmnop1234"
```

The write is rejected.

## Demonstrate Working Memory

```bash
python main.py session-demo
```

This places a value in temporary process memory.

It does **not** modify the persistent JSON store.

Run the command again and the value is recreated in a fresh process rather than loaded from disk.

## Memory Retrieval

Persistent retrieval uses a small lexical scoring function.

The query:

```text
Which editor do I prefer?
```

is compared with:

- category
- memory key
- memory value

Key matches receive more weight than value matches.

This is intentionally transparent.

A future system could replace lexical retrieval with embeddings, but memory write policy and deletion controls would still be necessary.

## Upsert Behavior

A logical persistent memory is identified by:

```text
category + normalized key
```

Saving:

```text
[preference] preferred editor = VS Code
```

and later saving:

```text
[preference] preferred editor = Zed
```

updates the same record ID.

This prevents repeated explicit writes from creating unlimited duplicates.

## Expiration

A memory may have:

```text
expires_at = null
```

or a UTC expiration timestamp.

Expired memories are excluded from:

- list
- get
- search

`purge-expired` physically removes them from the JSON file.

## Storage Limits

The demo uses conservative limits:

- maximum 200 active persistent records
- maximum 80 characters per normalized key
- maximum 500 characters per value

These are teaching safeguards, not universal production values.

## Atomic Writes

Persistent memory is written to a temporary file first.

The application then replaces the target JSON file atomically.

This reduces the chance of leaving a partially written store if a process is interrupted during the write.

## Corrupted Store Handling

If the JSON store becomes invalid, the project raises a clear error.

It does **not** silently overwrite the corrupted file.

That protects against accidental data loss.

## What This Project Does Not Do

It does not:

- call an LLM
- infer automatically what a user wants remembered
- collect entire conversations
- encrypt the memory store
- sync memories to a server
- share memory between users
- implement authentication
- store sensitive information safely
- claim that regex filtering catches every sensitive value

These exclusions are deliberate.

## Security Principle

The safest memory write is often the one you never make.

Before storing anything, ask:

1. Is it necessary?
2. Did the user explicitly ask to remember it?
3. Is it sensitive?
4. Does it need an expiration?
5. Can the user inspect it?
6. Can the user delete it?
7. What happens if it becomes stale?

## Exercises

### Beginner

Add a `language` preference and retrieve it with a differently worded query.

### Intermediate

Add a `--ttl-hours` convenience option while keeping `--ttl-seconds` for tests.

### Challenge

Add memory version history without storing unbounded copies.

Define a maximum history length and a deletion policy.

### Advanced Challenge

Create a memory-provider interface:

```text
MemoryProvider
├── LocalJSONMemory
└── FutureEncryptedMemory
```

Keep the local implementation as the default test backend.

## Next Step

Week 6 will introduce **Agentic Design Patterns**:

- reflection
- planning
- routing
- evaluator-optimizer
- parallelization
- human-in-the-loop

Return to the [main roadmap](../../README.md).
