"""Week 2: Tool Calling Agent.

The model may request one or more narrow local tools. The application remains
responsible for validating, executing, and returning tool results.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_DEFINITIONS, call_tool


MAX_TOOL_ROUNDS = 5

SYSTEM_INSTRUCTION = """
You are a careful tool-using assistant.

You have access to narrow application-controlled tools.

Rules:
- Use a tool when it materially improves correctness.
- Use calculate_expression for arithmetic rather than doing arithmetic mentally.
- Use analyze_url only to parse URL structure. It does not fetch webpages.
- Use analyze_text only when text statistics are useful.
- Never imply that a tool can do something outside its documented capability.
- Do not invent tool results.
- After receiving tool results, answer the user's original request concisely.
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small agent that can choose and call local tools."
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="User request. If omitted, the program prompts for it.",
    )
    return parser.parse_args()


def get_request(cli_request: str | None) -> str:
    request = cli_request.strip() if cli_request else input("Enter a request: ").strip()
    if not request:
        raise ValueError("Request cannot be empty.")
    return request


def run_tool_agent(user_request: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your API key."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip()
    if not model:
        raise RuntimeError("OPENAI_MODEL cannot be empty.")

    client = OpenAI(api_key=api_key)

    # Keeping all prior response items is important for reasoning models because
    # reasoning/tool-call items may need to be passed back with tool outputs.
    input_items: list[Any] = [
        {"role": "user", "content": user_request}
    ]

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):
        response = client.responses.create(
            model=model,
            instructions=SYSTEM_INSTRUCTION,
            input=input_items,
            tools=TOOL_DEFINITIONS,
        )

        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not function_calls:
            final_text = response.output_text.strip()
            if not final_text:
                raise RuntimeError("The model returned no final text.")
            return final_text

        # Preserve all response output items, including reasoning items.
        input_items += response.output

        for tool_call in function_calls:
            try:
                arguments = json.loads(tool_call.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object.")

                result = call_tool(tool_call.name, arguments)
                trace = {
                    "round": round_number,
                    "tool": tool_call.name,
                    "arguments": arguments,
                    "result": result,
                }
            except Exception as exc:
                result = {
                    "ok": False,
                    "error": str(exc),
                }
                trace = {
                    "round": round_number,
                    "tool": tool_call.name,
                    "error": str(exc),
                }

            print("[tool]", json.dumps(trace, ensure_ascii=False), file=sys.stderr)

            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError(
        f"Maximum tool rounds ({MAX_TOOL_ROUNDS}) reached before a final answer."
    )


def main() -> int:
    load_dotenv()

    try:
        args = parse_args()
        user_request = get_request(args.request)
        answer = run_tool_agent(user_request)
        print(answer)
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
