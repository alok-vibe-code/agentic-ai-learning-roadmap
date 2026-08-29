"""Load and validate versioned evaluation cases."""

from __future__ import annotations
import json
from pathlib import Path
from models import EvalCase

DEFAULT_CASES_PATH = Path(__file__).resolve().parent / "data" / "eval_cases.json"
VALID_STATUSES = {"completed", "abstained", "failed"}


def load_cases(path: str | Path | None = None) -> list[EvalCase]:
    case_path = Path(path) if path else DEFAULT_CASES_PATH
    payload = json.loads(case_path.read_text(encoding="utf-8"))

    if not isinstance(payload, list) or not payload:
        raise ValueError("Evaluation suite must be a non-empty JSON list.")

    cases: list[EvalCase] = []
    seen: set[str] = set()

    for raw in payload:
        case_id = str(raw["id"]).strip()
        if not case_id or case_id in seen:
            raise ValueError("Evaluation case IDs must be non-empty and unique.")
        seen.add(case_id)

        query = " ".join(str(raw["query"]).split())
        if not query:
            raise ValueError(f"Case {case_id} has an empty query.")

        status = str(raw["expected_status"]).strip()
        if status not in VALID_STATUSES:
            raise ValueError(f"Case {case_id} has invalid expected_status.")

        max_steps = int(raw["max_steps"])
        if max_steps < 1 or max_steps > 20:
            raise ValueError(f"Case {case_id} has invalid max_steps.")

        expected_tool = raw.get("expected_tool")
        if expected_tool is not None:
            expected_tool = str(expected_tool).strip() or None

        cases.append(
            EvalCase(
                id=case_id,
                query=query,
                expected_status=status,
                expected_tool=expected_tool,
                must_include=tuple(str(x) for x in raw.get("must_include", [])),
                must_not_include=tuple(str(x) for x in raw.get("must_not_include", [])),
                must_cite_source=bool(raw.get("must_cite_source", False)),
                allowed_source_ids=tuple(str(x) for x in raw.get("allowed_source_ids", [])),
                max_steps=max_steps,
            )
        )

    return cases
