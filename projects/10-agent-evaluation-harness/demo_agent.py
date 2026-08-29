"""Deterministic candidates used to demonstrate the evaluation harness."""

from __future__ import annotations
import ast
import operator
import re
import time

from models import AgentRun, ToolCall
from observability import TraceCollector

DOCS = {
    "MCP-SPEC": (
        "The Model Context Protocol specification defines a standard way for "
        "applications to expose tools, resources, and prompts to AI systems."
    ),
    "AGENTIC-RAG": (
        "Agentic RAG adds decision-making around retrieval: an agent can decide "
        "whether retrieval is needed, rewrite a query, inspect evidence, retry, "
        "and abstain when context is insufficient."
    ),
    "MEMORY": (
        "A safe default for persistent agent memory is explicit user-controlled "
        "writes, data minimization, sensitive-data rejection, expiration, and "
        "deletion controls."
    ),
    "MULTI-AGENT": (
        "Multi-agent systems are justified when specialization, independent "
        "subtasks, or review boundaries create enough value to offset coordination "
        "overhead and additional failure surfaces."
    ),
}

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _safe_calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            return _ALLOWED_BINOPS[type(node.op)](visit(node.left), visit(node.right))
        raise ValueError("Unsupported calculation.")

    return float(visit(tree))


def _estimate_tokens(text: str) -> int:
    # Deliberately approximate and provider-independent.
    return max(1, (len(text) + 3) // 4)


def _search(query: str) -> tuple[str, str] | None:
    q = query.casefold()
    mapping = (
        (("mcp", "model context protocol"), "MCP-SPEC"),
        (("agentic rag", "rag"), "AGENTIC-RAG"),
        (("memory", "persistent"), "MEMORY"),
        (("multi-agent", "multi agent"), "MULTI-AGENT"),
    )
    for terms, source_id in mapping:
        if any(term in q for term in terms):
            return source_id, DOCS[source_id]
    return None


class DemoAgent:
    def __init__(self, mode: str = "good") -> None:
        if mode not in {"good", "broken"}:
            raise ValueError("mode must be 'good' or 'broken'.")
        self.mode = mode

    def run(self, query: str) -> AgentRun:
        if not isinstance(query, str):
            raise TypeError("query must be a string.")
        query = " ".join(query.split())
        if not query:
            raise ValueError("query cannot be empty.")
        if len(query) > 2_000:
            raise ValueError("query exceeds demo limit.")

        started = time.perf_counter()
        trace = TraceCollector(f"{self.mode}:{query}")
        root = trace.span_id()
        trace.record(
            span_id=root,
            parent_span_id=None,
            kind="run",
            name="agent.run",
            candidate=self.mode,
            query=query,
        )

        q = query.casefold()
        tool_calls = []
        citations = []
        steps = 1
        status = "completed"
        error = None

        # No live-data access in this offline candidate.
        if "live weather" in q or "right now" in q:
            answer = (
                "I cannot answer that reliably because this offline demo does not "
                "have access to live data."
            )
            status = "abstained"
            trace.record(
                span_id=root,
                parent_span_id=None,
                kind="decision",
                name="abstain.live_data",
                reason="live_data_unavailable",
            )

        elif "private account password" in q or "my password" in q:
            answer = (
                "I do not have access to your private account credentials or password."
            )
            status = "abstained"
            trace.record(
                span_id=root,
                parent_span_id=None,
                kind="decision",
                name="abstain.private_data",
                reason="private_data_unavailable",
            )

        elif "calculate" in q:
            match = re.search(
                r"calculate\s+([0-9]+(?:\.[0-9]+)?\s*[+\-*/]\s*[0-9]+(?:\.[0-9]+)?)",
                query,
                flags=re.IGNORECASE,
            )
            if not match:
                answer = "I could not parse the requested calculation."
                status = "failed"
                error = "calculation_parse_error"
            else:
                expression = match.group(1)
                tool_name = "calculator"
                # Broken candidate demonstrates a routing regression.
                if self.mode == "broken":
                    tool_name = "local_search"

                tool_span = trace.span_id()
                trace.record(
                    span_id=tool_span,
                    parent_span_id=root,
                    kind="tool",
                    name=tool_name,
                    arguments={"expression": expression},
                )
                tool_calls.append(
                    ToolCall(name=tool_name, arguments={"expression": expression})
                )
                steps += 1

                if tool_name == "calculator":
                    value = _safe_calculate(expression)
                    if value.is_integer():
                        rendered = str(int(value))
                    else:
                        rendered = str(value)
                    answer = f"The result is {rendered}."
                else:
                    answer = "No relevant local document was found for that calculation."

        else:
            result = _search(query)
            if result is None:
                answer = "I do not have enough local evidence to answer this reliably."
                status = "abstained"
            else:
                source_id, text = result
                tool_name = "local_search"
                tool_span = trace.span_id()
                trace.record(
                    span_id=tool_span,
                    parent_span_id=root,
                    kind="tool",
                    name=tool_name,
                    arguments={"query": query},
                    returned_source_ids=[source_id],
                )
                tool_calls.append(
                    ToolCall(
                        name=tool_name,
                        arguments={"query": query},
                        returned_source_ids=(source_id,),
                    )
                )
                steps += 1

                answer = text
                citations = [source_id]

                # Broken candidate creates citation regressions for search cases.
                if self.mode == "broken":
                    citations = ["UNOBSERVED-SOURCE"]

        final_span = trace.span_id()
        trace.record(
            span_id=final_span,
            parent_span_id=root,
            kind="response",
            name="agent.response",
            status=status,
            citations=list(citations),
            steps=steps,
        )

        latency_ms = (time.perf_counter() - started) * 1000.0
        estimated_tokens = _estimate_tokens(query + "\n" + answer)

        return AgentRun(
            status=status,
            answer=answer,
            tool_calls=tuple(tool_calls),
            citations=tuple(citations),
            steps=steps,
            estimated_tokens=estimated_tokens,
            cost_usd=0.0,
            latency_ms=latency_ms,
            trace=trace.events(),
            error=error,
        )
