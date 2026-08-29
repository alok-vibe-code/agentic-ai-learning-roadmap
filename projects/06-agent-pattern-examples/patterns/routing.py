"""Routing pattern: send a request to the smallest matching specialist."""

from __future__ import annotations

import ast
import operator
import re

from models import PatternTrace, RouteDecision


ROUTES = {
    "calculator": {
        "calculator", "calculate", "math", "sum", "add", "subtract",
        "multiply", "divide", "percentage"
    },
    "text": {
        "text", "word", "words", "sentence", "sentences", "character",
        "characters", "count", "rewrite"
    },
    "research": {
        "research", "compare", "source", "sources", "evidence", "framework",
        "rag", "agentic", "mcp"
    },
}

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def route_request(request: str) -> tuple[RouteDecision, PatternTrace]:
    normalized = " ".join(request.strip().split())
    if not normalized:
        raise ValueError("Request cannot be empty.")

    trace = PatternTrace(pattern="routing")
    terms = set(re.findall(r"[a-z0-9_-]+", normalized.casefold()))

    scores: dict[str, int] = {
        route: len(terms & keywords)
        for route, keywords in ROUTES.items()
    }

    best_route = max(scores, key=scores.get)
    best_score = scores[best_route]
    tied = [route for route, score in scores.items() if score == best_score]

    if best_score == 0 or len(tied) > 1:
        decision = RouteDecision(
            route="general",
            confidence=0.40 if best_score == 0 else 0.50,
            reason="No unique specialist matched strongly enough.",
        )
    else:
        total = max(1, sum(scores.values()))
        confidence = min(0.99, 0.60 + 0.35 * (best_score / total))
        decision = RouteDecision(
            route=best_route,
            confidence=round(confidence, 2),
            reason=f"Matched {best_score} specialist keyword(s).",
        )

    trace.add(1, "score_routes", scores=scores)
    trace.add(
        2,
        "select_route",
        route=decision.route,
        confidence=decision.confidence,
    )
    trace.stop_reason = "route_selected"
    return decision, trace


def _safe_eval(expression: str) -> float:
    node = ast.parse(expression, mode="eval")

    def evaluate(current):
        if isinstance(current, ast.Expression):
            return evaluate(current.body)
        if isinstance(current, ast.Constant):
            if isinstance(current.value, (int, float)):
                return current.value
            raise ValueError("Only numeric constants are allowed.")
        if isinstance(current, ast.BinOp) and type(current.op) in _ALLOWED_BINOPS:
            left = evaluate(current.left)
            right = evaluate(current.right)
            if isinstance(current.op, ast.Div) and right == 0:
                raise ValueError("Division by zero is not allowed.")
            return _ALLOWED_BINOPS[type(current.op)](left, right)
        raise ValueError("Unsupported arithmetic expression.")

    return float(evaluate(node))


def run_specialist(route: str, request: str) -> str:
    if route == "calculator":
        match = re.search(r"([-+*/().\d\s]+)", request)
        if not match or not re.search(r"\d", match.group(1)):
            return "Calculator route selected, but no arithmetic expression was found."
        expression = match.group(1).strip()
        return f"Calculator result: {_safe_eval(expression):g}"

    if route == "text":
        words = re.findall(r"\b[\w'-]+\b", request)
        return (
            f"Text analysis: {len(words)} words, "
            f"{len(request)} characters."
        )

    if route == "research":
        return (
            "Research route selected: gather sources, compare evidence, "
            "and cite the result."
        )

    return "General route selected: handle the request without a specialist."
