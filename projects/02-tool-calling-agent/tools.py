"""Deterministic local tools for the Week 2 Tool Calling Agent.

These functions intentionally do not perform network requests or execute
arbitrary Python code. They demonstrate how an application can expose narrow,
validated capabilities to a model.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any
from urllib.parse import parse_qs, urlparse


MAX_EXPRESSION_LENGTH = 200
MAX_TEXT_LENGTH = 5_000
MAX_URL_LENGTH = 2_048
MAX_ABS_RESULT = 1e15
MAX_EXPONENT = 10

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _validate_number(value: Any) -> float | int:
    if type(value) not in (int, float):
        raise ValueError("Only real numeric values are allowed.")
    if not math.isfinite(float(value)):
        raise ValueError("Non-finite numeric results are not allowed.")
    if abs(float(value)) > MAX_ABS_RESULT:
        raise ValueError("Numeric result is too large.")
    return value


def _eval_ast(node: ast.AST, depth: int = 0) -> float | int:
    if depth > 25:
        raise ValueError("Expression is too deeply nested.")

    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, depth + 1)

    if isinstance(node, ast.Constant):
        return _validate_number(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        operand = _eval_ast(node.operand, depth + 1)
        return _validate_number(_UNARY_OPERATORS[type(node.op)](operand))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _eval_ast(node.left, depth + 1)
        right = _eval_ast(node.right, depth + 1)

        if isinstance(node.op, ast.Pow) and abs(float(right)) > MAX_EXPONENT:
            raise ValueError(f"Exponent magnitude must be <= {MAX_EXPONENT}.")

        try:
            result = _BINARY_OPERATORS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise ValueError("Division by zero is not allowed.") from exc

        return _validate_number(result)

    raise ValueError(
        "Unsupported expression. Use numbers, parentheses, and + - * / // % ** only."
    )


def calculate_expression(expression: str) -> dict[str, Any]:
    """Safely evaluate a restricted arithmetic expression."""

    expression = expression.strip()
    if not expression:
        raise ValueError("Expression cannot be empty.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("Expression is too long.")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Expression is not valid arithmetic.") from exc

    result = _eval_ast(tree)
    return {
        "ok": True,
        "expression": expression,
        "result": result,
    }


def analyze_url(url: str) -> dict[str, Any]:
    """Parse an HTTP(S) URL without fetching any remote content."""

    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty.")
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL is too long.")

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported.")
    if not parsed.hostname:
        raise ValueError("URL must include a valid hostname.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL contains an invalid port.") from exc

    query = parse_qs(parsed.query, keep_blank_values=True)
    query_count = sum(len(values) for values in query.values())

    return {
        "ok": True,
        "scheme": parsed.scheme,
        "hostname": parsed.hostname,
        "port": port,
        "path": parsed.path or "/",
        "query_parameter_names": sorted(query.keys()),
        "query_parameter_count": query_count,
        "has_fragment": bool(parsed.fragment),
        "note": "The URL was parsed locally. No network request was made.",
    }


def analyze_text(text: str) -> dict[str, Any]:
    """Return basic deterministic statistics for a text string."""

    if not text.strip():
        raise ValueError("Text cannot be empty.")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text must be <= {MAX_TEXT_LENGTH} characters.")

    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    sentences = [
        segment.strip()
        for segment in re.split(r"[.!?]+", text)
        if segment.strip()
    ]

    return {
        "ok": True,
        "word_count": len(words),
        "unique_word_count": len({word.casefold() for word in words}),
        "character_count": len(text),
        "character_count_without_spaces": len(re.sub(r"\s", "", text)),
        "sentence_count": len(sentences),
    }


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "calculate_expression",
        "description": (
            "Safely evaluate a basic arithmetic expression. "
            "Use this for calculations instead of doing arithmetic mentally."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression using numbers and + - * / // % ** with parentheses.",
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "analyze_url",
        "description": (
            "Parse the structure of an http or https URL locally. "
            "This does not visit, download, or inspect the webpage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Complete http or https URL to parse.",
                }
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "analyze_text",
        "description": (
            "Calculate basic statistics for supplied text, including word, "
            "character, sentence, and unique-word counts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to analyze, up to 5000 characters.",
                }
            },
            "required": ["text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route a validated tool name to application-controlled Python code."""

    if name == "calculate_expression":
        return calculate_expression(**arguments)
    if name == "analyze_url":
        return analyze_url(**arguments)
    if name == "analyze_text":
        return analyze_text(**arguments)

    raise ValueError(f"Unknown tool: {name}")
