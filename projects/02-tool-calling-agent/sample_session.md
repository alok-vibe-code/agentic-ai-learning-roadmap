# Sample Session

The exact wording of model responses will vary.

## Calculator

Command:

```bash
python main.py "What is 17% of 895? Use a tool if useful."
```

Example tool trace:

```text
[tool] {"round": 1, "tool": "calculate_expression", "arguments": {"expression": "(17 / 100) * 895"}, "result": {"ok": true, "expression": "(17 / 100) * 895", "result": 152.15}}
```

Example final answer:

```text
17% of 895 is 152.15.
```

## URL Analysis

Command:

```bash
python main.py "Analyze https://example.com/blog/post?ref=linkedin&x=1#section"
```

Example tool result includes:

```json
{
  "ok": true,
  "scheme": "https",
  "hostname": "example.com",
  "port": null,
  "path": "/blog/post",
  "query_parameter_names": ["ref", "x"],
  "query_parameter_count": 2,
  "has_fragment": true,
  "note": "The URL was parsed locally. No network request was made."
}
```

## Text Analysis

Command:

```bash
python main.py "Count the words and sentences in: Agents use tools. Tools need boundaries."
```

Example tool result:

```json
{
  "ok": true,
  "word_count": 6,
  "unique_word_count": 6,
  "character_count": 39,
  "character_count_without_spaces": 34,
  "sentence_count": 2
}
```
