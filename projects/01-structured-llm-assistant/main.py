"""Project 01: Structured LLM Assistant.

Turns a natural-language task into a validated TaskPlan using the OpenAI
Responses API and Pydantic Structured Outputs.

Never store API keys in this file. Use a local .env file instead.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


class TaskPlan(BaseModel):
    """Validated structure returned by the model."""

    task: str = Field(description="The user's task, rewritten clearly without changing intent.")
    objective: str = Field(description="The concrete outcome the user is trying to achieve.")
    category: Literal[
        "research",
        "writing",
        "analysis",
        "planning",
        "coding",
        "automation",
        "other",
    ] = Field(description="The best-fitting category for the task.")
    priority: Literal["low", "medium", "high"] = Field(
        description="Suggested priority based only on information present in the task."
    )
    assumptions: list[str] = Field(
        description="Explicit assumptions needed to create the plan. Use an empty list when none are needed."
    )
    steps: list[str] = Field(
        min_length=1,
        description="A concise ordered sequence of actions for completing the task.",
    )
    risks: list[str] = Field(
        description="Important risks, uncertainties, or failure modes. Use an empty list when none are apparent."
    )
    success_criteria: list[str] = Field(
        min_length=1,
        description="Observable conditions that indicate the task has been completed well.",
    )
    next_action: str = Field(
        description="The single most useful immediate next action."
    )


SYSTEM_INSTRUCTION = """
You are a planning assistant used inside a software application.

Convert the user's task into a practical structured plan.

Rules:
- Preserve the user's intent.
- Do not invent deadlines, budgets, credentials, people, or access that were not provided.
- Keep steps concise and executable.
- State assumptions explicitly.
- Include realistic risks.
- Use "high" priority only when the user indicates urgency or meaningful risk.
- Do not claim that work has already been completed.
- Do not include secrets or request credentials.
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a natural-language task into a validated structured plan."
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to analyze. If omitted, the program prompts for it.",
    )
    return parser.parse_args()


def get_task(cli_task: str | None) -> str:
    task = cli_task.strip() if cli_task else input("Enter a task: ").strip()
    if not task:
        raise ValueError("Task cannot be empty.")
    return task


def create_task_plan(task: str) -> TaskPlan:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your API key."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip()
    if not model:
        raise RuntimeError("OPENAI_MODEL cannot be empty.")

    client = OpenAI(api_key=api_key)

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": task},
        ],
        text_format=TaskPlan,
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "The model did not return a parsed TaskPlan. "
            "Review the API response or try a different supported model."
        )

    return response.output_parsed


def main() -> int:
    load_dotenv()

    try:
        args = parse_args()
        task = get_task(args.task)
        plan = create_task_plan(task)
        print(plan.model_dump_json(indent=2))
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
