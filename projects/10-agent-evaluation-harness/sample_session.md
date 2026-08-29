# Sample Session

## Good Candidate + Regression Check

```bash
python main.py evaluate --candidate good --format markdown --regression
```

Expected summary:

```text
Candidate: good
Cases: 8
Pass rate: 100%
Regression: passed
```

## Broken Candidate

```bash
python main.py evaluate --candidate broken --format markdown
```

Expected:

```text
non-zero exit status
calculator cases fail tool-selection checks
search cases fail groundedness checks
```

## JSON

```bash
python main.py evaluate --candidate good --format json --regression
```

## One Case

```bash
python main.py case mcp_spec --candidate good
```

## Trace

```bash
python main.py trace mcp_spec --candidate good
```

A trace should show a root run event, a local-search tool event, and a response event.

## Cases

```bash
python main.py cases
```
