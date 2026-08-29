# Project 02: Tool Calling Agent

This is the Week 2 working project in the **Agentic AI Learning Roadmap**.

The goal is to demonstrate the complete function-calling lifecycle:

**model selects a tool → application validates and executes it → result returns to the model → model answers the user**

The application, not the model, owns the actual tool execution.

## What You Will Build

A command-line assistant with three narrow local tools:

1. **Safe calculator**
   - Evaluates restricted arithmetic expressions
   - Does not use Python `eval`
   - Blocks names, function calls, and arbitrary code execution

2. **URL analyzer**
   - Parses an `http` or `https` URL
   - Returns hostname, path, query parameters, port, and fragment information
   - Does **not** fetch or visit the webpage

3. **Text analyzer**
   - Counts words
   - Counts unique words
   - Counts characters
   - Estimates sentence count

The model decides whether one or more tools are useful for the user's request.

## What You Will Learn

- How function tools are defined with JSON Schema
- Why tool descriptions matter
- How the model requests a function call
- How to parse tool arguments
- How to route tool names to application code
- How to return `function_call_output`
- How to preserve prior response items across tool rounds
- Why applications must validate tool arguments
- Why tool capabilities should be narrow
- How to limit repeated tool calls

## Architecture

```text
User
 ↓
OpenAI model
 ↓
Need a tool?
 ↙       ↘
No       Yes
↓         ↓
Answer   Function call
          ↓
     Python application
          ↓
   Validate arguments
          ↓
     Execute local tool
          ↓
   function_call_output
          ↓
       Model
          ↓
     Final answer
```

## Project Files

```text
02-tool-calling-agent/
├── README.md
├── main.py
├── tools.py
├── test_tools.py
├── requirements.txt
├── .env.example
└── sample_session.md
```

## Requirements

- Python 3.10+
- OpenAI API key
- Internet access for the OpenAI API request

The local tools themselves do not require external APIs.

## Setup

### 1. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the API key

Copy `.env.example` to `.env`.

Windows:

```bash
copy .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.6-luna
```

Never commit `.env`.

If the example model is unavailable to your API project, choose another model available to your account that supports function calling.

## Run the Local Tool Tests First

The tool tests do not call the OpenAI API:

```bash
python -m unittest test_tools.py
```

Expected result:

```text
......
----------------------------------------------------------------------
Ran 6 tests

OK
```

## Run the Agent

### Calculator example

```bash
python main.py "What is 17% of 895? Use a tool if useful."
```

The model should request `calculate_expression`, the application will execute the calculation, and the model will return the final answer.

### URL example

```bash
python main.py "Analyze this URL structure: https://example.com/blog/post?ref=linkedin&utm_source=test#intro"
```

The model can call `analyze_url`.

Remember: this tool **does not visit the webpage**.

### Text-analysis example

```bash
python main.py "How many words and sentences are in this text: Agent systems use tools. Tools need boundaries."
```

The model can call `analyze_text`.

### Multi-tool example

```bash
python main.py "Analyze https://example.com/a?x=1 and also calculate (1250 * 0.18) + 40."
```

The model may request multiple tools before answering.

## Tool Trace

Tool execution is printed to standard error in a trace like:

```text
[tool] {"round": 1, "tool": "calculate_expression", ...}
```

This is included for learning and debugging.

Do not treat this simple console trace as production observability.

## How the Function-Calling Loop Works

### 1. Send the user request and tool schemas

`main.py` sends the request to the Responses API along with the three tool definitions.

### 2. Inspect the model response

If the response contains a `function_call`, the application reads:

- tool name
- call ID
- JSON arguments

### 3. Execute application code

`call_tool()` routes only known tool names to narrow Python functions.

The model never directly executes Python code.

### 4. Return the result

The application appends a `function_call_output` item using the same `call_id`.

### 5. Ask the model to continue

The response output and tool result are passed back so the model can produce the final answer or request another tool.

### 6. Stop safely

The demo allows at most five tool rounds.

## Security Choices in This Project

### No `eval`

The calculator uses Python's AST parser and permits only restricted arithmetic nodes.

### Narrow tool allowlist

Only three explicitly registered tools can run.

### URL tool does not fetch remote content

This avoids introducing SSRF and untrusted-web-content concerns in a Week 2 example.

### Bounded inputs

The tools limit expression, URL, and text lengths.

### Bounded tool loop

The agent cannot request tools indefinitely.

### Errors become tool results

Invalid arguments produce controlled error information rather than automatically crashing the whole agent loop.

## What This Project Does Not Do

It does not:

- browse the web
- send emails
- modify files
- execute shell commands
- retain memory
- perform RAG
- run an autonomous research loop

Those capabilities introduce additional complexity and security boundaries that belong in later weeks.

## Exercises

### Beginner

Add a local tool called `convert_temperature` that converts Celsius to Fahrenheit and Fahrenheit to Celsius.

### Intermediate

Add a `slugify_text` tool and write unit tests for it.

### Challenge

Add a fourth tool that reads from a small **allowlisted local JSON file**. Do not allow arbitrary file paths supplied by the model.

Then answer:

1. What data can the tool access?
2. What arguments must be validated?
3. What would happen if retrieved content contained malicious instructions?

## Next Step

Week 3 will build a **Research Agent** with a bounded multi-step loop, explicit state, stopping conditions, and source handling.

Return to the [main roadmap](../../README.md).
