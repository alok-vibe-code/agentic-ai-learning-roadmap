# Project 01: Structured LLM Assistant

This is the first working project in the Agentic AI Learning Roadmap.

It intentionally **does not build an autonomous agent yet**. The purpose is to establish a reliable foundation: turning natural-language instructions into validated, typed data that application code can safely consume.

## What You Will Build

A command-line assistant that accepts a task and returns a structured plan with:

- task
- objective
- category
- priority
- assumptions
- ordered steps
- risks
- success criteria
- next action

Example request:

```text
Prepare a research plan for comparing major Model Context Protocol tools.
```

The application requests a structured response from an OpenAI model and validates the result with Pydantic.

## What You Will Learn

- Calling an LLM from Python
- Keeping secrets in environment variables
- Using structured model outputs
- Defining a Pydantic schema
- Validating generated data
- Handling API and validation failures
- Why structured output matters before building tool-using agents

## Architecture

```text
User task
   ↓
Python CLI
   ↓
System instruction
   ↓
LLM
   ↓
Structured Output schema
   ↓
Pydantic validation
   ↓
Typed JSON result
```

## Requirements

- Python 3.10+
- An OpenAI API key
- Internet access while running the project

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

### 3. Create your environment file

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

Do **not** commit `.env`.

The model is configurable through `OPENAI_MODEL`. If the example model is not available to your API project, choose a model available to your account that supports Structured Outputs.

## Run the Project

Pass the task directly:

```bash
python main.py "Create a plan for researching the Model Context Protocol."
```

Or run without an argument:

```bash
python main.py
```

You will be prompted to enter a task.

## Example Output

A response will follow this structure:

```json
{
  "task": "Create a plan for researching the Model Context Protocol.",
  "objective": "Produce an evidence-based overview of MCP architecture, ecosystem, and practical implementation considerations.",
  "category": "research",
  "priority": "medium",
  "assumptions": [
    "The research should prioritize primary and official sources."
  ],
  "steps": [
    "Define the research questions.",
    "Review the official protocol documentation.",
    "Identify reference implementations and ecosystem tools.",
    "Compare capabilities and trust boundaries.",
    "Summarize findings with source links."
  ],
  "risks": [
    "Relying on outdated third-party explanations.",
    "Mixing protocol capabilities with vendor-specific features."
  ],
  "success_criteria": [
    "Major MCP concepts are explained accurately.",
    "Claims are traceable to reliable sources.",
    "Implementation considerations are clearly separated from protocol requirements."
  ],
  "next_action": "List the primary research questions before collecting sources."
}
```

The exact wording will vary.

## How It Works

The `TaskPlan` Pydantic model defines the required output schema.

The application calls `client.responses.parse(...)` with that schema. The SDK requests structured output and returns a parsed Pydantic object when the response is valid.

The program then prints the validated object as formatted JSON.

## Why This Matters for Agentic AI

An agent may eventually use model output to:

- choose a tool
- create a plan
- update state
- route a task
- request human approval
- decide whether to continue

If these decisions are returned only as loosely formatted prose, application logic becomes brittle.

Structured outputs give the surrounding software a predictable contract.

## Security Notes

- Never hard-code your API key.
- Never commit `.env`.
- Do not send confidential information to a third-party model unless your data-handling requirements permit it.
- Treat model output as untrusted until validated.
- Schema validation improves structure but does not guarantee factual correctness.
- Avoid automatically executing actions based only on model output.

## Known Limitations

This project:

- does not call tools
- does not browse the web
- does not maintain memory
- does not verify factual claims
- is not an autonomous agent

Those limitations are intentional.

## Exercises

### Beginner

Add a new field called `estimated_effort` with allowed values:

- `small`
- `medium`
- `large`

### Intermediate

Add an optional list of `questions_to_clarify` and update the system instruction so the model identifies missing information.

### Challenge

Create a second Pydantic schema for a `ResearchPlan` and let the user select which structured output type they want.

## Next Step

Week 2 will add **tool calling**, where the model can request application-controlled functions rather than only returning a structured plan.

Return to the [main roadmap](../../README.md).
