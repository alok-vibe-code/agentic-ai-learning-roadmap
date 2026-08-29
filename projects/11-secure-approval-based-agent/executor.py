from __future__ import annotations
import ast, json, operator
from pathlib import Path
from guardrails import inspect_tool_output
from models import Action, ExecutionResult
from policy import PolicyEngine

DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parent / "data" / "knowledge.json"
_ALLOWED_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

def safe_calculate(expression: str) -> float:
    if len(expression) > 200:
        raise ValueError("Expression is too long.")
    tree = ast.parse(expression, mode="eval")
    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
            return _ALLOWED_OPS[type(node.op)](visit(node.left), visit(node.right))
        raise ValueError("Unsupported calculation.")
    return float(visit(tree))

class SandboxedExecutor:
    def __init__(self, policy: PolicyEngine, *, knowledge_path: str | Path | None = None) -> None:
        self.policy = policy
        path = Path(knowledge_path) if knowledge_path else DEFAULT_KNOWLEDGE_PATH
        self.knowledge = json.loads(path.read_text(encoding="utf-8"))
        self.effects: list[dict] = []
        self.idempotency_results: dict[str, ExecutionResult] = {}

    def execute(self, action: Action) -> ExecutionResult:
        if action.idempotency_key and action.idempotency_key in self.idempotency_results:
            cached = self.idempotency_results[action.idempotency_key]
            return ExecutionResult("idempotent_replay", "Existing result returned for idempotency key.", cached.data)
        result = self._execute_once(action)
        if action.idempotency_key and result.status == "executed":
            self.idempotency_results[action.idempotency_key] = result
        return result

    def _execute_once(self, action: Action) -> ExecutionResult:
        if action.type == "search":
            query = str(action.parameters.get("query", "")).casefold()
            matches = [
                {"resource": resource, "text": text}
                for resource, text in self.knowledge.items()
                if any(token in text.casefold() or token in resource.casefold()
                       for token in query.split() if len(token) > 2)
            ]
            return ExecutionResult("executed", f"Found {len(matches)} local result(s).", {"results": matches[:3]})

        if action.type == "read_resource":
            resource = str(action.parameters.get("resource", ""))
            if resource not in self.policy.allowlisted_resources:
                return ExecutionResult("blocked", "Resource is not on the allowlist.", {})
            if resource not in self.knowledge:
                return ExecutionResult("blocked", "Allowlisted resource does not exist.", {})
            text = self.knowledge[resource]
            guard = inspect_tool_output(text)
            if not guard.allowed:
                return ExecutionResult("blocked", "Untrusted resource output was blocked.", {"signals": list(guard.signals)})
            return ExecutionResult("executed", "Resource read successfully.", {"resource": resource, "text": text})

        if action.type == "calculate":
            value = safe_calculate(str(action.parameters.get("expression", "")))
            rendered = int(value) if value.is_integer() else value
            return ExecutionResult("executed", f"Calculation result: {rendered}", {"value": rendered})

        if action.type == "send_email":
            effect = {"type": "email", "to": action.parameters.get("to"), "subject": action.parameters.get("subject"),
                      "body": action.parameters.get("body"), "simulated": True}
            self.effects.append(effect)
            return ExecutionResult("executed", "Email send simulated.", effect)

        if action.type == "publish_content":
            effect = {"type": "publication", "content": action.parameters.get("content"), "simulated": True}
            self.effects.append(effect)
            return ExecutionResult("executed", "Content publication simulated.", effect)

        if action.type == "delete_file":
            path = str(action.parameters.get("path", ""))
            if path.startswith(("/", "\\", "~")) or ".." in Path(path).parts:
                return ExecutionResult("blocked", "Unsafe path is outside the demo sandbox.", {})
            effect = {"type": "file_deletion", "path": path, "simulated": True}
            self.effects.append(effect)
            return ExecutionResult("executed", "File deletion simulated.", effect)

        if action.type == "modify_external_record":
            effect = {"type": "external_record_update", **action.parameters, "simulated": True}
            self.effects.append(effect)
            return ExecutionResult("executed", "External record modification simulated.", effect)

        if action.type == "financial_transfer":
            amount = float(action.parameters.get("amount", 0.0))
            maximum = float(self.policy.limits.get("max_financial_transfer", 0.0))
            if amount <= 0:
                return ExecutionResult("blocked", "Transfer amount must be positive.", {})
            if amount > maximum:
                return ExecutionResult("blocked", f"Transfer exceeds demo limit of {maximum}.", {})
            effect = {"type": "financial_transfer", "amount": amount,
                      "destination": action.parameters.get("destination"), "simulated": True}
            self.effects.append(effect)
            return ExecutionResult("executed", "Financial transfer simulated.", effect)

        return ExecutionResult("blocked", "Executor does not implement this action.", {})
