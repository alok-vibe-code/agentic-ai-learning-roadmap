# Sample Session: Project 05 Memory-Aware Assistant

## 1. Check Persistent Store Location

```bash
python main.py where
```

Example:

```text
/home/codespace/.agentic-ai-learning-roadmap/project05-memory.json
```

## 2. Store an Explicit Preference

```bash
python main.py remember \
  --category preference \
  --key "preferred editor" \
  --value "VS Code"
```

```text
Saved memory [preference] preferred editor = VS Code.
```

## 3. Recall It in a Later Command

```bash
python main.py recall "Which editor do I prefer?"
```

```text
1. [preference] preferred editor = VS Code (...)
```

## 4. Update the Same Memory

```bash
python main.py remember \
  --category preference \
  --key "preferred editor" \
  --value "Zed"
```

```text
Updated memory [preference] preferred editor = Zed.
```

The store contains one logical `preferred editor` record, not two duplicates.

## 5. Add an Expiring Episode

```bash
python main.py remember \
  --category episode \
  --key "temporary task" \
  --value "Review Project 05" \
  --ttl-seconds 60
```

## 6. Try to Store a Credential

```bash
python main.py remember \
  --category preference \
  --key "api key" \
  --value "abc123"
```

Expected:

```text
Rejected: Rejected by privacy policy: possible credential data.
```

## 7. Forget a Memory

```bash
python main.py forget \
  --category preference \
  --key "preferred editor"
```

```text
Memory deleted.
```

## 8. Clear All Persistent Memory

```bash
python main.py clear --yes
```

## 9. Demonstrate Working Memory

```bash
python main.py session-demo
```

The working-memory item is process-local and is never written to the persistent JSON store.
